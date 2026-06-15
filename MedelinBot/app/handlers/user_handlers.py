
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup

from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext

from app.databases.orders_database import orders_db

from app.databases.active_orders_database import active_orders_db

from app.databases.admin_database import admin_db

from app.databases.user_database import user_db

from app.databases.location_database import location_db

from app.databases.contacts_database import contacts_db

from app.databases.coffee_beans_database import coffee_beans_db

import app.keyboards.user_keyboards as kb
import app.keyboards.admin_keyboards as akb

from app.utils.time_utils import is_working_hours, get_closed_message

from app.utils.data_cache import public_data_cache

from app.utils.message_utils import safe_edit_message

import asyncio

import logging

logger = logging.getLogger(__name__)

from aiogram.filters import StateFilter

user_router = Router()

@user_router.message(F.text == '/start', StateFilter('*'))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Register user in DB so they can be added to staff later
    await user_db.add_user(
        message.from_user.id, 
        message.from_user.first_name, 
        message.from_user.username
    )
    
    is_admin = await admin_db.is_admin(message.from_user.id)
    
    if not is_admin:
        kb_contact = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='📱 ПОДІЛИТИСЯ КОНТАКТОМ', request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            '🔒 <b>Цей бот призначений тільки для адміністраторів Medelin.</b>\n\n'
            'Щоб власник міг додати вас до команди за номером телефону, натисніть кнопку нижче 👇', 
            reply_markup=kb_contact,
            parse_mode='HTML'
        )
        return

    role = await admin_db.get_admin_role(message.from_user.id)
    
    role_label = {
        'developer': 'developer',
        'owner': 'власник',
        'admin': 'адмін'
    }.get(role, role)
    
    await message.answer(f'🔐 <b>ВІТАЄМО В АДМІН-ПАНЕЛІ!</b>\nВаша роль: <b>{role_label}</b>', reply_markup=akb.get_admin_main_kb(role), parse_mode='HTML')

@user_router.message(F.contact)
async def handle_contact(message: Message):
    if not message.contact: return
    
    # Check if contact belongs to the user
    if message.contact.user_id != message.from_user.id:
        await message.answer("❌ Будь ласка, надішліть свій власний контакт.")
        return
        
    await user_db.set_phone(message.from_user.id, message.contact.phone_number)
    
    is_admin = await admin_db.is_admin(message.from_user.id)
    if not is_admin:
        await message.answer(
            "✅ <b>Дякуємо! Ваш номер збережено.</b>\n\nТепер власник може додати вас до команди. Очікуйте повідомлення про призначення ролі.", 
            parse_mode='HTML',
            reply_markup=ReplyKeyboardMarkup(keyboard=[], remove_keyboard=True) # Hide keyboard
        )
    else:
        await message.answer("✅ Номер телефону оновлено.", reply_markup=ReplyKeyboardMarkup(keyboard=[], remove_keyboard=True))

# --- Public Information Handlers ---

async def show_contacts(message: Message):
    text = (
        "<b>📞 НАШІ КОНТАКТИ</b>\n\n"
        "Слідкуйте за нами в соцмережах та зв'язуйтеся з нами зручним для вас способом:"
    )
    await message.answer(text, reply_markup=await kb.get_contact_kb(), parse_mode='HTML')

async def show_locations(message: Message):
    text = '📍 <b>НАШІ ЗАКЛАДИ</b>\n\nОберіть локацію, щоб дізнатися адресу та графік:'
    await message.answer(text, reply_markup=await kb.get_locations_info_kb(), parse_mode='HTML')

async def show_coffee_menu(message: Message):
    beans = await coffee_beans_db.get_all_beans()
    text = "☕️ <b>КАВА В ЗЕРНАХ</b>\n\nОберіть сорт для замовлення:"
    await message.answer(text, reply_markup=kb.get_beans_kb(beans), parse_mode='HTML')

async def show_beans(message: Message):
    await show_coffee_menu(message)

