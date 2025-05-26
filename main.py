from fastapi import FastAPI, Request, Body
from fastapi.params import Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import status
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Union
import uvicorn
import requests
import logging
from schemas import test as test_schemas
import models, schemas, crud
from db.database import engine, get_db
from initial_data import init_belbin_roles, init_belbin_questions, init_position_requirements
from get_current_user import get_current_user, UserData
import os
app = FastAPI()
from sqlalchemy.orm import DeclarativeBase
import httpx
from auth import jwks_cache, JWKS_URL, create_clerk_user, delete_clerk_user, update_clerk_user, CLERK_ISSUER
from invite_user_email import invite_user_via_clerk

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass
from fastapi.middleware.cors import CORSMiddleware

app_host_url = os.getenv("APP_HOST_URL", "http://localhost:3000")  # Значение по умолчанию

app.add_middleware(
    CORSMiddleware,
    allow_origins=[app_host_url],  # вместо '*'
    allow_credentials=True,                  # разрешить куки и Authorization

    allow_methods=["*"],  # Явное указание
allow_headers=["*"] ,
    expose_headers=["*"],  # Для доступа к кастомным заголовкам
    max_age=600,  # Время кэширования preflight

)

app.mount("/static", StaticFiles(directory="static"), name="static")
@app.on_event("startup")
async def load_jwks():
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        jwks_cache["keys"] = response.json()["keys"]

# Модель для данных из Web App
class QuizResult(BaseModel):
    user_id: int
    answers: list[str]

# @app.on_event("startup")
# def startup_event():
#     db = next(get_db())
#     # Инициализация данных
#     Base.metadata.create_all(bind=engine)

#     if not db.query(models.BelbinRole).first():
#         init_belbin_roles(db)
#         init_belbin_questions(db)
#         # init_position_requirements(db)
#     db.close()

