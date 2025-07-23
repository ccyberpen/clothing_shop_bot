from aiogram.fsm.state import StatesGroup, State

class CatalogStates(StatesGroup):
    choosing_category = State()
    viewing_products = State()
class CartStates(StatesGroup):
    choosing_size = State()
class OrderStates(StatesGroup):
    viewing_cart = State()
    creating_order = State()