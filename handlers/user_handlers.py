from aiogram import types,Router,F
from aiogram.filters import  CommandStart
from aiogram.fsm.context import FSMContext
from keyboards import user_keyborad
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from utility.database import *
from handlers.states import CatalogStates, CartStates, OrderStates
import asyncio
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot_instance import bot
user_router= Router()


@user_router.message(CommandStart())
async def cmd_start(message: types.Message, state:FSMContext):
    await state.clear()
    if not get_user(message.from_user.id):
        add_user(message.from_user.id,message.from_user.username)
    await message.answer("👕 Добро пожаловать в \"Ноунейм сторе\"!\n",reply_markup=user_keyborad.main_keyboard())
    

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
        reply_markup=user_keyborad.main_keyboard(),
        parse_mode=ParseMode.HTML
    )
###########################################################
#                   ОБРАБОТЧИКИ КАТАЛОГА                  #
###########################################################
@user_router.message(F.text == "🛍️ Каталог")
async def start_catalog(message: types.Message, state: FSMContext):
    try:
        root_categories = get_categories(parent_id=None)
        
        if not root_categories:
            await message.answer("Категории не найдены", reply_markup=user_keyborad.main_keyboard())
            return
        
        
        
        # 1. Сначала отправляем команду на удаление клавиатуры
        await message.answer(
            "Открываем каталог...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # 2. Ждем немного, чтобы Telegram обработал удаление клавиатуры
        await asyncio.sleep(0.3)
        
        # 3. Удаляем служебное сообщение (если нужно)
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id + 1  # ID следующего сообщения
            )
        except:
            pass
        
        # 4. Показываем категории в новом сообщении
        sent_message = await message.answer(
            "📂 Выберите категорию:",
            reply_markup=user_keyborad.catalog_keyboard(root_categories)
        )
        await state.set_state(CatalogStates.choosing_category)
        await state.update_data(
            catalog_message_id = sent_message.message_id
        )
        
    except Exception as e:
        print(f"Ошибка в start_catalog: {e}")
        await message.answer(
            "Произошла ошибка, попробуйте снова",
            reply_markup=user_keyborad.main_keyboard()
        )

@user_router.callback_query(F.data.startswith("cat_"), CatalogStates.choosing_category)
async def choose_category(callback: types.CallbackQuery, state: FSMContext):
    try:
        category_id = int(callback.data.split("_")[1])
        categories = get_categories(parent_id=category_id)
        
        if categories:
            # Редактируем существующее сообщение с категориями
            sent_message = await callback.message.edit_text(
                "📂 Выберите подкатегорию:",
                reply_markup=user_keyborad.catalog_keyboard(categories, back_id=get_parent_id(category_id))
            )
            await state.update_data(
                catalog_message_id = sent_message.message_id
            )
        else:
            # Удаляем сообщение с выбором категории
            await callback.message.delete()
            # Показываем товары
            await show_products(callback.message, category_id, state)
            
    except Exception as e:
        print(f"Ошибка в choose_category: {e}")
        await callback.answer("Произошла ошибка, попробуйте ещё раз")

async def show_products(message: types.Message, category_id: int, state: FSMContext):
    products = get_products(category_id)
    
    if not products:
        await message.answer("В этой категории пока нет товаров",reply_markup=user_keyborad.main_keyboard())
        await state.clear()
        return
    
    await state.set_state(CatalogStates.viewing_products)
    await state.update_data(
        current_index=0,
        category_id=category_id,
        products=products,
        product_messages=[message.message_id]  # Сохраняем ID текущего сообщения
    )
    
    await display_product(message, products[0], 0, len(products), category_id, state)

