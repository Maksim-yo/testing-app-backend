from sqlalchemy.orm import Session, selectinload, joinedload
from models import test as model
from schemas import test as schema
from models import Employee, Test, Question, BelbinQuestion, BelbinAnswer, TestSettings, UserAnswer, TestResult, UserAnswerItem, UserBelbinAnswer, BelbinTestResult, BelbinPositionRequirement, Position
from fastapi import HTTPException, status
from schemas.test import Test as TestSchema, TestWithAnswersSchema, UserAnswer as UserAnswerSchema, UserAnswerCreate, TestAssignmentCreate, SafeTest, SafeAnswer, SafeBelbinAnswer, SafeBelbinQuestion, SafeQuestion, TestResultSchema
from datetime import datetime, timezone, timedelta
from typing import List, Set, Tuple, Dict, Iterable
from sqlalchemy import insert, delete, and_
from sqlalchemy.exc import IntegrityError
import json
from sqlalchemy import select

from collections import defaultdict

# Need celery + redis 
def auto_complete_expired_tests(results: Iterable[TestResult], db: Session, now: datetime | None = None) -> None:
    """Завершает тесты, если истекло отведенное время прохождения."""
    now = now or datetime.now(timezone.utc)

    for result in results:
        test = result.test
        started_at = result.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        if not result.is_completed and test.time_limit_minutes is not None:
            elapsed = now - started_at
            if elapsed > timedelta(minutes=test.time_limit_minutes):
                # Нужно найти clerk_id пользователя, которому принадлежит результат
                clerk_id = result.employee.clerk_id
                complete_test(db, user_id=clerk_id, test_id=test.id)

        if test.end_date and test.end_date < now:
            clerk_id = result.employee.clerk_id
            complete_test(db, user_id=clerk_id, test_id=test.id)

  
def get_belbin_answers_data(db: Session, test_id: int, employee_id: int) -> Dict:
    """Получить данные о ответах пользователя на вопросы Белбина."""
    belbin_user_answers = db.query(UserBelbinAnswer).filter(
        and_(
            UserBelbinAnswer.test_id == test_id,
            UserBelbinAnswer.employee_id == employee_id
        )
    ).all()

    return {uba.answer_id: uba.score for uba in belbin_user_answers}


def build_safe_questions(questions: List[model.Question], user_answers_data: Tuple) -> List[SafeQuestion]:
    """Сформировать SafeQuestion объекты с информацией о ответах пользователя."""
    user_answers_by_qid, answer_ids_by_question = user_answers_data
    safe_questions = []
    
    for question in questions:
        safe_answers = build_safe_answers(question, user_answers_by_qid, answer_ids_by_question)
        
        safe_questions.append(SafeQuestion(
            id=question.id,
            text=question.text,
            question_type=question.question_type,
            order=question.order,
            test_id=question.test_id,
            image=question.image,
            answers=safe_answers
        ))
    
    return safe_questions


def build_safe_answers(question: model.Question, user_answers_by_qid: Dict, answer_ids_by_question: Dict) -> List[SafeAnswer]:
    """Сформировать SafeAnswer объекты для вопроса."""
    safe_answers = []
    user_answer = user_answers_by_qid.get(question.id)
    selected_answer_ids = answer_ids_by_question.get(question.id, set())

    if question.question_type == "text_answer" and user_answer and user_answer.text_response:
        safe_answers.append(SafeAnswer(
            id=None,
            question_id=question.id,
            text=user_answer.text_response,
            image=None,
            is_user_answer=True
        ))
    else:
        for answer in question.answers:
            safe_answers.append(SafeAnswer(
                id=answer.id,
                question_id=answer.question_id,
                text="" if question.question_type == "text_answer" else answer.text,
                image=answer.image,
                is_user_answer=(answer.id in selected_answer_ids)
            ))
    
    return safe_answers


def build_safe_belbin_questions(belbin_questions: List[model.BelbinQuestion], belbin_scores: Dict) -> List[SafeBelbinQuestion]:
    """Сформировать SafeBelbinQuestion объекты с информацией о ответах пользователя."""
    return [
        SafeBelbinQuestion(
            id=bq.id,
            text=bq.text,
            block_number=bq.block_number,
            order=bq.order,
            test_id=bq.test_id,
            answers=[
                SafeBelbinAnswer(
                    id=ans.id,
                    question_id=ans.question_id,
                    text=ans.text,
                    user_score=belbin_scores.get(ans.id)
                )
                for ans in bq.answers
            ]
        )
        for bq in belbin_questions
    ]


def determine_test_status(db: Session, test: model.Test, employee_id: int, now: datetime) -> str:
    """Определить статус теста для пользователя."""
    if test.end_date and test.end_date < now:
        return "expired"
    
    result = db.query(model.TestResult).filter(
        model.TestResult.test_id == test.id,
        model.TestResult.employee_id == employee_id
    ).first()

    if result and result.completed_at:
        return "completed"
    elif result and result.started_at:
        return "in_progress"
    else:
        return "not_started"


def create_safe_test_schema(test: model.Test, status: str, 
                           questions: List[SafeQuestion], 
                           belbin_questions: List[SafeBelbinQuestion]) -> SafeTest:
    """Создать финальный SafeTest объект."""
    return SafeTest(
        id=test.id,
        title=test.title,
        description=test.description,
        is_active=test.is_active,
        created_at=test.created_at,
        updated_at=test.updated_at,
        end_date=test.end_date,
        status=status,
        questions=questions,
        belbin_questions=belbin_questions,
        time_limit_minutes=test.time_limit_minutes
    )

