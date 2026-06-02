
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from app.databases.orders_database import orders_db

from app.databases.active_orders_database import active_orders_db

from app.databases.admin_database import admin_db

from app.databases.user_database import user_db

from app.databases.location_database import location_db

from app.databases.contacts_database import contacts_db

from app.databases.coffee_beans_database import coffee_beans_db

import app.keyboards.admin_keyboards as akb

from app.utils.data_cache import public_data_cache

from app.utils.message_utils import safe_edit_message

from app.common.config import DEVELOPER_IDS

from app.databases.mongo_client import get_db

import logging

import html

logger = logging.getLogger(__name__)

admin_router = Router()

class AdminStates(StatesGroup):
    adding_admin_id = State()
    adding_admin_role = State()
    choosing_admin_locations = State()
    adding_bean_name = State()
    adding_bean_price = State()
    adding_bean_desc = State()
    adding_location_name = State()
    adding_location_address = State()

async def get_user_role(user_id: int) -> str:
    if str(user_id) in DEVELOPER_IDS: return 'developer'
    db = await get_db()
    admin = await db.admins.find_one({'user_id': int(user_id)})
    return admin.get('role', 'user') if admin else 'user'

@admin_router.message(F.text == '🔐 АДМІН-ПАНЕЛЬ')
async def show_admin_panel(message: Message):
    role = await get_user_role(message.from_user.id)
    if role == 'user': return
    await message.answer(f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>', reply_markup=akb.get_admin_main_kb(role), parse_mode='HTML')

@admin_router.callback_query(F.data == 'admin_panel_back')
async def back_to_admin_main(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await safe_edit_message(callback.message, f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>', reply_markup=akb.get_admin_main_kb(role), parse_mode='HTML')

@admin_router.callback_query(F.data == 'active_panel')
async def show_active_panel(callback: CallbackQuery):
    await safe_edit_message(callback.message, '🛍 <b>КЕРУВАННЯ ЗАМОВЛЕННЯМИ:</b>', reply_markup=akb.get_active_types_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'active_orders')
async def list_active_orders(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    locs = None
    if role not in ('boss', 'owner', 'developer'):
        locs = await admin_db.get_locations_for_admin(callback.from_user.id)
    
    orders = await active_orders_db.get_active_orders(locs)
    if not orders:
        await callback.answer('Немає активних замовлень.')
        return
    await safe_edit_message(callback.message, '🛍 <b>АКТИВНІ ЗАМОВЛЕННЯ:</b>\nНатисніть для завершення:', reply_markup=akb.get_active_orders_list_kb(orders), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('finish_order_'))
async def finish_order(callback: CallbackQuery):
    oid = callback.data.replace('finish_order_', '')
    await active_orders_db.remove_order(oid)
    await callback.answer('Замовлення виконано!')
    await list_active_orders(callback)

@admin_router.callback_query(F.data == 'beans_manage')
async def manage_beans(callback: CallbackQuery):
    await safe_edit_message(callback.message, '☕️ <b>КЕРУВАННЯ ЗЕРНАМИ:</b>', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'bean_add')
async def add_bean_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer('Вкажіть назву нового сорту:')
    await state.set_state(AdminStates.adding_bean_name)

@admin_router.message(AdminStates.adding_bean_name)
async def add_bean_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Вкажіть ціну за 250г:')
    await state.set_state(AdminStates.adding_bean_price)

@admin_router.message(AdminStates.adding_bean_price)
async def add_bean_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price_250=price)
        await coffee_beans_db.add_bean(name=(await state.get_data())['name'], price_250=price)
        await message.answer('✅ Сорт додано!', reply_markup=akb.get_beans_manage_kb())
        await state.clear()
    except:
        await message.answer('Помилка. Вкажіть число ціною:')

@admin_router.callback_query(F.data.startswith('admin_auth_confirm_'))
async def confirm_admin_login(callback: CallbackQuery, bot: Bot):
    uid = int(callback.data.replace('admin_auth_confirm_', ''))
    code = f"LOGIN_{uid}_{int(time.time())}"
    await admin_db.create_auth_request(uid, code)
    try:
        await bot.send_message(uid, f"✅ <b>ВХІД ПІДТВЕРДЖЕНО!</b>\n\nВаш код для сайту: <code>{code}</code>", parse_mode='HTML')
        await callback.answer('Підтверджено!')
        await callback.message.delete()
    except:
        await callback.answer('Помилка відправки повідомлення.', show_alert=True)

@admin_router.callback_query(F.data.startswith('admin_auth_reject_'))
async def reject_admin_login(callback: CallbackQuery, bot: Bot):
    uid = int(callback.data.replace('admin_auth_reject_', ''))
    try:
        await bot.send_message(uid, "❌ <b>ВХІД ВІДХИЛЕНО.</b>", parse_mode='HTML')
        await callback.answer('Відхилено.')
        await callback.message.delete()
    except:
        await callback.answer('Помилка.')

async def deliver_guest_message(bot: Bot, order: dict, user_text: str, admin_text: str):
    uid = order.get('user_id')
    if uid:
        try: await bot.send_message(uid, user_text, parse_mode='HTML')
        except: pass
    else:
        logger.info(f"No user_id for order {order.get('_id')}, skipping user notification")
