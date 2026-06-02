
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
    choosing_bean_payment = State()

@order_router.callback_query(F.data == 'bean_back')
async def bean_back(callback: CallbackQuery, state: FSMContext):
    from app.handlers.user_handlers import show_beans
    await show_beans(callback.message)
    await callback.message.delete()
    await state.clear()

@order_router.callback_query(F.data == 'bean_w_250')
async def bean_weight_chosen(callback: CallbackQuery, state: FSMContext):
    await state.update_data(weight=250)
    kb_del = kb.get_beans_delivery_kb()
    await safe_edit_message(callback.message, '🚚 <b>ОБЕРІТЬ СПОСІБ ОТРИМАННЯ:</b>', reply_markup=kb_del, parse_mode='HTML')
    await state.set_state(OrderStates.choosing_bean_delivery)

@order_router.callback_query(F.data == 'bean_del_np', OrderStates.choosing_bean_delivery)
async def bean_delivery_np(callback: CallbackQuery, state: FSMContext):
    await state.update_data(delivery_type='nova_poshta', location_id='NP')
    await callback.message.answer('🏙 <b>ВКАЖІТЬ ВАШЕ МІСТО (або частину назви):</b>', parse_mode='HTML')
    await state.set_state(OrderStates.entering_phone) # Simplified: just ask for phone for now

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
    rid = await orders_db.add_order(
        user_id=user.id, username=user.username, fullname=user.full_name, phone=data.get('phone', '—'), 
        location_id=data.get('location_id') or "NP", wishes=f"ВАГА: 250г", 
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
    
    rid = await orders_db.add_order(
        user_id=user.id, username=user.username, fullname=user.full_name, phone=data.get('phone', '—'), 
        location_id=data.get('location_id') or "NP", wishes=f"ВАГА: 250г", 
        cart=f"ЗЕРНА: {data['bean_name']}", order_type=order_type,
        date_time='НОВА ПОШТА', people_count='0',
        payment_mode='pay_on_delivery', total_amount=data.get('base_price', 0)
    )

    await active_orders_db.add_active_order(
        rid, user.id, user.full_name, data.get('phone', '—'), data.get('location_id') or "NP", 
        data['bean_name'], order_type, total=data.get('base_price', 0), 
        payment_mode='pay_on_delivery', wishes="ВАГА: 250г"
    )

    msg = f"☕️ <b>НОВЕ ЗАМОВЛЕННЯ ЗЕРЕН</b>\n\n👤 <b>КЛІЄНТ:</b> {user.full_name}\n📞 <b>ТЕЛЕФОН:</b> <code>{data.get('phone')}</code>\n📦 <b>СОРТ:</b> {data['bean_name']} (250г)\n🚚 <b>ДОСТАВКА:</b> НОВА ПОШТА\n📦 <b>ОПЛАТА:</b> НАКЛАДЕНИЙ ПЛАТІЖ"

    targets = await admin_db.get_notification_targets(data.get('location_id'))
    for aid in targets:
        try: await bot.send_message(aid, msg, reply_markup=akb.get_booking_manage_kb(rid), parse_mode='HTML')
        except: pass

    await bot.send_message(chat_id, '✅ <b>ДЯКУЄМО!</b> Ваше замовлення прийнято.', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')
    await state.clear()
