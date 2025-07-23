from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utility.database import *

def main_keyboard():
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

def products_keyboard(product_index, total_products, category_id, product_id, user_id=None):
    builder = InlineKeyboardBuilder()
    
    # Проверяем наличие товара (если передан user_id)
    in_cart = 0
    total_available = 0
    if user_id:
        sizes = get_product_sizes(product_id)
        if sizes:
            total_available = sum(size['quantity'] for size in sizes)
            in_cart = check_product_in_cart(user_id, product_id)
        else:
            total_available = get_product_total_quantity(product_id)
            in_cart = check_product_in_cart(user_id, product_id)
    
    # Кнопки навигации
    if product_index > 0:
        builder.button(text="⬅️", callback_data=f"prev_{product_index}_{category_id}")
    
    # Кнопка корзины с учетом доступного количества
    cart_text = "🛒 В корзину"
    if user_id and in_cart > 0:
        if total_available > 0:
            cart_text = f"✅ В корзине ({in_cart}/{total_available})"
        else:
            cart_text = "❌ Нет в наличии"
    
    builder.button(
        text=cart_text,
        callback_data=f"cart_{product_id}"
    )
    
    if product_index < total_products - 1:
        builder.button(text="➡️", callback_data=f"next_{product_index}_{category_id}")
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 К категориям", 
            callback_data=f"back_to_cat_{category_id}"
        ),
        InlineKeyboardButton(
            text="🏠 Главное меню", 
            callback_data="main_menu"
        )
    )
    
    builder.adjust(2, 1)
    return builder.as_markup()