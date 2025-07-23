from aiogram import Bot, Dispatcher, types
from os import getenv
from utility.database import init_db
from dotenv import load_dotenv, find_dotenv
from aiogram.fsm.storage.memory import MemoryStorage
from handlers.user_handlers import user_router
from handlers.admin_handlers import admin_router
import logging
import asyncio
from pathlib import Path
import threading
from admin.server import run_admin_panel
from bot_instance import bot

dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO) # Включаем логирование

dp.include_router(admin_router)
dp.include_router(user_router)


async def on_startup():
    # Устанавливаем команды бота
    await bot.set_my_commands(
        commands=[
            types.BotCommand(command="/start", description="Начать"),
            types.BotCommand(command="/help", description="Помощь")
        ],
        scope=types.BotCommandScopeDefault()  # Для всех пользователей
    )
# Запуск бота
async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await on_startup()  # Вызываем после удаления вебхука
        admin_thread = threading.Thread(target=run_admin_panel,daemon=True)
        admin_thread.start()
        await dp.start_polling(bot)
        
    finally:
        await bot.session.close()

if __name__ == '__main__':
    import asyncio
    init_db()
    asyncio.run(main())