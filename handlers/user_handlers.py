from aiogram import types,Router,F,flags
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from keyboards import user_keyborad
user_router= Router()

@user_router.message(CommandStart())
async def cmd_start(message: types.Message, state:FSMContext):
    await state.clear()
    await message.answer("👕 Добро пожаловать в \"Ноунейм сторе\"!\n",reply_markup=user_keyborad.main_kb())
    