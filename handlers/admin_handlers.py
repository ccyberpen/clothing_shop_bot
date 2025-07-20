from aiogram import types,Router,F,flags
from aiogram.filters import  CommandStart
from aiogram.fsm.context import FSMContext
from keyboards import admin_keyboard
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from utility.database import *
from filters.is_admin import IsAdminIDFilter
from admin.server import ADMIN_TOKEN, LOCALTONET_URL
admin_router= Router()
admin_router.message.filter(IsAdminIDFilter())

@admin_router.message(CommandStart())
async def cmd_start(message: types.Message, state:FSMContext):
    await state.clear()
    await message.answer(f"👕 Добро пожаловать, администратор {message.from_user.username}",reply_markup=admin_keyboard.main_kb())

@admin_router.message(F.text == "Админка")
async def send_admin_link(message: types.Message):
    if not LOCALTONET_URL:
        return await message.answer("Админ-панель ещё не готова")
    
    web_app_url = f"{LOCALTONET_URL}"
    await message.answer(
        "Панель администратора:",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="Открыть админку",
                    web_app=types.WebAppInfo(url=web_app_url)
                )
            ]]
        )
    )