async def display_product(message: types.Message, product: dict, index: int, total: int, category_id: int, state: FSMContext):
    images = get_product_images(product['product_id'])
    caption = (
        f"<b>{product['name']}</b>\n\n"
        f"💰 Цена: <code>{product['price']} ₽</code>\n"
        f"📝 Описание: {product['description'] or 'Нет описания'}\n\n"
        f"🆔 Артикул: <code>{product['product_id']}</code>"
    )

    message_ids = []

    # Удаляем предыдущие сообщения (если есть)
    data = await state.get_data()
    print(data["product_messages"])
    if 'product_messages' in data:
        for msg_id in reversed(data['product_messages']):
            try:
                print(f"Удаление {msg_id}")
                await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            except Exception as e:
                print(f"Ошибка удаления сообщения с товаром {msg_id}: {e}")
                continue

    if images:
        max_images = 10  # Лимит Telegram
        images = images[:max_images]

        try:
            # Отправляем медиагруппу с фотографиями
            media_group = MediaGroupBuilder()
            for img in images:
                photo = FSInputFile(f"admin/static/products/{img['image_path']}")
                media_group.add_photo(media=photo)
            
            sent_messages = await message.answer_media_group(media=media_group.build())
            message_ids.extend([m.message_id for m in sent_messages])
        except Exception as e:
            print(f"Ошибка отправки медиагруппы: {e}")

    # Отправляем описание с кнопками
    msg = await message.answer(
        text=caption,
        reply_markup=user_keyborad.products_keyboard(index, total, category_id, product['product_id']),
        parse_mode=ParseMode.HTML
    )
    message_ids.append(msg.message_id)

    # Сохраняем IDs сообщений в состоянии
    await state.update_data(product_messages=message_ids)
    print(f"Итого имеем: {message_ids}")
    return message_ids

@user_router.callback_query(F.data.startswith(("prev_", "next_")), CatalogStates.viewing_products)
async def navigate_product(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data['products']
    
    action, current_idx, category_id = callback.data.split("_")
    current_idx = int(current_idx)
    category_id = int(category_id)
    
    new_idx = current_idx + 1 if action == "next" else current_idx - 1
    if 0 <= new_idx < len(products):
        # Удаляем предыдущие сообщения перед показом новых
        if 'product_messages' in data:
            for msg_id in reversed(data['product_messages']):
                try:
                    await callback.bot.delete_message(
                        chat_id=callback.message.chat.id,
                        message_id=msg_id
                    )
                except:
                    continue
        
        await display_product(callback.message, products[new_idx], new_idx, len(products), category_id, state)
        await state.update_data(current_index=new_idx)

@user_router.callback_query(F.data.startswith("back_to_cat_"), CatalogStates.viewing_products)
async def back_to_categories(callback: types.CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[-1])
    parent_id = get_parent_id(category_id)
    if parent_id:
        categories = get_categories(parent_id=parent_id)
        print(callback.message.message_id)
        await callback.message.delete()
        data = await state.get_data()
        if 'product_messages' in data:
            for msg_id in reversed(data['product_messages']):
                try:
                    await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
                except Exception as e:
                    print(f"Ошибка удаления сообщения с товаром: {e}")
                    continue
        await callback.message.answer(
            "📂 Выберите подкатегорию:",
            reply_markup=user_keyborad.catalog_keyboard(categories, back_id=get_parent_id(parent_id))
        )
    else:
        root_categories = get_categories(parent_id=None)
        await callback.message.delete()
        data = await state.get_data()
        if 'product_messages' in data:
            for msg_id in reversed(data['product_messages']):
                try:
                    await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
                except Exception as e:
                    print(f"Ошибка удаления сообщения с товаром: {e}")
                    continue
        
        await callback.message.answer(
            "📂 Выберите категорию:",
            reply_markup=user_keyborad.catalog_keyboard(root_categories)
        )
    
    await state.set_state(CatalogStates.choosing_category)

@user_router.callback_query(F.data == "main_menu")
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        if 'product_messages' in data:
            for msg_id in reversed(data['product_messages']):
                try:
                    await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
                except Exception as e:
                    print(f"Ошибка удаления сообщения с товаром: {e}")
                    continue
        # Удаляем сообщение с выбором категории
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id)
        # Очищаем состояние
        await state.clear()
        
        # Отправляем главное меню
        await callback.message.answer(
            "Вы вернулись в главное меню:",
            reply_markup=user_keyborad.main_keyboard()
        )
        callback.message.delete()
        
    except Exception as e:
        print(f"Ошибка возврата в меню: {e}")
        await callback.message.answer(
            "Главное меню:",
            reply_markup=user_keyborad.main_keyboard()
        )