async def cmd_start_msg(message: Message, is_admin: bool=False):
    await message.answer('☕️ <b>ГОЛОВНЕ МЕНЮ</b>', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

@user_router.message()
async def block_all_other_messages(message: Message):
    is_admin = await admin_db.is_admin(message.from_user.id)
    
    # Allow main menu buttons for everyone
    if message.text == kb.BTN_CONTACTS:
        return await show_contacts(message)
    if message.text == kb.BTN_LOCATIONS:
        return await show_locations(message)
    if message.text == kb.BTN_BEANS:
        return await show_coffee_menu(message)
    if message.text == '🏠 НА ГОЛОВНУ':
        return await cmd_start_msg(message, is_admin)

    if not is_admin:
        await message.answer('🔒 <b>Цей бот призначений тільки для адміністраторів Medelin.</b>', parse_mode='HTML')

@user_router.callback_query(F.data.startswith('locinfo_'))

async def show_location_details(callback: CallbackQuery):

    loc_id = callback.data.replace('locinfo_', '')

    loc = await location_db.get_location_by_id(loc_id)

    if not loc:

        await callback.answer('Локацію не знайдено.')

        return

    text = f"📍 <b>{loc['name']}</b>\n\n"
    text += f"🏠 <b>Адреса:</b> {loc['address']}\n"
    text += f"🕒 <b>Графік:</b> {loc['schedule']}\n"


    if loc.get('atmosphere'):

        text += f"\n✨ {loc['atmosphere']}\n"

    kb_loc = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text='🗺 ГУГЛ КАРТИ', url=loc.get('google_maps_url', 'https://maps.google.com'))],

        [InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='back_locinfo')]

    ])

    if loc.get('image_url'):

        try:

            await callback.message.answer_photo(loc['image_url'], caption=text, reply_markup=kb_loc, parse_mode='HTML')

            await callback.message.delete()

        except:

            await safe_edit_message(callback.message, text, reply_markup=kb_loc, parse_mode='HTML')

    else:

        await safe_edit_message(callback.message, text, reply_markup=kb_loc, parse_mode='HTML')

@user_router.callback_query(F.data == 'back_locinfo')

async def back_to_locs(callback: CallbackQuery):

    text = '📍 <b>НАШІ ЗАКЛАДИ</b>\n\nОберіть локацію, щоб дізнатися адресу та графік:'

    await safe_edit_message(callback.message, text, reply_markup=await kb.get_locations_info_kb(), parse_mode='HTML')

@user_router.callback_query(F.data.startswith('bean_'))

async def show_bean_details(callback: CallbackQuery, state: FSMContext):

    bid = callback.data.replace('bean_', '')

    if bid == 'back':

        await show_beans(callback.message)

        await callback.message.delete()

        return

    bean = await coffee_beans_db.get_bean_by_id(bid)

    if not bean:

        await callback.answer('Сорт не знайдено.')

        return

    await state.update_data(bean_id=str(bean['_id']), bean_name=bean['name'], base_price=bean.get('price_250', 0))

    text = f"☕️ <b>{bean['name']}</b>\n\n"

    text += f"{bean.get('description', '')}\n\n"

    if bean.get('species'): text += f"<b>Склад:</b> {bean['species']}\n"
    if bean.get('roast'): text += f"<b>Обсмаження:</b> {bean['roast']}\n"
    if bean.get('quality_score') or bean.get('cup_score'): 
        text += f"<b>Оцінка якості:</b> {bean.get('quality_score') or bean['cup_score']}\n"
    
    if bean.get('variety'): text += f"<b>Різновид:</b> {bean['variety']}\n"
    if bean.get('altitude'): text += f"<b>Висота зростання:</b> {bean['altitude']}\n"
    if bean.get('processing'): text += f"<b>Метод обробки:</b> {bean['processing']}\n"
    if bean.get('harvest'): text += f"<b>Період врожаю:</b> {bean['harvest']}\n"
    if bean.get('descriptors') or bean.get('taste'):
        text += f"<b>Дескриптори:</b> {bean.get('descriptors') or bean.get('taste')}\n"
    
    text += f"\n💰 <b>Ціна:</b> {bean.get('price_250', 0)} ₴"

    await callback.message.answer_photo(bean.get('image_url', ''), caption=text, reply_markup=kb.get_beans_weight_kb(), parse_mode='HTML')

    await callback.message.delete()

@user_router.callback_query(F.data == 'back_main_menu_only')

async def back_to_main_menu_only(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    is_admin = await admin_db.is_admin(callback.from_user.id)

    text = '☕️ <b>ГОЛОВНЕ МЕНЮ</b>'

    await callback.message.answer(text, reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

    await callback.message.delete()
