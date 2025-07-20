from aiogram import types,Router,F,flags
from aiogram.filters import  CommandStart
from aiogram.fsm.context import FSMContext
from keyboards import user_keyborad
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from utility.database import *
user_router= Router()

@user_router.message(CommandStart())
async def cmd_start(message: types.Message, state:FSMContext):
    await state.clear()
    if not get_user(message.from_user.id):
        add_user(message.from_user.id,message.from_user.username)
    await message.answer("👕 Добро пожаловать в \"Ноунейм сторе\"!\n",reply_markup=user_keyborad.main_kb())
    

@user_router.message(F.text=="🆘 Поддержка")
async def cmd_support(message: types.Message, state:FSMContext):
    await state.clear()
    photo = FSInputFile("static/images/support.jpg")
    support_text = (
        "📞 <b>Служба поддержки</b>\n\n"
        "При возникновении каких либо вопросов, пишите менеджеру:\n\n"
        "@cyberpen"
    )
    await message.answer_photo(
        photo=photo,
        caption=support_text,
        reply_markup=user_keyborad.main_kb(),
        parse_mode=ParseMode.HTML
    )