def get_parent_id(category_id: int) -> int | None:
    """Получаем ID родительской категории с проверкой пустых значений"""
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT parent_id FROM categories 
        WHERE category_id = ?
    """, (category_id,))
    result = cur.fetchone()
    conn.close()
    
    if not result or not result[0] or str(result[0]).strip() == '':
        return None
    return int(result[0])

#######################################
#          РАБОТА С КОРЗИНОЙ          #
#######################################
@user_router.callback_query(F.data.startswith("cart_"))
async def add_to_cart(callback: types.CallbackQuery, state: FSMContext):
    try:
        product_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        product = get_product(product_id)
        
        if not product:
            await callback.answer("Товар не найден", show_alert=True)
            return
        
        sizes = get_product_sizes(product_id)
        
        if sizes:
            await callback.answer()
            await state.set_state(CartStates.choosing_size)
            
            # Формируем клавиатуру только с доступными размерами
            sizes_kb = InlineKeyboardBuilder()
            available_sizes = []
            
            for size in sizes:
                if size['quantity'] > 0:
                    available_sizes.append(size)
                    sizes_kb.button(
                        text=f"{size['size_value']} (осталось: {size['quantity']})",
                        callback_data=f"size_{size['size_id']}"
                    )
            
            if not available_sizes:
                await callback.answer("Нет доступных размеров", show_alert=True)
                return
            
            sizes_kb.button(text="❌ Отмена", callback_data="cancel_cart")
            sizes_kb.adjust(2)
            
            # Сохраняем данные для восстановления навигации
            nav_data = await state.get_data()
            await state.update_data(
                product_id=product_id,
                product_name=product['name'],
                product_price=product['price'],
                product_index=nav_data.get('current_index', 0),
                category_id=nav_data.get('category_id'),
                products=nav_data.get('products', []),
                product_messages=nav_data.get('product_messages', [])
            )
            
            size_msg = await callback.message.answer(
                f"Выберите размер для {product['name']}:",
                reply_markup=sizes_kb.as_markup()
            )
            
            # Обновляем список сообщений
            messages = nav_data.get('product_messages', [])
            messages.append(size_msg.message_id)
            await state.update_data(product_messages=messages)
            
        else:
            # Для товаров без размеров проверяем общее количество
            total_quantity = get_product_total_quantity(product_id)
            if total_quantity <= 0:
                await callback.answer("Товар закончился", show_alert=True)
                return
                
            # Проверяем, сколько уже в корзине
            in_cart = check_product_in_cart(user_id, product_id)
            if in_cart >= total_quantity:
                await callback.answer(
                    f"Нельзя добавить больше {total_quantity} шт.", 
                    show_alert=True
                )
                return
                
            add_to_cart_db(user_id, product_id)
            await callback.answer(f"{product['name']} добавлен в корзину!")
            
    except Exception as e:
        print(f"Ошибка добавления в корзину: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@user_router.callback_query(F.data.startswith("size_"), CartStates.choosing_size)
async def choose_size(callback: types.CallbackQuery, state: FSMContext):
    try:
        size_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        data = await state.get_data()
        
        # Проверяем доступное количество
        size_info = get_size_info(size_id)
        if not size_info or size_info['quantity'] <= 0:
            await callback.answer("Этот размер закончился", show_alert=True)
            return
            
        # Проверяем, сколько уже в корзине
        in_cart = check_product_in_cart(user_id, data['product_id'], size_id)
        if in_cart >= size_info['quantity']:
            await callback.answer(
                f"Максимум {size_info['quantity']} шт. для размера {size_info['size_value']}",
                show_alert=True
            )
            return
            
        # Добавляем в корзину
        add_to_cart_db(user_id, data['product_id'], size_id)
        
        # Удаляем сообщение с выбором размера
        await callback.message.delete()
        
        # Восстанавливаем навигацию
        await state.set_state(CatalogStates.viewing_products)
        await state.update_data(
            current_index=data['product_index'],
            category_id=data['category_id'],
            products=data['products'],
            product_messages=data.get('product_messages', [])
        )
        
        await callback.answer(
            f"{data['product_name']} (размер: {size_info['size_value']}) добавлен в корзину!",
            show_alert=True
        )
        
    except Exception as e:
        print(f"Ошибка выбора размера: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
        await state.clear()

@user_router.callback_query(F.data == "cancel_cart", CartStates.choosing_size)
async def cancel_cart(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Получаем данные о текущем товаре из состояния
        data = await state.get_data()
        
        # Удаляем сообщение с выбором размера
        await callback.message.delete()
        
        # Восстанавливаем состояние просмотра товаров
        await state.set_state(CatalogStates.viewing_products)
        await state.update_data(
            current_index=data['product_index'],
            category_id=data['category_id'],
            products=data['products'],
            product_messages=data.get('product_messages', [])
        )
        
        await callback.answer("Выбор размера отменён")
        
    except Exception as e:
        print(f"Ошибка при отмене добавления в корзину: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
        await state.clear()

############################################################
#           ПРОСМОТР КОРЗИНЫ И ОФОРМЛЕНИЕ ЗАКАЗА           #
############################################################

@user_router.message(F.text == "🛒 Корзина")
async def view_cart(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cart_items = get_cart_items(user_id)
    
    if not cart_items:
        await message.answer("Ваша корзина пуста", reply_markup=user_keyborad.main_keyboard())
        return
    
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
    cart_text = "🛒 <b>Ваша корзина</b>\n\n"
    
    for item in cart_items:
        size_text = f", размер: {item['size_value']}" if item['size_value'] else ""
        cart_text += (
            f"▪️ {item['name']}{size_text}\n"
            f"   Кол-во: {item['quantity']} × {item['price']} ₽ = {item['quantity'] * item['price']} ₽\n\n"
        )
    
    cart_text += f"💳 <b>Итого: {total_amount} ₽</b>"
    
    await state.set_state(OrderStates.viewing_cart)
    await message.answer(
        cart_text,
        parse_mode=ParseMode.HTML,
        reply_markup=user_keyborad.cart_keyboard()
    )
@user_router.callback_query(F.data == "checkout", OrderStates.viewing_cart)
async def start_checkout(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Введите ваши контактные данные для оформления заказа (имя и телефон):\n"
        "Пример: Иван Иванов, +79123456789",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(OrderStates.creating_order)

@user_router.message(OrderStates.creating_order)
async def process_order(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        contact_info = message.text.strip()
        
        # Проверяем формат ввода
        if len(contact_info) < 5 or ',' not in contact_info:
            await message.answer(
                "Пожалуйста, введите данные в формате: Имя, Телефон\n"
                "Пример: Иван Иванов, +79123456789",
                reply_markup=user_keyborad.cancel_keyboard()
            )
            return
        
        # Создаем заказ
        order_id = create_order(user_id, contact_info)
        
        # Отправляем подтверждение
        await message.answer(
            "✅ <b>Ваш заказ оформлен!</b>\n\n"
            f"Номер заказа: <code>{order_id}</code>\n"
            "Статус: В обработке\n\n"
            f"Отправляйте на номер +78005553535 <code>{get_order_total(order_id)}</code>₽",
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyborad.main_keyboard()
        )
        
        # Очищаем корзину
        clear_cart(user_id)
        await state.clear()
        
        
    except Exception as e:
        print(f"Ошибка оформления заказа: {e}")
        await message.answer(
            "Произошла ошибка при оформлении заказа. Пожалуйста, попробуйте позже.",
            reply_markup=user_keyborad.main_keyboard()
        )
        await state.clear()

@user_router.callback_query(F.data == "cancel_order", OrderStates.creating_order)
async def cancel_checkout(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Оформление заказа отменено",reply_markup=user_keyborad.main_keyboard())
    await state.clear()
    await callback.answer()
    

##############################
#           ЗАКАЗЫ           #
##############################

@user_router.message(F.text == "📦 Мои заказы")
async def show_user_orders(message: types.Message):
    """Показываем список заказов пользователя"""
    try:
        user_id = message.from_user.id
        orders = get_user_orders(user_id)
        
        if not orders:
            await message.answer(
                "📭 У вас пока нет заказов",
                reply_markup=user_keyborad.main_keyboard()
            )
            return
        
        orders_text = "📦 <b>Ваши заказы</b>\n\n"
        for order in orders:
            status_emoji = {
                'new': '🆕',
                'processing': '🔄', 
                'shipped': '🚚',
                'completed': '✅',
                'cancelled': '❌'
            }.get(order['status'], 'ℹ️')
            
            orders_text += (
                f"{status_emoji} <b>Заказ #{order['order_id']}</b>\n"
                f"📅 Дата: {order['created_at']}\n"
                f"🏷 Статус: {get_status_string(order['status'])}\n"
                f"💳 Сумма: {order['total_amount']} ₽\n\n"
            )
        
        await message.answer(
            orders_text,
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyborad.orders_keyboard(orders)
        )
        
    except Exception as e:
        print(f"Ошибка при показе заказов: {e}")
        await message.answer(
            "Произошла ошибка при загрузке ваших заказов",
            reply_markup=user_keyborad.main_keyboard()
        )

@user_router.callback_query(F.data.startswith("order_detail_"))
async def show_order_detail(callback: types.CallbackQuery):
    """Показываем детали конкретного заказа"""
    try:
        order_id = int(callback.data.split("_")[2])
        order = get_order_details(order_id)
        items = get_order_items(order_id)
        
        if not order or order['user_id'] != callback.from_user.id:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        order_text = (
            f"📦 <b>Заказ #{order['order_id']}</b>\n\n"
            f"📅 Дата: {order['created_at']}\n"
            f"🏷 Статус: {get_status_string(order['status'])}\n"
        )
        
        if order.get('tracking_number'):
            order_text += f"📦 Трек-номер: {order['tracking_number']}\n"
        
        order_text += "\n<b>Состав заказа:</b>\n"
        
        for item in items:
            size_text = f", размер: {item['size_value']}" if item.get('size_value') else ""
            order_text += (
                f"▪ {item['name']}{size_text}\n"
                f"   {item['quantity']} × {item['price_at_order']} ₽ = "
                f"{item['quantity'] * item['price_at_order']} ₽\n\n"
            )
        
        order_text += f"💳 <b>Итого: {order['total_amount']} ₽</b>"
        
        await callback.message.edit_text(
            order_text,
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyborad.back_to_orders_keyboard()
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Ошибка при показе деталей заказа: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

# Добавляем новую функцию для уведомлений
async def send_order_notification(user_id: int, order_id: int, new_status: str, tracking_number: str = None):
    print("Ща отправлю")
    """Отправка уведомления пользователю об изменении статуса заказа"""
    status_messages = {
        'processing': "🔄 Ваш заказ #{} передан в обработку",
        'shipped': "🚚 Ваш заказ #{} отправлен" + (f", трек-номер: {tracking_number}" if tracking_number else ""),
        'completed': "✅ Ваш заказ #{} завершен. Спасибо за покупку!",
        'cancelled': "❌ Ваш заказ #{} отменен"
    }
    
    message = status_messages.get(new_status, f"ℹ️ Статус вашего заказа #{order_id} изменен: {new_status}")
    
    try:
        print("Отправляю")
        await bot.send_message(
            chat_id=user_id,
            text=message.format(order_id)
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")


# Добавляем обработчик обновления статуса заказа (вызывается из API)
async def handle_order_status_update(order_id: int, new_status: str, old_status: str, tracking_number: str = None):
    """Обработчик изменения статуса заказа"""
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        # Получаем информацию о заказе
        order = conn.execute("""
            SELECT user_id, status 
            FROM orders 
            WHERE order_id = ?
        """, (order_id,)).fetchone()
        
        if not order:
            return False
        
        user_id = order['user_id']
        
        # Отправляем уведомление пользователю
        await send_order_notification(user_id, order_id, new_status, tracking_number)
        
        # Обработка остатков товаров
        if new_status in ['shipped', 'completed'] and old_status not in ['shipped', 'completed']:
            # Списание товаров при отправке/завершении
            update_inventory(order_id, decrease=True)
        elif new_status == 'cancelled' and old_status in ['shipped', 'completed']:
            # Возврат товаров при отмене отправленного/завершенного заказа
            update_inventory(order_id, decrease=False)
        
        # Обновляем время изменения заказа
        conn.execute("""
            UPDATE orders 
            SET updated_at = ? 
            WHERE order_id = ?
        """, (datetime.now(), order_id))
        conn.commit()
        
        return True
        
    except Exception as e:
        print(f"Ошибка обработки изменения статуса заказа {order_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
def get_status_string(status):
    status_name = {
                'new': 'Новый',
                'processing': 'В обработке',
                'shipped': 'Отправлен',
                'completed': 'Завершен',
                'cancelled': 'Отменен'
            }.get(status,'?')
    return status_name
@user_router.callback_query(F.data == "back_to_orders")
async def back_to_orders_list(callback: types.CallbackQuery):
    """Возврат к списку заказов"""
    try:
        user_id = callback.from_user.id
        orders = get_user_orders(user_id)
        
        if not orders:
            await callback.message.edit_text(
                "📭 У вас пока нет заказов",
                reply_markup=user_keyborad.main_keyboard()
            )
            return
        
        orders_text = "📦 <b>Ваши заказы</b>\n\n"
        for order in orders:
            status_emoji = {
                'new': '🆕',
                'processing': '🔄', 
                'shipped': '🚚',
                'completed': '✅',
                'cancelled': '❌'
            }.get(order['status'], 'ℹ️')
            
            orders_text += (
                f"{status_emoji} <b>Заказ #{order['order_id']}</b>\n"
                f"📅 Дата: {order['created_at']}\n"
                f"🏷 Статус: {get_status_string(order['status'])}\n"
                f"💳 Сумма: {order['total_amount']} ₽\n\n"
            )
        
        await callback.message.edit_text(
            orders_text,
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyborad.orders_keyboard(orders)
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Ошибка при показе заказов: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)