def answers_changed(old_answers, new_answers, belbin=False):
    if len(old_answers) != len(new_answers):
        return True
    # Сравниваем по id, text и order (если есть)
    old_sorted = sorted(old_answers, key=lambda x: x.get("id") or x.get("text"))
    new_sorted = sorted(new_answers, key=lambda x: x.get("id") or x.get("text"))

    for old_a, new_a in zip(old_sorted, new_sorted):
        if (
            old_a.get("text") != new_a.get("text") 
        ):
            return True
        if (old_a.get("is_correct") != new_a.get("is_correct")):
            return True
    return False

def get_changed_question_ids(db_test, update_data) -> tuple[Set[int], Set[int], Set[int], Set[int]]:
    old_questions = {q.id: q for q in db_test.questions}
    old_belbin_questions = {q.id: q for q in db_test.belbin_questions}

    new_questions = update_data.get("questions", [])
    new_belbin_questions = update_data.get("belbin_questions", [])
    for q in new_questions:
        print(q )
        print("\n")
    changed_question_ids = set()
    changed_belbin_question_ids = set()

    new_q_ids = set()
    for q_data in new_questions:
        q_id = q_data.get("id")
        if q_id:
            new_q_ids.add(q_id)
            old_q = old_questions.get(q_id)

            if old_q:
                is_answers_changed = answers_changed(
                    [dict(text=a.text, is_correct=a.is_correct, id=a.id) for a in old_q.answers],
                    q_data.get("answers", [])
                )
                if (q_data["text"] != old_q.text ) or is_answers_changed:
                    changed_question_ids.add(q_id)

    removed_q_ids = set(old_questions.keys()) - new_q_ids
    changed_question_ids.update(removed_q_ids)

    new_bq_ids = set()
    for bq_data in new_belbin_questions:
        bq_id = bq_data.get("id")
        if bq_id:
            new_bq_ids.add(bq_id)
            old_bq = old_belbin_questions.get(bq_id)
            if old_bq:
                is_answers_changed = answers_changed(
                    [dict(text=a.text, id=a.id) for a in old_bq.answers],
                    bq_data.get("answers", [])
                )
                if (
                bq_data["text"] != old_bq.text) or is_answers_changed:
                    changed_belbin_question_ids.add(bq_id)
    removed_bq_ids = set(old_belbin_questions.keys()) - new_bq_ids
    changed_belbin_question_ids.update(removed_bq_ids)

    return changed_question_ids, changed_belbin_question_ids, removed_q_ids, removed_bq_ids

def remove_changed_answers(db: Session, test_id: int, changed_q_ids: Set[int], changed_bq_ids: Set[int]):
    if changed_q_ids:
        ua_ids = db.query(UserAnswer.id).filter(
            UserAnswer.test_id == test_id,
            UserAnswer.question_id.in_(changed_q_ids)
        )
        db.query(UserAnswerItem).filter(
            UserAnswerItem.user_answer_id.in_(ua_ids)
        ).delete(synchronize_session=False)

        db.query(UserAnswer).filter(
            UserAnswer.test_id == test_id,
            UserAnswer.question_id.in_(changed_q_ids)
        ).delete(synchronize_session=False)

    if changed_bq_ids:
        db.query(UserBelbinAnswer).filter(
            UserBelbinAnswer.test_id == test_id,
            UserBelbinAnswer.question_id.in_(changed_bq_ids)
        ).delete(synchronize_session=False)

def handle_test_settings(db: Session, db_test, ts_data):
    if ts_data:
        if isinstance(ts_data, dict):
            if db_test.test_settings:
                for field, value in ts_data.items():
                    setattr(db_test.test_settings, field, value)
            else:
                db_settings = TestSettings(**ts_data)
                db.add(db_settings)
                db.commit()
                db.refresh(db_settings)
                db_test.test_settings_id = db_settings.id
        else:
            raise ValueError("test_settings должен быть dict")


def check_user_permissions(db: Session, user_id: str, is_admin: bool = False):
        employee = (
            db.query(Employee)
            .filter(Employee.clerk_id == user_id, Employee.is_admin == is_admin)
            .first()
            )
        if not employee:
            raise HTTPException(status_code=404, detail="User has not permissions")
        return employee

def get_current_user(db: Session, user_id: str):
    employee = (db.query(Employee).filter(Employee.clerk_id == user_id).first())
    return employee

def create_test(db: Session, test: schema.TestCreate, user_id: str):
    db_employee = check_user_permissions(db, user_id, True)

    settings = test.test_settings
    if settings:
        db_settings = TestSettings(
            min_questions=settings.min_questions,
            belbin_block=settings.belbin_block,
            belbin_questions_in_block=settings.belbin_questions_in_block,
            has_time_limit=settings.has_time_limit
        )
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
    else:
        db_settings = None

    db_test = model.Test(
        title=test.title,
        description=test.description,
        is_active=test.is_active,
        end_date=test.end_date,
        created_by=db_employee.id,
        test_settings_id=db_settings.id if db_settings else None,

    )
    db.add(db_test)
    db.commit()
    db.refresh(db_test)

    # Обычные вопросы
    for question in test.questions:
        db_question = model.Question(
            text=question.text,
            question_type=question.question_type,
            test_id=db_test.id,
            image=question.image,
            order=question.order,
            points=question.points
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)

        for answer in question.answers:
            db_answer = model.Answer(
                text=answer.text,
                is_correct=answer.is_correct,
                question_id=db_question.id,
                image=answer.image
            )
            db.add(db_answer)

    for belbin_q in test.belbin_questions:
        db_belbin_q = model.BelbinQuestion(
            text=belbin_q.text,
            block_number=belbin_q.block_number,
            order=belbin_q.order,
            test_id=db_test.id
        )
        db.add(db_belbin_q)
        db.commit()
        db.refresh(db_belbin_q)

        for answer in belbin_q.answers:
            db_belbin_answer = BelbinAnswer(
                text=answer.text,
                role_id=answer.role_id,
                question_id=db_belbin_q.id
            )
            db.add(db_belbin_answer)

    db.commit()
    return db_test

