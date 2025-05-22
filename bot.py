import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),  # Запись в файл
        logging.StreamHandler()  # Вывод в консоль
    ]
)
logger = logging.getLogger(__name__)
# Токен бота (замените на свой)
TOKEN = "8141316524:AAG8wbW5JS-Z-HsMfLijjfqaqv-3X14xFIk"

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Обработчик команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    try:
        logger.info(f"User {message.from_user.id} started the bot")

        # Создаем кнопку с Web App
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="Открыть тест 🚀",
                web_app=WebAppInfo(url="https://84my3i-159-253-172-21.ru.tuna.am")
            )
        )

        await message.answer(
            "Нажмите кнопку ниже, чтобы начать тест:",
            reply_markup=builder.as_markup()
        )
        logger.info(f"Start message sent to user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in start handler: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


# Логирование ошибок
@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    logger.error(f"Update: {update}\nException: {exception}", exc_info=True)
    return True


# Запуск бота
async def main():
    try:
        logger.info("Starting bot")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Bot stopped with error: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped")
        await bot.session.close()


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)