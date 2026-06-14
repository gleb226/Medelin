
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from app.common.config import PAYMENT_TOKEN

from app.databases.orders_database import orders_db

from app.databases.active_orders_database import active_orders_db

from app.databases.user_database import user_db

from app.databases.admin_database import admin_db

from app.databases.sales_database import sales_db

from app.databases.location_database import location_db

from app.databases.mongo_client import get_db

from app.databases.coffee_beans_database import coffee_beans_db

import logging

from app.utils.logger import log_activity

from app.utils.time_utils import is_working_hours, get_closed_message

from app.utils.message_utils import safe_edit_message

import app.keyboards.admin_keyboards as akb

import app.keyboards.user_keyboards as kb

import re, time

order_router = Router()

from app.utils.nova_poshta import np_client

class OrderStates(StatesGroup):
    choosing_order_type = State()
    choosing_location = State()
    entering_table_number = State()
    choosing_payment_mode = State()
    entering_pickup_time = State()
    entering_wishes = State()
    entering_phone = State()
    choosing_bean_weight = State()
    choosing_bean_delivery = State()
    searching_np_city = State()
    choosing_np_warehouse = State()
    choosing_bean_payment = State()

@order_router.callback_query(F.data == 'bean_del_np', OrderStates.choosing_bean_delivery)
async def bean_delivery_np(callback: CallbackQuery, state: FSMContext):
    await state.update_data(delivery_type='nova_poshta', location_id='NP')
    await safe_edit_message(callback.message, '🏙 <b>ВКАЖІТЬ ВАШЕ МІСТО (або частину назви):</b>', parse_mode='HTML')
    await state.set_state(OrderStates.searching_np_city)

@order_router.message(OrderStates.searching_np_city)
async def np_city_search(message: Message, state: FSMContext):
    search = (message.text or '').strip()
    if len(search) < 2:
        await message.answer('Назва занадто коротка. Спробуйте ще раз:')
        return
    
    cities = await np_client.search_settlements(search)
    if not cities:
        await message.answer('🏙 Місто не знайдено. Спробуйте іншу назву:')
        return
    
    await message.answer(f'🔍 <b>РЕЗУЛЬТАТИ ПОШУКУ "{search}":</b>', reply_markup=kb.get_np_cities_kb(cities), parse_mode='HTML')

@order_router.callback_query(F.data.startswith('np_city_'), OrderStates.searching_np_city)
async def np_city_chosen(callback: CallbackQuery, state: FSMContext):
    city_ref = callback.data.replace('np_city_', '')
    # Find city name from keyboard (or we could store it in state during search)
    city_name = "Місто"
    for row in callback.message.reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data == callback.data:
                city_name = button.text
                break
    
    await state.update_data(np_city_ref=city_ref, np_city_name=city_name)
    
    warehouses = await np_client.get_warehouses(city_ref)
    if not warehouses:
        await callback.answer('У цьому місті не знайдено відділень.', show_alert=True)
        return
    
    await state.update_data(all_warehouses=warehouses) # Cache for pagination
    await safe_edit_message(callback.message, f'🏪 <b>ОБЕРІТЬ ВІДДІЛЕННЯ ({city_name}):</b>\n\nМожна ввести номер або вулицю для пошуку:', reply_markup=kb.get_np_warehouses_kb(warehouses), parse_mode='HTML')
    await state.set_state(OrderStates.choosing_np_warehouse)

@order_router.message(OrderStates.choosing_np_warehouse)
async def np_wh_search(message: Message, state: FSMContext):
    search = (message.text or '').strip()
    data = await state.get_data()
    city_ref = data.get('np_city_ref')
    if not city_ref:
        await message.answer('Спочатку оберіть місто.')
        return
    
    warehouses = await np_client.get_warehouses(city_ref, search)
    if not warehouses:
        await message.answer('Нічого не знайдено. Спробуйте інший номер або вулицю:')
        return
    
    await message.answer(f'🔍 <b>РЕЗУЛЬТАТИ ПОШУКУ "{search}":</b>', reply_markup=kb.get_np_warehouses_kb(warehouses), parse_mode='HTML')

@order_router.callback_query(F.data.startswith('np_wh_page_'), OrderStates.choosing_np_warehouse)

async def np_wh_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.replace('np_wh_page_', ''))
    data = await state.get_data()
    warehouses = data.get('all_warehouses', [])
    await safe_edit_message(callback.message, callback.message.text, reply_markup=kb.get_np_warehouses_kb(warehouses, page=page), parse_mode='HTML')

@order_router.callback_query(F.data.startswith('np_wh_'), OrderStates.choosing_np_warehouse)
async def np_wh_chosen(callback: CallbackQuery, state: FSMContext):
    wh_ref = callback.data.replace('np_wh_', '')
    wh_name = "Відділення"
    for row in callback.message.reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data == callback.data:
                wh_name = button.text
                break
    
    await state.update_data(np_warehouse=wh_name)
    await ask_phone_order(callback, state)