def calculate_test_result(db: Session, test_id: int, employee_id: int):

    calculate_test_score(db, test_id, employee_id)
    calculate_and_save_belbin_results(db, test_id, employee_id)
    return

def reset_test_for_employee(db: Session, test_id: int, employee_id: int):
    # Удалить BelbinTestResult

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    test = db.query(Test).filter(Test.id == test_id).first()

    if not employee or not test:
        raise ValueError("Тест или сотрудник не найдены")

    if employee not in test.assigned_to:
        raise ValueError("Тест не назначен данному сотруднику")


    belbin_results = db.query(BelbinTestResult).join(TestResult).filter(
        TestResult.test_id == test_id,
        TestResult.employee_id == employee_id
    ).all()
    for item in belbin_results:
        db.delete(item)

    # Удалить UserAnswerItem, связанные через UserAnswer
    user_answers = db.query(UserAnswer).filter_by(test_id=test_id, employee_id=employee_id).all()
    user_answer_ids = [ua.id for ua in user_answers]

    if user_answer_ids:
        db.query(UserAnswerItem).filter(UserAnswerItem.user_answer_id.in_(user_answer_ids)).delete(synchronize_session=False)

    # Удалить UserAnswer
    db.query(UserAnswer).filter_by(test_id=test_id, employee_id=employee_id).delete(synchronize_session=False)

    # Удалить UserBelbinAnswer
    db.query(UserBelbinAnswer).filter_by(test_id=test_id, employee_id=employee_id).delete(synchronize_session=False)

    # Удалить TestResult
    db.query(TestResult).filter_by(test_id=test_id, employee_id=employee_id).delete(synchronize_session=False)

    db.commit()

def calculate_test_score(db: Session, test_id: int, employee_id: int) -> int:
    score = 0
    max_score = 0

    questions = db.query(Question).filter(Question.test_id == test_id).all()

    for question in questions:
        points = question.points or 0  # если не задано, считаем 0
        if question.question_type == "single_choice":
            user_answer = (
                db.query(UserAnswer)
                .filter(
                    UserAnswer.test_id == test_id,
                    UserAnswer.employee_id == employee_id,
                    UserAnswer.question_id == question.id,
                )
                .first()
            )
            if not user_answer:
                continue
            # Получаем выбранный ответ из UserAnswerItem (один для single_choice)
            user_answer_item = (
                db.query(UserAnswerItem)
                .filter(UserAnswerItem.user_answer_id == user_answer.id)
                .first()
            )
            if user_answer_item and user_answer_item.answer.is_correct:
                score += points
            max_score += points


        elif question.question_type == "multiple_choice":
            correct_answer_ids = {a.id for a in question.answers if a.is_correct}
            if not correct_answer_ids:
                continue

            selected_answer_ids = {
                item.answer_id
                for item in (
                    db.query(UserAnswerItem)
                    .join(UserAnswer)
                    .filter(
                        UserAnswer.test_id == test_id,
                        UserAnswer.employee_id == employee_id,
                        UserAnswer.question_id == question.id,
                    )
                    .all()
                )
            }

            if selected_answer_ids == correct_answer_ids:
                score += points
            max_score += points

        elif question.question_type == "text_answer":
        # Получаем правильные варианты текста ответов
            correct_texts = {ans.text.strip().lower() for ans in question.answers if ans.is_correct}
            
            # Получаем ответ пользователя из UserAnswer
            user_answer = (
                db.query(UserAnswer)
                .filter(
                    UserAnswer.test_id == test_id,
                    UserAnswer.employee_id == employee_id,
                    UserAnswer.question_id == question.id
                )
                .first()
            )
            
            if user_answer and user_answer.text_response:
                user_text = user_answer.text_response.strip().lower()
                if user_text in correct_texts:
                    score += points
            max_score += points
        
        elif question.question_type == "belbin":
            # Белбин считается отдельно
            pass

    test_result = (
        db.query(TestResult)
        .filter_by(test_id=test_id, employee_id=employee_id)
        .first()
    )
    if not test_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден"
        )

    test_result.score = score
    test_result.max_score = max_score
    test_result.percent = (score / max_score * 100) if max_score > 0 else None

    db.commit()

    return score



def calculate_and_save_belbin_results(db: Session, test_id: int, employee_id: int):
    # Считаем баллы по ролям
    answers = db.query(UserBelbinAnswer).filter_by(
        test_id=test_id, employee_id=employee_id
    ).all()

    role_scores = {}
    if not answers:
        return

    for ans in answers:
        role = ans.answer.role  # BelbinAnswer -> BelbinRole
        if role:
            role_scores[role.id] = role_scores.get(role.id, 0) + (ans.score or 0)

    # Удаляем старые результаты, если есть
    test_result = db.query(TestResult).filter_by(test_id=test_id, employee_id=employee_id).first()
    if test_result:
        db.query(BelbinTestResult).filter_by(test_id=test_result.id).delete()

    # Сохраняем новые
    for role_id, score in role_scores.items():
        result = BelbinTestResult(
            test_id=test_result.id,
            role_id=role_id,
            total_score=score
        )
        db.add(result)

    db.commit()

