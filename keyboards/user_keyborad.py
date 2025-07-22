from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍️ Каталог"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="🆘 Поддержка")]
        ],
        resize_keyboard=True
    )
def catalog_keyboard(categories,back_id=None):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat['name'], callback_data=f"cat_{cat['category_id']}")
    if back_id:
        builder.button(text="🔙 Назад", callback_data=f"cat_{back_id}")
    
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1, repeat=True)
    return builder.as_markup()

def products_keyboard(product_index, total_products, category_id, product_id):
    builder = InlineKeyboardBuilder()
    
    if product_index > 0:
        builder.button(text="⬅️", callback_data=f"prev_{product_index}_{category_id}")
    
    builder.button(text="🛒 В корзину", callback_data=f"cart_{product_id}")
    
    if product_index < total_products - 1:
        builder.button(text="➡️", callback_data=f"next_{product_index}_{category_id}")
    
    builder.button(text="🔙 К категориям", callback_data=f"back_to_cat_{category_id}")
    builder.adjust(2, 1)
    return builder.as_markup()