
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

from app.utils.time_utils import is_working_hours, get_closed_message

from app.utils.data_cache import public_data_cache

from app.utils.message_utils import safe_edit_message

import asyncio

import logging

logger = logging.getLogger(__name__)

user_router = Router()

@user_router.message(F.text == '/start')

async def cmd_start(message: Message, state: FSMContext):

    await state.clear()

    await user_db.add_user(message.from_user.id, message.from_user.full_name, message.from_user.username)

    is_admin = await admin_db.is_admin(message.from_user.id)

    welcome_text = '☕️ <b>ВІТАЄМО У MEDELIN!</b>\n\nМи обсмажуємо каву з 2015 року, щоб ви могли насолоджуватися ідеальним смаком щодня.\n\nОберіть цікавий вам розділ:'

    await message.answer(welcome_text, reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

@user_router.message(F.text == kb.BTN_BEANS)

async def show_beans(message: Message):

    beans = await coffee_beans_db.get_all_beans()

    if not beans:

        await message.answer('Наразі кава в зернах відсутня.')

        return

    text = '☕️ <b>КАВА В ЗЕРНАХ</b>\n\nОберіть сорт для замовлення або деталей:'

    await message.answer(text, reply_markup=kb.get_beans_kb(beans), parse_mode='HTML')

@user_router.message(F.text == kb.BTN_LOCATIONS)

async def show_locations(message: Message):

    locs = await location_db.get_all_locations()

    text = '📍 <b>НАШІ ЗАКЛАДИ</b>\n\nОберіть локацію, щоб дізнатися адресу та графік:'

    await message.answer(text, reply_markup=await kb.get_locations_info_kb(), parse_mode='HTML')

@user_router.message(F.text == kb.BTN_CONTACTS)

async def show_contacts(message: Message):

    text = '📞 <b>КОНТАКТИ ТА СОЦМЕРЕЖІ</b>\n\nМи завжди на зв’язку! Слідкуйте за нами в соцмережах або телефонуйте:'

    await message.answer(text, reply_markup=await kb.get_contact_kb(), parse_mode='HTML')

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

    if loc.get('phone'):

        text += f"📞 <b>Тел:</b> {loc['phone']}\n"

    if loc.get('atmosphere'):

        text += f"\n✨ {loc['atmosphere']}\n"

    kb_loc = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text='🗺 ГУГЛ КАРТИ', url=loc.get('google_maps_url', 'https://maps.google.com'))],

        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='back_locinfo')]

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

    if bean.get('taste'): text += f"<b>Смак:</b> {bean['taste']}\n"

    if bean.get('country'): text += f"<b>Країна:</b> {bean['country']}\n"
    
    text += f"\n💰 <b>Ціна:</b> {bean.get('price_250', 0)} ₴ / 250г"

    await callback.message.answer_photo(bean.get('image_url', ''), caption=text, reply_markup=kb.get_beans_weight_kb(), parse_mode='HTML')

    await callback.message.delete()

@user_router.callback_query(F.data == 'back_main_menu_only')

async def back_to_main_menu_only(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    is_admin = await admin_db.is_admin(callback.from_user.id)

    text = '☕️ <b>ГОЛОВНЕ МЕНЮ</b>'

    await callback.message.answer(text, reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

    await callback.message.delete()