def get_test(db: Session, test_id: int, user_id: str):
    return db.query(model.Test).filter(
        model.Test.id == test_id,
        model.Test.created_by == user_id
    ).first()


def get_tests_by_position(db: Session, position_id: int, user_id: str):
    return db.query(model.Test).filter(
        model.Test.position_id == position_id,
        model.Test.is_active == True,
        model.Test.created_by == user_id
    ).all()
def update_test(db: Session, test_id: int, test_update: schema.TestCreate, user_id: str):
    # Проверка прав и получение теста
    db_employee = check_user_permissions(db, user_id, True)
    db_test = get_test_for_update(db, test_id, db_employee.id)
    if not db_test:
        return None

    # Подготовка данных обновления
    update_data = test_update.model_dump(exclude_unset=True)
    
    # Обработка изменений вопросов и ответов
    process_question_changes(db, test_id, db_test, update_data)
    
    # Обновление основных полей теста
    update_test_fields(db_test, update_data)
    if test_update.test_settings.has_time_limit == False:
        db_test.time_limit_minutes = None
    # Фиксация изменений
    db.commit()
    db.refresh(db_test)
    return db_test


def get_test_for_update(db: Session, test_id: int, employee_id: int) -> model.Test | None:
    """Получить тест для обновления с проверкой владельца."""
    return db.query(model.Test).filter(
        model.Test.id == test_id,
        model.Test.created_by == employee_id
    ).first()


def process_question_changes(db: Session, test_id: int, db_test: model.Test, update_data: dict):
    """Обработка изменений вопросов и связанных данных."""
    # Определение измененных вопросов
    changed_question_ids, changed_belbin_question_ids, removed_q_ids, removed_bq_ids = get_changed_question_ids(
        db_test, update_data
    )
    
    # Удаление ответов на измененные вопросы
    remove_changed_answers(
        db, test_id,
        changed_question_ids,
        changed_belbin_question_ids
    )

    # Очистка результатов теста при значительных изменениях
    if changed_question_ids or changed_belbin_question_ids:
        db.query(model.TestResult).filter(model.TestResult.test_id == test_id).delete(synchronize_session=False)

    # Обновление настроек теста
    handle_test_settings(db, db_test, update_data.pop("test_settings", None))

    # Обновление обычных вопросов
    if "questions" in update_data:
        update_regular_questions(db_test, update_data["questions"])

    # Обновление вопросов Белбина
    if "belbin_questions" in update_data:
        update_belbin_questions(db_test, update_data["belbin_questions"])


def should_clear_test_results(update_data: dict, removed_q_ids: set, removed_bq_ids: set) -> bool:
    """Определить, нужно ли очищать результаты теста."""
    has_new_questions = any(q.get("id") is None 
                    for q in update_data.get("questions", []) + update_data.get("belbin_questions", []))
    return removed_q_ids or removed_bq_ids or has_new_questions


def update_test_fields(db_test: model.Test, update_data: dict):
    """Обновление основных полей теста."""

    now = datetime.now(timezone.utc)

    old_end_date = db_test.end_date
    new_end_date = update_data.get("end_date")

    for field, value in update_data.items():
        if field in ["questions", "belbin_questions", "test_settings"]:
            continue
        setattr(db_test, field, value)
    db_test.updated_at = now

    if new_end_date and new_end_date != old_end_date and new_end_date > now:
        db_test.status = "draft"

def update_regular_questions(db_test: model.Test, questions_data: list[dict]):
    """Обновление обычных вопросов теста."""
    existing_questions = {q.id: q for q in db_test.questions}
    new_questions = []

    for q_data in questions_data:
        answers_data = q_data.pop("answers", [])
        q_id = q_data.get("id")

        if q_id and q_id in existing_questions:
            update_existing_question(existing_questions[q_id], q_data, answers_data)
        else:
            new_questions.append(create_new_question(q_data, answers_data))

    # Удаление отсутствующих вопросов
    new_q_ids = {q.get("id") for q in questions_data if q.get("id")}
    remove_missing_questions(db_test, new_q_ids)

    # Добавление новых вопросов
    db_test.questions.extend(new_questions)


def update_existing_question(question: model.Question, q_data: dict, answers_data: list[dict]):
    """Обновление существующего вопроса и его ответов."""
    question.text = q_data["text"]
    # обновляем другие поля при необходимости

    existing_answers = {answer.id: answer for answer in question.answers}
    incoming_ids = set()
    
    for a_data in answers_data:
        a_id = a_data.get("id")
        if a_id and a_id in existing_answers:
            # Обновляем существующий ответ
            ans = existing_answers[a_id]
            ans.text = a_data["text"]
            ans.image = a_data.get("image")  # если нужно
            incoming_ids.add(a_id)
        else:
            # Добавляем новый ответ
            a_data.pop("id", None)  # на всякий случай
            new_answer = model.Answer(**a_data)
            question.answers.append(new_answer)

    # Удаляем ответы, которых нет в входных данных
    question.answers[:] = [ans for ans in question.answers if ans.id is None or ans.id in incoming_ids]



