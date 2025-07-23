from aiogram import types,Router,F
from aiogram.filters import  CommandStart
from aiogram.fsm.context import FSMContext
from keyboards import user_keyborad
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from utility.database import *
from handlers.states import CatalogStates, CartStates
import asyncio
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.utils.keyboard import InlineKeyboardBuilder
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
        reply_markup=user_keyborad.main_kb(),
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
        await message.answer("В этой категории пока нет товаров")
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