from aiogram import types,Router,F
from aiogram.filters import  CommandStart
from aiogram.fsm.context import FSMContext
from keyboards import user_keyborad
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from utility.database import *
from handlers.states import CatalogStates
import asyncio
from aiogram.types import InputMediaPhoto
from aiogram.utils.media_group import MediaGroupBuilder
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
    if 'product_messages' in data:
        for msg_id in reversed(data['product_messages']):
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            except:
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
        await callback.message.delete()
        data = await state.get_data()
        if 'product_messages' in data:
            for msg_id in reversed(data['product_messages']):
                try:
                    await message.bot.delete_message(chat_id=callback.chat.id, message_id=msg_id)
                except:
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
                    await callback.bot.delete_message(chat_id=callback.chat.id, message_id=msg_id)
                except:
                    continue
        
        await callback.message.answer(
            "📂 Выберите категорию:",
            reply_markup=user_keyborad.catalog_keyboard(root_categories)
        )
    
    await state.set_state(CatalogStates.choosing_category)

@user_router.callback_query(F.data == "main_menu")
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
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