def create_new_question(q_data: dict, answers_data: list[dict]) -> model.Question:
    """Создание нового вопроса."""
    q_data.pop("id", None)
    question = model.Question(**q_data)
    for a_data in answers_data:
        a_data.pop("id", None)
        question.answers.append(model.Answer(**a_data))
    return question


def remove_missing_questions(db_test: model.Test, new_q_ids: set[int]):
    """Удаление вопросов, которых нет в новых данных."""
    for q in db_test.questions[:]:
        if q.id not in new_q_ids:
            db_test.questions.remove(q)


def update_belbin_questions(db_test: model.Test, belbin_questions_data: list[dict]):
    """Обновление вопросов Белбина."""
    existing_bq = {bq.id: bq for bq in db_test.belbin_questions}
    new_belbin_questions = []

    for bq_data in belbin_questions_data:
        answers_data = bq_data.pop("answers", [])
        bq_id = bq_data.get("id")

        if bq_id and bq_id in existing_bq:
            update_existing_belbin_question(existing_bq[bq_id], bq_data, answers_data)
        else:
            new_belbin_questions.append(create_new_belbin_question(bq_data, answers_data))

    # Удаление отсутствующих вопросов
    incoming_bq_ids = {bq.get("id") for bq in belbin_questions_data if bq.get("id")}
    remove_missing_belbin_questions(db_test, incoming_bq_ids)

    # Добавление новых вопросов
    db_test.belbin_questions.extend(new_belbin_questions)


def update_existing_belbin_question(belbin_question: model.BelbinQuestion, bq_data: dict, answers_data: list[dict]):
    """Обновление существующего вопроса Белбина."""
    belbin_question.text = bq_data["text"]
    belbin_question.block_number = bq_data["block_number"]
    belbin_question.order = bq_data["order"]
    
    # Обновление ответов
    belbin_question.answers.clear()
    for ba_data in answers_data:
        ba_data.pop("id", None)
        belbin_question.answers.append(BelbinAnswer(**ba_data))


def create_new_belbin_question(bq_data: dict, answers_data: list[dict]) -> model.BelbinQuestion:
    """Создание нового вопроса Белбина."""
    bq_data.pop("id", None)
    belbin_question = model.BelbinQuestion(**bq_data)
    for ba_data in answers_data:
        ba_data.pop("id", None)
        belbin_question.answers.append(BelbinAnswer(**ba_data))
    return belbin_question


def remove_missing_belbin_questions(db_test: model.Test, incoming_bq_ids: set[int]):
    """Удаление вопросов Белбина, которых нет в новых данных."""
    for bq in db_test.belbin_questions[:]:
        if bq.id not in incoming_bq_ids:
            db_test.belbin_questions.remove(bq)


def get_assigned_tests_for_employee(db: Session, user_id: str) -> List[SafeTest]:
    """Получить список назначенных тестов для сотрудника с информацией о статусе и ответах."""
    now = datetime.now(timezone.utc)
    user = get_current_user(db, user_id)

    # Получаем все назначенные тесты
    tests = get_assigned_tests(db, user_id)
    
    result_schemas = []
    for test in tests:
        if test.status == "draft":
            continue
        
        # Получаем данные о ответах пользователя
        user_answers_data = get_user_answers_data(db, test.id, user.id)
        belbin_answers_data = get_belbin_answers_data(db, test.id, user.id)
        
        # Формируем вопросы с ответами
        safe_questions = build_safe_questions(test.questions, user_answers_data)
        safe_belbin_questions = build_safe_belbin_questions(test.belbin_questions, belbin_answers_data)
        
        # Определяем статус теста
        status = determine_test_status(db, test, user.id, now)
        
        # Собираем финальную схему
        result_schemas.append(create_safe_test_schema(test, status, safe_questions, safe_belbin_questions))

    return result_schemas

def get_assigned_test_for_employee(db: Session, user_id: str, test_id: int):
    """Получить данные одного назначенного теста для сотрудника с информацией о статусе и ответах."""
    now = datetime.now(timezone.utc)
    user = get_current_user(db, user_id)
    # Получаем тест по id и проверяем, что он назначен этому сотруднику
    test = db.query(Test).filter(
        Test.id == test_id,
        Test.status != "draft",  # можно сразу исключить черновики
        Test.assigned_users.any(id=user.id)  # или аналогичная проверка назначений
    ).first()

    if not test:
        return None  # Тест не найден или не назначен

    # Получаем данные о ответах пользователя
    user_answers_data = get_user_answers_data(db, test.id, user.id)
    belbin_answers_data = get_belbin_answers_data(db, test.id, user.id)

    # Формируем вопросы с ответами
    safe_questions = build_safe_questions(test.questions, user_answers_data)
    safe_belbin_questions = build_safe_belbin_questions(test.belbin_questions, belbin_answers_data)

    # Определяем статус теста
    status = determine_test_status(db, test, user.id, now)

    # Формируем и возвращаем схему
    return create_safe_test_schema(test, status, safe_questions, safe_belbin_questions)

def get_user_test_results(db: Session, user_id: str) -> List[TestResult]:
       return (
        db.query(TestResult)
        .join(TestResult.test)
        .join(Test.assigned_to)
        .filter(Employee.clerk_id == user_id)
        .all()
    )