async def ask_phone_order(target, state: FSMContext):
    text = '📞 <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН (+380...):</b>\n\nНатисніть кнопку нижче або введіть вручну:'
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, parse_mode='HTML', reply_markup=kb.get_phone_kb())
    else:
        await target.answer(text, parse_mode='HTML', reply_markup=kb.get_phone_kb())
    await state.set_state(OrderStates.entering_phone)

@order_router.message(OrderStates.entering_phone)
async def order_phone_entered(message: Message, state: FSMContext, bot: Bot):
    phone = (message.text or '').strip()
    digits = ''.join((ch for ch in phone if ch.isdigit()))
    if len(digits) < 10:
        await message.answer('Некоректний телефон. Вкажіть у форматі +380...', parse_mode='HTML')
        return
    await state.update_data(phone=phone)
    await user_db.set_phone(message.from_user.id, phone)
    
    kb_pay = kb.get_beans_payment_kb()
    await message.answer('💳 <b>ОБЕРІТЬ СПОСІБ ОПЛАТИ:</b>', reply_markup=kb_pay, parse_mode='HTML')
    await state.set_state(OrderStates.choosing_bean_payment)

@order_router.callback_query(F.data.startswith('bean_pay_'), OrderStates.choosing_bean_payment)
async def bean_payment_chosen(callback: CallbackQuery, state: FSMContext, bot: Bot):
    pay_method = 'card' if callback.data == 'bean_pay_card' else 'cash'
    await state.update_data(payment_method=pay_method)
    
    if pay_method == 'card':
        await send_beans_invoice(callback.from_user, callback.message.chat.id, state, bot)
    else:
        await process_beans_final(callback.from_user, callback.message.chat.id, state, bot)

async def send_beans_invoice(user, chat_id, state, bot):
    data = await state.get_data()
    total = int(data.get('base_price') or 300)
    
    order_type = 'beans_delivery' if data.get('delivery_type') == 'nova_poshta' else 'beans_booking'
    rid, is_new = await orders_db.add_order(
        user_id=user.id, username=user.username, fullname=user.full_name, phone=data.get('phone', '—'), 
        location_id=data.get('location_id') or "NP", wishes="НОВА ПОШТА", 
        cart=f"ЗЕРНА: {data['bean_name']}", order_type=order_type,
        date_time='НОВА ПОШТА', people_count='0',
        payment_mode='pay_now', total_amount=total
    )

    payment_url = f"{WEB_APP_URL}/index.html?order_id={rid}"
    kb_pay = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💳 ПЕРЕЙТИ ДО ОПЛАТИ', url=payment_url)],
        [InlineKeyboardButton(text='❌ Скасувати', callback_data='back_main_menu_only')]
    ])

    await bot.send_message(chat_id, f"<b>💳 ОПЛАТА КАВИ</b>\n\n<b>Сорт:</b> {data['bean_name']}\n<b>Сума:</b> {total} ₴", reply_markup=kb_pay, parse_mode='HTML')

async def process_beans_final(user, chat_id, state, bot):
    data = await state.get_data()
    is_admin = await admin_db.is_admin(user.id)
    order_type = 'beans_delivery' if data.get('delivery_type') == 'nova_poshta' else 'beans_booking'
    
    delivery_info = f"{data.get('np_city_name', '')}, {data.get('np_warehouse', '')}" if order_type == 'beans_delivery' else "Самовивіз"
    pay_label = "ОПЛАЧЕНО" if data.get('payment_method') == 'card' else "Накладний платіж"
    
    rid, is_new = await orders_db.add_order(
        user_id=user.id, username=user.username, fullname=user.full_name, phone=data.get('phone', '—'), 
        location_id=data.get('location_id') or "NP", wishes="НОВА ПОШТА", 
        cart=f"ЗЕРНА: {data['bean_name']}", order_type=order_type,
        date_time='НОВА ПОШТА', people_count='0',
        payment_mode='pay_on_delivery' if data.get('payment_method') != 'card' else 'pay_now', 
        total_amount=data.get('base_price', 0)
    )

    if is_new:
        msg = f"☕️ <b>НОВЕ ЗАМОВЛЕННЯ ЗЕРЕН</b>\n\n👤 {user.full_name}\n📞 <code>{data.get('phone')}</code>\n🚚 Куди: <b>{delivery_info}</b>"

        msg += f"\n📦 Сорт: <b>{data['bean_name']}</b>\n💳 Оплата: <b>{pay_label}</b>"
        msg += f"\n\n🛒 {data['bean_name']}"

        targets = await admin_db.get_notification_targets(data.get('location_id'))

        for aid in targets:
            try: await bot.send_message(aid, msg, reply_markup=akb.get_booking_manage_kb(rid), parse_mode='HTML')
            except: pass

    await bot.send_message(chat_id, '✅ <b>ДЯКУЄМО!</b> Ваше замовлення прийнято.', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')
    await state.clear()