# Главная страница (HTML)
@app.get("/", response_class=HTMLResponse)
async def read_web_app():
    with open("static/index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(file.read())

# @app.get("/api/quiz", response_model=Test)
# async def get_quiz(questions: int = 5):
#     return generate_quiz(questions)

# API для сохранения результатов
@app.post("/submit-quiz")
async def save_quiz(result: QuizResult):
    print(f"User {result.user_id} answered: {result.answers}")
    return {"status": "ok"}


# Роутеры для должностей
@app.post("/positions/", response_model=schemas.Position, status_code=status.HTTP_201_CREATED)
def create_position(position: schemas.PositionCreate, current_user: UserData = Depends(get_current_user),
    db: Session = Depends(get_db)):
    return crud.create_position(db=db, position=position, user_id=current_user.user_id)

@app.put("/positions/{position_id}", response_model=schemas.Position)
def update_position(position_id: int, position: schemas.PositionCreate, current_user: UserData = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.update_position(db=db, position_id=position_id, position_update=position, user_id=current_user.user_id)


@app.delete("/positions/{position_id}", response_model=schemas.Position, status_code=status.HTTP_200_OK)
def delete_position(position_id: int, current_user: UserData = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.delete_position(db=db, position_id=position_id, user_id=current_user.user_id)


@app.get("/positions/", response_model=List[schemas.Position], status_code=status.HTTP_200_OK)
def get_positions(db: Session = Depends(get_db),  current_user: UserData = Depends(get_current_user)):
    return crud.get_positions(db, current_user.user_id)

@app.post("/employees/local/", status_code=status.HTTP_201_CREATED)
def create_employee_local(
    employee: schemas.EmployeeCreate = Depends(schemas.EmployeeCreate.as_form), photo: UploadFile = File(None),    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if photo is not None:
        photo = photo.file.read()
    # Локальное создание сотрудника без взаимодействия с Clerk
    return crud.create_employee(
        db=db,
        employee=employee,
        photo=photo,
        user_id=current_user.user_id,
        employee_id=None  # или какое-то другое значение, если не нужно
    )

#Add delete old accounts
@app.post("/employees/clerk/", status_code=status.HTTP_201_CREATED)
def create_employees_clerk_batch(
    employees: List[schemas.EmployeeCreateWithAccount] = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    results = []
    errors = []
    clerk_user_created = False

    for idx, employee in enumerate(employees):
        try:
            employee_create_data = employee.model_dump(
                exclude={"type", "username", "password"}
            )
            employee_create = schemas.EmployeeCreate(**employee_create_data)

            if employee.type == "link":
                if not employee.email:
                    raise HTTPException(status_code=422, detail="Email обязателен для регистрации по ссылке")
                response = invite_user_via_clerk(employee.email, f"{CLERK_ISSUER}/sign-up")
                employee_id = response["id"]

            elif employee.type in ("email_password", "username_password"):
                if employee.type == "email_password" and not employee.email:
                    raise HTTPException(status_code=422, detail="Email обязателен для регистрации по email + пароль")
                if employee.type == "username_password" and not employee.username:
                    raise HTTPException(status_code=422, detail="Логин обязателен для регистрации по логину + пароль")
                if not employee.password:
                    raise HTTPException(status_code=422, detail="Пароль обязателен для регистрации")

                clerk_user = create_clerk_user(
                    email=employee.email if employee.email != "" else None,
                    username=employee.username if employee.type == "username_password" else None,
                    password=employee.password,
                    first_name=employee.first_name,
                    last_name=employee.last_name,
                    is_admin=employee.is_admin
                )
                clerk_user_created = True

                employee_id = clerk_user["id"]

            else:
                raise HTTPException(status_code=400, detail="Неподдерживаемый тип создания аккаунта")
            employee_create.clerk_id = employee_id
            created_employee = crud.update_employee(
                db=db,
                employee_update=employee_create,
                user_id=current_user.user_id,
                photo=None,
                employee_id = employee.id
            )

            # Получаем должность из БД по position_id
            position = db.query(models.Position).filter(models.Position.id == created_employee.position_id).first()
            position_title = position.title if position else None

            full_name = f"{created_employee.last_name} {created_employee.first_name}"
            if created_employee.middle_name:
                full_name += f" {created_employee.middle_name}"

            results.append({
                "id": created_employee.id,
                "fullName": full_name,
                "username": employee.username if hasattr(employee, "username") else None,
                "password": employee.password if hasattr(employee, "password") else None,
                "email": employee.email,
                "positionTitle": position_title,
            })

        except requests.HTTPError as e:
            try:
                response_data = e.response.json()
            except Exception:
                response_data = {}

            print("❌ Clerk HTTP error:", response_data)
            errors_list = response_data.get("errors", [])
            error_msg = "Неизвестная ошибка от Clerk"

            if errors_list:
                for err_detail in errors_list:
                    if err_detail.get("code") == "form_identifier_exists":
                        error_msg = "Пользователь с таким email уже зарегистрирован"
                    elif err_detail.get("code") == "duplicate_record":
                        error_msg = "Приглашение уже отправлено"
                    else:
                        error_msg = err_detail.get("long_message") or err_detail.get("message") or error_msg
            else:
                error_msg = response_data.get("message") or error_msg

            errors.append({"index": idx, "error": error_msg})

        except HTTPException as he:
            if clerk_user_created and employee_id:
                delete_clerk_user(employee_id)
            errors.append({"index": idx, "error": he.detail})

        except Exception as ex:
            import traceback
            print(f"❌ Unknown error on employee index {idx}: {ex}")
            traceback.print_exc()
            if clerk_user_created and employee_id:
                delete_clerk_user(employee_id)

            errors.append({"index": idx, "error": str(ex)})

    return {"results": results, "errors": errors}


# @router.post("/employees/", status_code=status.HTTP_201_CREATED)
# def create_employee(
#     employee: schemas.EmployeeCreateWithAccount = Body(...),
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user)
# ):
#     if employee.type == "link":
#         # Приглашение пользователя по email (без пароля)
#         if not employee.email:
#             raise HTTPException(status_code=422, detail="Email обязателен для регистрации по ссылке")
#         try:
#             response = invite_user_via_clerk(employee.email, f"{CLERK_ISSUER}/sign-up")
#         except requests.HTTPError as e:
#             response_data = e.response.json()
#             errors = response_data.get("errors", [])
#             error_msg = "Unknown error"
#             if errors:
#                 first_error = errors[0]
#                 error_code = first_error.get("code")
#                 if error_code == "form_identifier_exists":
#                     raise HTTPException(
#                         status_code=400,
#                         detail={"message": "Пользователь с таким email уже зарегистрирован"}
#                     )
#                 elif error_code == "duplicate_record":
#                     raise HTTPException(
#                         status_code=400,
#                         detail={"message": "Приглашение уже отправлено"}
#                     )
#                 error_msg = first_error.get("long_message", error_msg)
#                 logger.error(f"Clerk invitation failed: {e.response.status_code} - {e.response.text}")
#                 raise HTTPException(
#                     status_code=400,
#                     detail={"message": "Ошибка при приглашении пользователя", "error_message": error_msg}
#                 )

#         return crud.create_employee(
#             db=db,
#             employee=employee,
#             user_id=current_user.user_id,
#             employee_id=response["id"]
#         )

#     elif employee.type in ("email_password", "username_password"):
#         # Создание пользователя с логином/паролем или email/паролем
#         if employee.type == "email_password" and not employee.email:
#             raise HTTPException(status_code=422, detail="Email обязателен для регистрации по email + пароль")
#         if employee.type == "username_password" and not employee.username:
#             raise HTTPException(status_code=422, detail="Логин обязателен для регистрации по логину + пароль")
#         if not employee.password:
#             raise HTTPException(status_code=422, detail="Пароль обязателен для регистрации")

#         try:
#             clerk_user = create_clerk_user(
#                 email=employee.email,
#                 username=employee.username if employee.type == "username_password" else None,
#                 password=employee.password,
#                 first_name=employee.first_name,
#                 last_name=employee.last_name,
#                 is_admin=employee.is_admin
#             )
#         except requests.HTTPError as e:
#             logger.error(f"Clerk user creation failed: {e.response.status_code} - {e.response.text}")
#             raise HTTPException(
#                 status_code=400,
#                 detail={ 
#                     "message": "Ошибка при создании clerk пользователя", 
#                     "error_message": e.response.json().get('message', 'Unknown error') 
#                 }
#             )

#         return crud.create_employee(
#             db=db,
#             employee=employee,
#             user_id=current_user.user_id,
#             employee_id=clerk_user["id"]
#         )

#     else:
#         raise HTTPException(status_code=400, detail="Неподдерживаемый тип создания аккаунта")


@app.delete("/tests/{test_id}/employees/{employee_id}/reset")
def reset_test(test_id: int, employee_id: int, db: Session = Depends(get_db)):
    try:
        crud.reset_test_for_employee(db, test_id, employee_id)
        return {"message": "Test reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/create_user/", status_code=status.HTTP_200_OK)
async def clerk_user_created(request: Request, employee: schemas.EmployeeMinimal, db: Session = Depends(get_db)):
    try:

        new_user = crud.create_account(db, employee)
        return {"status": "created", "user_id": new_user.id}

    except Exception as e:
        # Удалим Clerk пользователя
        delete_clerk_user(employee.clerk_id)
        raise HTTPException(status_code=500, detail=f"Ошибка создания сотрудника: {e}")


@app.get("/me/profile/",  status_code=status.HTTP_200_OK)
def get_profile(db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return schemas.Employee.model_validate(crud.get_current_user(db, current_user.user_id))

@app.delete("/me/profile/", status_code=status.HTTP_200_OK)
def delete_profile(db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    try:
        # Удаляем пользователя из Clerk
        delete_clerk_user(current_user.user_id)
    except requests.exceptions.HTTPError as e:
        # Ошибка от Clerk API
        raise HTTPException(
            status_code=502,
            detail=f"Ошибка при удалении пользователя из Clerk: {str(e)}"
        )
    except requests.exceptions.RequestException as e:
        # Проблемы с сетью/доступом к Clerk
        raise HTTPException(
            status_code=503,
            detail=f"Сетевая ошибка при удалении пользователя из Clerk: {str(e)}"
        )
    except ValueError as e:
        # Неверный формат clerk_id
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        # Прочие ошибки
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )

    # Если удаление в Clerk прошло успешно — удаляем пользователя из локальной БД
    return crud.delete_current_user(db, current_user.user_id)

# Todo add admin check
@app.delete("/clerk/delete/{clerk_id}/",  status_code=status.HTTP_200_OK)
def delete_user_clerk(clerk_id: str, db: Session = Depends(get_db)):
    return delete_clerk_user(clerk_id)

@app.post("/me/profile/",  status_code=status.HTTP_200_OK)
def update_profile(data: schemas.EmployeeCreate = Depends(schemas.EmployeeCreate.as_form), photo: UploadFile = File(None),  db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    update_clerk_user(data, current_user.user_id)
    employee_data = data.dict(exclude_unset=True)
    
    # Если есть фото - добавляем его
    if photo is not None:
        photo = photo.file.read()
    

    return crud.update_profile(db=db, user_update=data, photo=photo, user_id=current_user.user_id)

# @app.post("/me/profile",  status_code=status.HTTP_200_OK)
# def complete_profile(profile: schemas.EmployeeCreate,
#     db: Session = Depends(get_db),
#     current_user: UserData = Depends(get_current_user)
# ):
#     update_clerk_user()
    
@app.delete("/employees/{employee_id}/", status_code=status.HTTP_200_OK)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: UserData = Depends(get_current_user)
):
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if db_employee.clerk_id != None:
        response = delete_clerk_user(db_employee.clerk_id)
    response = crud.delete_employee(db=db, employee_id=employee_id, user_id=current_user.user_id)
    return response
      

@app.put("/employees/{employee_id}/", response_model=schemas.Employee)
def update_employee(
    employee_id: int,
    employee: schemas.EmployeeCreate = Depends(schemas.EmployeeCreate.as_form),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserData = Depends(get_current_user)
):
    if photo is not None:
        photo = photo.file.read()
        
    return crud.update_employee(db=db, employee_id=employee_id, employee_update=employee, photo=photo, user_id=current_user.user_id)


@app.get("/employees/", response_model=List[Union[schemas.Employee, schemas.EmployeeMinimal]], status_code=status.HTTP_200_OK)
def get_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.get_employees(db, current_user.user_id)


@app.get("/employees/complete-invite")
def complete_invite(employee_data: schemas.EmployeeCreate, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    crud.update_profile(db=db, employee_update=employee_data, user_id=current_user.user_id)

    return {"message": "Profile completed successfully"}

@app.post("/tests/", status_code=status.HTTP_201_CREATED)
def create_test(test: test_schemas.TestCreate, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.create_test(db=db, test=test, user_id=current_user.user_id)

@app.delete("/tests/{test_id}", status_code=status.HTTP_200_OK)
def delete_test(test_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.delete_test(db=db, test_id=test_id, user_id=current_user.user_id)

@app.get("/tests/{test_id}", response_model=test_schemas.Test, status_code=status.HTTP_200_OK)
def get_test(test_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    db_test = crud.get_test(db, test_id=test_id)
    if db_test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    return db_test

@app.get("/tests/", status_code=status.HTTP_200_OK)
def get_tests(db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.get_tests(db, current_user.user_id)

@app.get("/tests/assign/", status_code=status.HTTP_200_OK)
def get_assigned_tests_for_employee( db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.get_assigned_tests_for_employee(db, current_user.user_id)

@app.get("/tests/assign/{test_id}", status_code=status.HTTP_200_OK)
def get_assigned_test_for_employee(test_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.get_assigned_test_for_employee(db, current_user.user_id, test_id)

@app.post("/tests/assign/", status_code=201)
def assign_tests(
    assignment_data: test_schemas.TestAssignmentCreate,
    db: Session = Depends(get_db)
):
    return crud.assign_test_to_employees(db, assignment_data)

@app.post("/tests/unassign/", status_code=200)
def unassign_tests(
    assignment_data: test_schemas.TestAssignmentCreate,
    db: Session = Depends(get_db)
):
    return crud.remove_test_assignments(db, assignment_data)


@app.put("/tests/{test_id}", status_code=status.HTTP_200_OK)
def update_test(test_id:int, test: test_schemas.TestCreate, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.update_test(db, test_id, test, current_user.user_id)

@app.get("/tests/{test_id}/result", status_code=status.HTTP_200_OK)
def get_tests_results(test_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.get_test_results_with_employee(db, test_id, current_user.user_id)


@app.get("/positions/{position_id}/tests/", response_model=List[test_schemas.Test], status_code=status.HTTP_200_OK)
def get_tests_by_position(position_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.get_tests_by_position(db, position_id=position_id, skip=skip, limit=limit)


@app.post("/belbin-tests/", response_model=schemas.BelbinTest, status_code=status.HTTP_201_CREATED)
def create_belbin_test(test: schemas.BelbinTestCreate, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.create_belbin_test(db=db, test=test)



@app.post("/belbin-tests/{test_id}/evaluate", response_model=schemas.BelbinTestEvaluation)
def evaluate_belbin_test(test_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    evaluation = crud.evaluate_test(db=db, test_id=test_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Test not found")

    # Получаем дополнительную информацию для отчета
    test = db.query(models.BelbinTest).filter(models.BelbinTest.id == test_id).first()
    employee = db.query(models.Employee).filter(models.Employee.id == test.employee_id).first()
    position = db.query(models.Position).filter(models.Position.id == employee.position_id).first()

    results = []
    for result in evaluation["results"]:
        role = db.query(models.BelbinRole).filter(models.BelbinRole.id == result.role_id).first()
        results.append(schemas.BelbinTestResult(
            role_id=role.id,
            role_name=role.name,
            total_score=result.total_score,
            is_required=result.is_required,
            meets_requirement=result.meets_requirement
        ))

    return schemas.BelbinTestEvaluation(
        test_id=test_id,
        employee_name=f"{employee.last_name} {employee.first_name}",
        position_name=position.title,
        overall_result=evaluation["overall_result"],
        results=results
    )


@app.get("/belbin-tests/{test_id}/results", response_model=List[schemas.BelbinTestResult])
def get_belbin_test_results(test_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    results = crud.get_test_results(db=db, test_id=test_id)
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    return results

@app.post("/belbin-roles/", response_model=schemas.BelbinRole)
def create_belbin_role(role: schemas.BelbinRoleCreate, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.create_belbin_role(db, role, current_user.user_id)


@app.get("/belbin-roles/", response_model=list[schemas.BelbinRole])
def get_belbin_roles(db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    print("current_user:", current_user)
    print("user_id:", current_user.user_id)

    return crud.get_belbin_roles(db, current_user.user_id)

@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.put("/belbin-roles/", response_model=schemas.BelbinRole)
def update_belbin_role(role: schemas.BelbinRole, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.update_belbin_role(db, role, current_user.user_id)

@app.delete("/belbin-roles/{role_id}")
def delete_belbin_role(role_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.delete_belbin_role(db, role_id, current_user.user_id)


@app.post("/belbin-positions/")
def create_belbin_position(position: schemas.BelbinPositionRequirementCreate = Body(...), db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    try:
        return crud.create_belbin_position(db, position, current_user.user_id)

    except Exception as exc:
        print(exc)
        return {"success": False}
    



@app.put("/belbin-positions/{position_id}/")
def update_belbin_position(position_id: int, position: schemas.BelbinPositionRequirement, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    updated = crud.update_belbin_position(db, position, current_user.user_id)
    return updated


@app.delete("/belbin-positions/{position_id}")
def delete_belbin_position(position_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    deleted = crud.delete_belbin_position(db, position_id, current_user.user_id)
    return deleted

@app.get("/belbin-positions/")
def get_belbin_position( db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    position = crud.get_belbin_position(db, current_user.user_id)
    return position

@app.delete("/belbin-requiriments/{requiriment_id}")
def delete_belbin_requiriment(requiriment_id:  int,  db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.delete_belbin_requiriment(db, requiriment_id, current_user.user_id)

@app.patch("/tests/{test_id}/status/")
def change_test_status(test_id: int, test_status: schemas.TestStatusUpdate, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.change_test_status(db, test_id, test_status, current_user.user_id)

@app.post("/test/complete/{test_id}")
def complete_test(test_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    test_result = crud.complete_test(db, current_user.user_id, test_id)
    return {"message": "Test completed", "test_result": test_result}    

@app.post("/test/start/{test_id}")
def start_test(test_id: int, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    test_start = crud.start_test(db, current_user.user_id, test_id)
    return test_start

@app.post("/test/save_answer/")
def save_test_answer( answer: schemas.UserAnswerCreate, db: Session = Depends(get_db), current_user: UserData = Depends(get_current_user)):
    return crud.create_user_answer(db, answer, current_user.user_id)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