def get_assigned_tests(db: Session, user_id: str) -> List[model.Test]:
    """Получить список тестов, назначенных пользователю."""
    user = get_current_user(db, user_id)
    now = datetime.now(timezone.utc)

    tests_results = get_user_test_results(db, user_id)
    auto_complete_expired_tests(tests_results, db, now)

    tests = (
        db.query(model.Test)
        .join(model.Test.assigned_to)
        .filter(Employee.clerk_id == user_id)
        .options(
            selectinload(model.Test.questions).selectinload(model.Question.answers),
            selectinload(model.Test.belbin_questions)
                .selectinload(model.BelbinQuestion.answers)
                .selectinload(BelbinAnswer.role),
            selectinload(model.Test.assigned_to),
            selectinload(model.Test.test_settings),
            selectinload(model.Test.results)
        )
        .all()
    )


    return tests


def get_user_answers_data(db: Session, test_id: int, employee_id: int) -> Tuple[Dict, Dict, Dict]:
    """Получить данные о ответах пользователя на обычные вопросы."""
    # Получаем UserAnswer записи
    user_answers = db.query(UserAnswer).filter(
        and_(
            UserAnswer.test_id == test_id,
            UserAnswer.employee_id == employee_id
        )
    ).all()

    # Сопоставляем question_id с UserAnswer
    user_answers_by_qid = {ua.question_id: ua for ua in user_answers}
    user_answer_ids = [ua.id for ua in user_answers]

    # Получаем UserAnswerItem записи
    user_answer_items = db.query(UserAnswerItem).filter(
        UserAnswerItem.user_answer_id.in_(user_answer_ids)
    ).all()

    # Сопоставляем question_id с выбранными answer_id
    question_id_by_user_answer_id = {ua.id: ua.question_id for ua in user_answers}
    answer_ids_by_question = defaultdict(set)
    
    for item in user_answer_items:
        qid = question_id_by_user_answer_id.get(item.user_answer_id)
        if qid is not None:
            answer_ids_by_question[qid].add(item.answer_id)

    return user_answers_by_qid, answer_ids_by_question


def change_test_status(db: Session, test_id: int, test_status: schema.TestStatusUpdate, user_id: str):
    db_employee = check_user_permissions(db, user_id, True)

    db_test = db.query(model.Test).filter(
        model.Test.id == test_id,
        model.Test.created_by == db_employee.id
    ).first()

    if not db_test:
        return None

    # Обработка изменения статуса
    new_status = test_status.status

    if new_status == "draft":
        # Завершение теста для всех пользователей
        test_results = db.query(TestResult).filter(
            TestResult.test_id == test_id,
            TestResult.is_completed == False
        ).all()

        for result in test_results:
            complete_test(db, user_id=result.employee.clerk_id, test_id=test_id)

    elif new_status == "active":
        # Удаление всех результатов теста
        db.query(TestResult).filter(
            TestResult.test_id == test_id
        ).delete(synchronize_session=False)

    db_test.status = new_status
    db.commit()
    db.refresh(db_test)

    return {"id": db_test.id, "status": db_test.status}


def delete_test(db: Session, test_id: int, user_id: str):
    user = check_user_permissions(db, user_id, True)

    db_test = db.query(model.Test).filter(
        model.Test.id == test_id,
        model.Test.created_by == user.id
    ).first()

    if not db_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест не найден или у вас нет прав на удаление"
        )

    try:
        db.delete(db_test)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении теста: {str(e)}"
        )
    return {"detail": "Тест успешно удалён"}



def get_tests(db: Session, user_id: str):
    db_employee = check_user_permissions(db, user_id, True)
    now = datetime.now(timezone.utc)

    tests = db.query(Test).options(
        selectinload(Test.questions).selectinload(Question.answers),
        selectinload(Test.belbin_questions).selectinload(BelbinQuestion.answers).selectinload(BelbinAnswer.role),
        selectinload(Test.assigned_to),
        selectinload(Test.test_settings),
    ).filter(Test.created_by == db_employee.id).all()

    result_schemas = []

    for test in tests:
        # ⏰ Проверка истечения времени
        if test.status != "expired":
            test_end_time = test.end_date
            if not test_end_time and test.time_limit_minutes:
                test_end_time = test.created_at + timedelta(minutes=test.time_limit_minutes)
            
            if test_end_time and now > test_end_time:
                test.status = "expired"
                db.add(test)  
                db.commit()

        for bq in test.belbin_questions:
            for answer in bq.answers:
                answer.role_name = answer.role.name if answer.role else None
        
        schema = TestSchema.model_validate(test, from_attributes=True)
        result_schemas.append(schema)

    return result_schemas  

# def get_tests_by_assigned_to(db: Session, assigned_to: int, user_id: str):
#     now = datetime.now(timezone.utc)

#     tests = db.query(model.Test).options(
#         selectinload(model.Test.questions).selectinload(model.Question.answers),
#         selectinload(model.Test.belbin_questions).selectinload(model.BelbinQuestion.answers).selectinload(model.BelbinAnswer.role),
#         selectinload(model.Test.assigned_to),
#         selectinload(model.Test.test_settings),
#     ).join(model.Test.assigned_to).filter(
#         model.Employee.id == assigned_to,
#     ).all()

#     result_schemas = []

#     for test in tests:
#         # Назначаем role_name для Белбина
#         for bq in test.belbin_questions:
#             for answer in bq.answers:
#                 answer.role_name = answer.role.name if answer.role else None

#         # Получаем результат теста для этого сотрудника
#         result = db.query(model.TestResult).filter(
#             model.TestResult.test_id == test.id,
#             model.TestResult.employee_id == assigned_to
#         ).first()

