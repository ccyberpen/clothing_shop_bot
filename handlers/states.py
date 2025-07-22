from aiogram.fsm.state import StatesGroup, State

class CatalogStates(StatesGroup):
    choosing_category = State()
    viewing_products = State()