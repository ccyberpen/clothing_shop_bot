from aiogram.filters import Filter
from aiogram import types
from utility.database import *
from filters.is_admin import IsAdminIDFilter


class IsNotAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return not await IsAdminIDFilter()(message)