#         # Логика определения статуса
#         if result and result.completed_at:
#             status = "completed"
#         elif result and result.started_at:
#             status = "in_progress"
#         elif test.test_settings and test.end_date and test.end_date < now:
#             status = "expired"
#         else:
#             status = "not_started"
#         print(status)
#         schema = TestSchema.model_validate(test, from_attributes=True)
#         schema.status = status
#         result_schemas.append(schema)

#     return result_schemas


def get_completed_tests_for_employee(db: Session, user_id: str):
    employee = get_current_user(db, user_id)

    return (
        db.query(model.TestResult)
        .filter(model.TestResult.employee_id == employee.id, model.TestResult.is_completed == True)
        .all()
    )

def validate_test_availability(db, test, employee):
    
    now = datetime.now(timezone.utc)

    # 1. Проверка глобального срока доступности
    if test.end_date and now > test.end_date:
        raise HTTPException(status_code=400, detail="Срок действия теста истёк")

    if test.status == "draft":
        raise HTTPException(status_code=400, detail="Тест приостановлен")
    # 2. Проверка индивидуального лимита времени
    if test.time_limit_minutes:
        test_result = db.query(TestResult).filter_by(
            test_id=test.id,
            employee_id=employee.id
        ).first()

        if not test_result:
            raise HTTPException(status_code=400, detail="Результат теста не найден. Тест ещё не был начат")

        if not test_result.started_at:
            raise HTTPException(status_code=400, detail="Тест не был начат должным образом")
        
        started_at = test_result.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        individual_deadline = started_at + timedelta(minutes=test.time_limit_minutes)
        if now > individual_deadline:
            raise HTTPException(status_code=400, detail="Время на выполнение теста истекло")


def create_user_answer(db: Session, user_answer: UserAnswerCreate, user_id: str):
    employee = get_current_user(db, user_id)

    test = db.query(model.Test).filter(
        model.Test.id == user_answer.test_id,
        model.Test.is_active == True,
    ).first()
    if not test:
        raise HTTPException(status_code=400, detail="Test not available")

    validate_test_availability(db, test, employee)
    question = None

    if user_answer.question_type == "belbin":
        question = db.query(model.BelbinQuestion).filter(
            model.BelbinQuestion.id == user_answer.question_id,
            model.BelbinQuestion.test_id == user_answer.test_id
        ).first()
        if not question:
            raise HTTPException(status_code=404, detail="Belbin question not found in this test")
    elif user_answer.question_type in ("single_choice", "multiple_choice", "text_answer"):
        question = db.query(model.Question).filter(
            model.Question.id == user_answer.question_id,
            model.Question.test_id == user_answer.test_id,
            model.Question.question_type == user_answer.question_type
        ).first()
        if not question:
            raise HTTPException(status_code=404, detail=f"Question of type '{user_answer.question_type}' not found in this test")
    else:
        raise HTTPException(status_code=400, detail="Unknown question_type")

    # Валидация и сохранение ответа
    if user_answer.question_type in ("single_choice", "multiple_choice", "text_answer"):
        valid_answer_ids = {a.id for a in question.answers}
        for answer_id in user_answer.answer_ids:
            if answer_id not in valid_answer_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Answer ID {answer_id} doesn't belong to this question"
                )

        db_answer = db.query(UserAnswer).filter_by(
            employee_id=employee.id,
            test_id=user_answer.test_id,
            question_id=user_answer.question_id
        ).first()

        if db_answer:
            db.query(UserAnswerItem).filter_by(user_answer_id=db_answer.id).delete()
            db_answer.text_response = user_answer.text_response
        else:
            db_answer = UserAnswer(
                test_id=user_answer.test_id,
                employee_id=employee.id,
                question_id=user_answer.question_id,
                text_response=user_answer.text_response
            )
            db.add(db_answer)
            db.commit()
            db.refresh(db_answer)

        for answer_id in user_answer.answer_ids:
            db_item = UserAnswerItem(
                user_answer_id=db_answer.id,
                answer_id=answer_id
            )
            db.add(db_item)

        db.commit()
        return db_answer

    elif user_answer.question_type == "belbin":
        db.query(UserBelbinAnswer).filter_by(
            employee_id=employee.id,
            test_id=user_answer.test_id,
            question_id=user_answer.question_id
        ).delete()

        if not user_answer.answer_ids and user_answer.text_response:
            try:
                parsed_answers = json.loads(user_answer.text_response)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid text_response format")

            for answer_id, score in parsed_answers:
                belbin_answer = db.query(BelbinAnswer).filter(
                    BelbinAnswer.id == answer_id,
                    BelbinAnswer.question_id == question.id
                ).first()
                if not belbin_answer:
                    raise HTTPException(status_code=400, detail=f"Invalid Belbin answer id {answer_id}")

                db_belbin_answer = UserBelbinAnswer(
                    test_id=user_answer.test_id,
                    employee_id=employee.id,
                    question_id=user_answer.question_id,
                    answer_id=answer_id,
                    score=score
                )
                db.add(db_belbin_answer)
        else:
            for answer_id in user_answer.answer_ids:
                belbin_answer = db.query(BelbinAnswer).filter(
                    BelbinAnswer.id == answer_id,
                    BelbinAnswer.question_id == question.id
                ).first()
                if not belbin_answer:
                    raise HTTPException(status_code=400, detail=f"Invalid Belbin answer id {answer_id}")

                db_belbin_answer = UserBelbinAnswer(
                    test_id=user_answer.test_id,
                    employee_id=employee.id,
                    question_id=user_answer.question_id,
                    role_id=belbin_answer.role_id,
                    score=belbin_answer.score
                )
                db.add(db_belbin_answer)

        db.commit()
        return {"status": "Belbin structured answer saved"}



