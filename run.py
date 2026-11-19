"""Точка входа: polling. Работает одинаково на локальном ПК и на VPS."""
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.db import init_db
from bot.handlers import router
from config import ADMIN_ID, BOT_TOKEN, LOG_LEVEL, LOGS_DIR


def setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # консоль Windows по умолчанию в OEM-кодировке (866): принудительно UTF-8,
    # иначе русский текст в окне терминала превращается в «кракозябры»
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(LOGS_DIR / "bot.log", maxBytes=2_000_000,
                                       backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="new", description="Новая сделка"),
        BotCommand(command="archive", description="Мои договоры"),
        BotCommand(command="help", description="Как это работает"),
    ])


async def main() -> None:
    setup_logging()
    log = logging.getLogger("bot")

    if not BOT_TOKEN:
        log.error("BOT_TOKEN не задан. Скопируйте .env.example в .env и впишите токен.")
        return

    init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await set_commands(bot)
    me = await bot.get_me()
    log.info("Бот запущен: @%s", me.username)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