def complete_test(db: Session, user_id: str, test_id: int):
    employee = get_current_user(db, user_id)

    test_result = db.query(TestResult).filter(
        TestResult.test_id == test_id,
        TestResult.employee_id == employee.id
    ).first()

    if not test_result:
        raise HTTPException(status_code=404, detail="Результат теста не найден")

    if test_result.is_completed:
        return {"message": "Тест уже завершён", "status": "completed"}

    test = db.query(model.Test).filter(model.Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    # Если есть лимит времени, устанавливаем completed_at как started_at + time_limit
    if test.time_limit_minutes and test_result.started_at:
        test_result.completed_at = test_result.started_at + timedelta(minutes=test.time_limit_minutes)
    else:
        test_result.completed_at = datetime.now(timezone.utc)


    test_result.is_completed = True
    test_result.completed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(test_result)

    calculate_test_result(db, test_id, employee.id)

    return {
        "message": "Тест завершён",
        "status": "completed",
   
    }

def start_test(db: Session, user_id: str, test_id: int):
    employee = get_current_user(db, user_id)

    test = (
        db.query(Test)
        .options(
            selectinload(Test.questions).selectinload(Question.answers),
            selectinload(Test.belbin_questions)
        )
        .filter(Test.id == test_id)
        .first()
    )
    now = datetime.now(timezone.utc)

    if test.end_date and now > test.end_date:
        raise HTTPException(status_code=400, detail="Срок действия теста истёк")

    if test.status == "draft":
        raise HTTPException(status_code=400, detail="Тест приостановлен")
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    # Проверка на повторный запуск
    existing_result = db.query(TestResult).filter(
        TestResult.test_id == test_id,
        TestResult.employee_id == employee.id
    ).first()

    now = datetime.now(timezone.utc)
    end_date = test.end_date
    if existing_result:
        if existing_result.is_completed:
            status = "completed"
        elif end_date and now > end_date:
            status = "expired"
        else:
            status = "in_progress"
    else:
        if end_date and now > end_date:
            status = "expired"
        else:
            # Тест не начинался — создаём TestResult
            test_result = TestResult(
                test_id=test_id,
                employee_id=employee.id,
                is_completed=False,
                started_at=now
            )
            db.add(test_result)
            db.commit()
            db.refresh(test_result)
            status = "in_progress"

    started_at = existing_result.started_at if existing_result else now
    user_answers_data = get_user_answers_data(db, test.id, employee.id)
    belbin_answers_data = get_belbin_answers_data(db, test.id, employee.id)

    # Строим безопасные схемы вопросов
    safe_questions = build_safe_questions(test.questions, user_answers_data)
    safe_belbin_questions = build_safe_belbin_questions(test.belbin_questions, belbin_answers_data)

    # Возвращаем финальную схему
    return create_safe_test_schema(
        test=test,
        status=status,
        safe_questions=safe_questions,
        safe_belbin_questions=safe_belbin_questions,
        started_at=started_at
    )


def assign_test_to_employees(db: Session, assignment: TestAssignmentCreate):
    values = [
        {"employee_id": item.employee_id, "test_id": item.test_id}
        for item in assignment.assignments
    ]

    stmt = insert(model.test_assignments).values(values)
    try:
        db.execute(stmt)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Назначение уже существует"
        )
    
    return {"message": "Тест успешно назначен"}

def get_test_results_with_employee(db: Session, test_id: int, user_id: int):
    employee = get_current_user(db, user_id)

    stmt = (
        select(TestResult)
        .join(TestResult.test)
        .options(
            joinedload(TestResult.employee)
                .joinedload(Employee.position)
                .joinedload(Position.belbin_requirements)
                .joinedload(BelbinPositionRequirement.role),

            joinedload(TestResult.belbin_results)
                .joinedload(BelbinTestResult.role),

            joinedload(TestResult.test)
        )
        .where(
            TestResult.test_id == test_id,
            Test.created_by == employee.id
        )
    )

    results = db.execute(stmt).unique().scalars().all()

    # Завершаем просроченные тесты
    auto_complete_expired_tests(results, db)

    # Возвращаем только завершённые
    for r in results:
        r.time_limit_minutes = r.test.time_limit_minutes

    # Валидация и возврат
    return [TestResultSchema.model_validate(r) for r in results if r.is_completed]


def remove_test_assignments(db: Session, assignment: TestAssignmentCreate):
    # Извлекаем test_id и список employee_id из переданных назначений
    test_ids = set(item.test_id for item in assignment.assignments)
    employee_ids = [item.employee_id for item in assignment.assignments]

    # ВАЖНО: в данном примере предполагается, что все назначения относятся к одному тесту
    # Если может быть несколько тестов, нужно изменять логику accordingly
    if len(test_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Все назначения должны относиться к одному тесту"
        )
    test_id = test_ids.pop()

    stmt = (
        delete(model.test_assignments)
        .where(
            model.test_assignments.c.test_id == test_id,
            model.test_assignments.c.employee_id.in_(employee_ids),
        )
    )

    result = db.execute(stmt)
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Назначения не найдены для удаления",
        )

    return {"message": f"Удалено назначений: {result.rowcount}"}