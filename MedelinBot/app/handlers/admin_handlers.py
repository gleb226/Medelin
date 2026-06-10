
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

import time

logger = logging.getLogger(__name__)

admin_router = Router()

class AdminStates(StatesGroup):
    adding_admin_id = State()
    adding_admin_role = State()
    choosing_admin_locations = State()
    
    # Bean management states
    adding_bean_name = State()
    adding_bean_photo = State()
    adding_bean_description = State()
    adding_bean_species = State()
    adding_bean_roast = State()
    adding_bean_score = State()
    adding_bean_harvest = State()
    adding_bean_descriptors = State()
    adding_bean_variety = State()
    adding_bean_altitude = State()
    adding_bean_processing = State()
    adding_bean_price = State()
    
    editing_bean_field = State()
    
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
    await message.answer(f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>\n\nВиберіть розділ керування:', reply_markup=akb.get_admin_main_kb(role), parse_mode='HTML')

@admin_router.callback_query(F.data == 'admin_panel_back')
async def back_to_admin_main(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await safe_edit_message(callback.message, f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>\n\nВиберіть розділ керування:', reply_markup=akb.get_admin_main_kb(role), parse_mode='HTML')

# --- ORDERS BLOCK ---

@admin_router.message(F.text == '🆕 НОВІ ЗАМОВЛЕННЯ')
async def list_new_orders_msg(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    await show_new_orders(message)

@admin_router.callback_query(F.data == 'new_orders')
async def list_new_orders_cb(callback: CallbackQuery):
    await show_new_orders(callback.message)
    await callback.answer()

async def show_new_orders(message: Message):
    orders = await orders_db.get_new_orders()
    if not orders:
        await message.answer('🆕 <b>НОВІ ЗАМОВЛЕННЯ:</b>\nНаразі нових замовлень немає.', parse_mode='HTML')
        return
    
    for o in orders:
        oid = str(o['_id'])
        order_num = o.get('order_number', '—')
        status_label = "НОВЕ" if o.get('status') == 'new' else "ОПЛАЧЕНО"
        
        type_map = { 'takeaway': 'З собою', 'in_house': 'В закладі', 'nova_poshta': 'Доставка', 'beans_delivery': 'Зерна', 'beans_booking': 'Зерна (Самовивіз)' }
        order_type = o.get('order_type')
        type_label = type_map.get(order_type, order_type)
        if order_type in ('nova_poshta', 'beans_delivery'):
            di = o.get('delivery_info', '')
            if 'вул.' in di: type_label = "Кур'єр"
            else: type_label = "Відділення"

        pay_mode = o.get('payment_mode', '—')
        if pay_mode == 'pay_now': pay_label = "ОПЛАЧЕНО" if o.get('status') == 'paid' else "КАРТКА (Очікується)"
        elif pay_mode == 'pay_at_checkout': pay_label = "Накладний платіж" if order_type in ('nova_poshta', 'beans_delivery') else "НА КАСІ"
        else: pay_label = pay_mode

        msg = f"📦 <b>ЗАМОВЛЕННЯ #{order_num}</b> ({status_label})\n\n"
        msg += f"👤 <b>{o.get('fullname')}</b>\n"
        msg += f"📞 <code>{o.get('phone')}</code>\n"
        msg += f"🚚 Куди: <b>{type_label} {o.get('delivery_info', '')}</b>\n"
        msg += f"💰 Сума: <b>{o.get('total_amount')} ₴</b>\n"
        msg += f"💳 Оплата: <b>{pay_label}</b>\n\n"
        msg += f"🛒 {o.get('cart')}\n\n"
        msg += f"📝 ПОБАЖАННЯ: <b>{o.get('wishes') or '—'}</b>"
        
        await message.answer(msg, reply_markup=akb.get_booking_manage_kb(oid, o.get('user_id') or -1), parse_mode='HTML')

@admin_router.message(F.text == '📦 АКТИВНІ ЗАМОВЛЕННЯ')
async def list_active_orders_msg(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    await show_active_orders(message)

@admin_router.callback_query(F.data == 'active_orders')
async def list_active_orders_cb(callback: CallbackQuery):
    await show_active_orders(callback.message)
    await callback.answer()

async def show_active_orders(message: Message):
    orders = await active_orders_db.get_all_active_orders()
    if not orders:
        await message.answer('📦 <b>АКТИВНІ ЗАМОВЛЕННЯ:</b>\nНаразі активних замовлень немає.', parse_mode='HTML')
        return
    
    for o in orders:
        oid = o.get('order_id')
        full_o = await orders_db.get_order_by_id(oid)
        if not full_o: continue
        
        order_num = full_o.get('order_number', '—')
        
        type_map = { 'takeaway': 'З собою', 'in_house': 'В закладі', 'nova_poshta': 'Доставка', 'beans_delivery': 'Зерна', 'beans_booking': 'Зерна (Самовивіз)' }
        order_type = full_o.get('order_type')
        type_label = type_map.get(order_type, order_type)
        if order_type in ('nova_poshta', 'beans_delivery'):
            di = full_o.get('delivery_info', '')
            if 'вул.' in di: type_label = "Кур'єр"
            else: type_label = "Відділення"

        pay_mode = full_o.get('payment_mode', '—')
        if pay_mode == 'pay_now': pay_label = "ОПЛАЧЕНО" if full_o.get('status') == 'paid' else "КАРТКА"
        elif pay_mode == 'pay_at_checkout': pay_label = "Накладний платіж" if order_type in ('nova_poshta', 'beans_delivery') else "НА КАСІ"
        else: pay_label = pay_mode

        msg = f"📦 <b>АКТИВНЕ #{order_num}</b>\n\n"
        msg += f"👤 <b>{full_o.get('fullname')}</b>\n"
        msg += f"📞 <code>{full_o.get('phone')}</code>\n"
        msg += f"🚚 Куди: <b>{type_label} {full_o.get('delivery_info', '')}</b>\n"
        msg += f"💰 Сума: <b>{full_o.get('total_amount', 0)} ₴</b>\n"
        msg += f"💳 Оплата: <b>{pay_label}</b>\n\n"
        msg += f"🛒 {full_o.get('cart')}\n\n"
        msg += f"📝 ПОБАЖАННЯ: <b>{full_o.get('wishes') or '—'}</b>"
        
        kb_finish = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✅ ЗАВЕРШИТИ', callback_data=f'finish_order_{oid}')]
        ])
        await message.answer(msg, reply_markup=kb_finish, parse_mode='HTML')

@admin_router.message(F.text.startswith('/view_order_'))
async def view_order_details(message: Message, bot: Bot):
    if not await admin_db.is_admin(message.from_user.id): return
    oid = message.text.replace('/view_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await message.answer("Замовлення не знайдено.")
        return
    
    order_num = order.get('order_number', '—')
    status_label = "НОВЕ" if order.get('status') == 'new' else "ОПЛАЧЕНО"
    type_map = { 'takeaway': 'З собою', 'in_house': 'В закладі', 'nova_poshta': 'Доставка', 'beans_delivery': 'Зерна', 'beans_booking': 'Зерна (Самовивіз)' }
    order_type = order.get('order_type')
    type_label = type_map.get(order_type, order_type)
    if order_type in ('nova_poshta', 'beans_delivery'):
        di = order.get('delivery_info', '')
        if 'вул.' in di: type_label = "Кур'єр"
        else: type_label = "Відділення"
    
    msg = f"📦 <b>ЗАМОВЛЕННЯ #{order_num}</b> ({status_label})\n\n"
    msg += f"👤 Клієнт: <b>{order.get('fullname')}</b>\n"
    msg += f"📞 Телефон: <code>{order.get('phone')}</code>\n"
    msg += f"🚚 Куди: <b>{type_label} {order.get('delivery_info', '')}</b>\n"
    msg += f"💰 Сума: <b>{order.get('total_amount')} ₴</b>\n"
    msg += f"💳 Оплата: <b>{order.get('payment_mode')}</b>\n\n"
    msg += f"🛒 <b>СКЛАД:</b>\n{order.get('cart')}\n\n"
    msg += f"📝 ПОБАЖАННЯ: <b>{order.get('wishes') or '—'}</b>"
    
    await message.answer(msg, reply_markup=akb.get_booking_manage_kb(oid, order.get('user_id') or -1), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('confirm_order_'))
async def confirm_order_handler(callback: CallbackQuery, bot: Bot):
    oid = callback.data.replace('confirm_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await callback.answer('Замовлення не знайдено.')
        return
    
    await orders_db.update_status(oid, 'confirmed')
    # Add to active orders if not there
    await active_orders_db.add_active_order(
        oid, order.get('user_id'), order.get('fullname'), order.get('phone'), 
        order.get('location_id'), order.get('cart'), order.get('order_type'), 
        order.get('table_number', ''), order.get('total_amount'), 
        order.get('payment_mode'), order.get('wishes')
    )
    
    await safe_edit_message(callback.message, callback.message.text + "\n\n✅ <b>ПІДТВЕРДЖЕНО</b>", parse_mode='HTML')
    await callback.answer('Підтверджено!')

@admin_router.callback_query(F.data.startswith('reject_order_'))
async def reject_order_handler(callback: CallbackQuery, bot: Bot):
    oid = callback.data.replace('reject_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await callback.answer('Замовлення не знайдено.')
        return
    
    await orders_db.update_status(oid, 'rejected')
    await safe_edit_message(callback.message, callback.message.text + "\n\n❌ <b>ВІДХИЛЕНО</b>", parse_mode='HTML')
    await callback.answer('Відхилено.')

@admin_router.callback_query(F.data.startswith('finish_order_'))
async def finish_order_handler(callback: CallbackQuery, bot: Bot):
    oid = callback.data.replace('finish_order_', '')
    await active_orders_db.delete_active_order(oid)
    await callback.answer('Замовлення завершено!')
    try:
        await callback.message.delete()
    except:
        await safe_edit_message(callback.message, callback.message.text + "\n\n✅ <b>ЗАВЕРШЕНО</b>")


# --- CONTENT MANAGEMENT BLOCK ---

@admin_router.message(F.text == '☕️ ЗЕРНА')
async def manage_beans_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer', 'boss'): return
    await message.answer('☕️ <b>ЗЕРНА:</b>\nКеруйте асортиментом кави.', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '📍 ЛОКАЦІЇ')
async def manage_locations_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer', 'boss'): return
    await message.answer('📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ:</b>\nНалаштування кав\'ярень та точок видачі.', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '📞 КОНТАКТИ')
async def manage_contacts_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer', 'boss'): return
    await message.answer('📞 <b>КЕРУВАННЯ КОНТАКТАМИ:</b>\nРедагування посилань на соцмережі та контакти.', reply_markup=akb.get_contacts_manage_kb(), parse_mode='HTML')

# --- SYSTEM MANAGEMENT BLOCK ---

@admin_router.message(F.text == '👤 ПЕРСОНАЛ')
async def manage_staff_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer'): return
    await message.answer('👤 <b>КЕРУВАННЯ ПЕРСОНАЛОМ:</b>\nДодавання адміністраторів та менеджерів.', reply_markup=akb.get_staff_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '📊 СТАТИСТИКА')
async def show_stats_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer'): return
    await message.answer('📊 <b>СТАТИСТИКА ПРОДАЖІВ:</b>\n(Розділ знаходиться в розробці)', parse_mode='HTML')

@admin_router.callback_query(F.data == 'beans_manage')
async def manage_beans_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, '☕️ <b>ЗЕРНА:</b>', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'locations_manage')
async def manage_locations_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, '📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ:</b>', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'contacts_manage')
async def manage_contacts_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, '📞 <b>КЕРУВАННЯ КОНТАКТАМИ:</b>', reply_markup=akb.get_contacts_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data.in_(['beans_list', 'beans_list_edit', 'beans_list_del']))
async def list_beans_admin(callback: CallbackQuery):
    mode = 'list'
    if 'edit' in callback.data: mode = 'edit'
    elif 'del' in callback.data: mode = 'del'
    
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer('Сорти відсутні.')
        return
    
    mode_titles = {'list': 'СПИСОК', 'edit': 'РЕДАГУВАННЯ', 'del': 'ВИДАЛЕННЯ'}
    text = f"📜 <b>{mode_titles[mode]} ЗЕРЕН:</b>"
    
    keyboard = []
    row = []
    for b in beans:
        bid = str(b['_id'])
        cb = f"bean_edit_{bid}"
        if mode == 'del': cb = f"bean_del_confirm_{bid}"
        
        # Grid logic: 2 columns
        row.append(InlineKeyboardButton(text=f"⚙️ {b['name'][:18]}", callback_data=cb))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='beans_manage')])
    await safe_edit_message(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('bean_edit_'))
async def edit_bean_menu(callback: CallbackQuery):
    bid = callback.data.replace('bean_edit_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if not bean: return
    
    text = f"⚙️ <b>РЕДАГУВАННЯ: {bean['name']}</b>\n\n"
    text += f"💰 Ціна: <b>{bean.get('price_250')} ₴</b>\n"
    text += f"📊 Оцінка: <b>{bean.get('quality_score') or '—'}</b>\n"
    text += f"🔥 Обсмаження: <b>{bean.get('roast') or '—'}</b>\n"
    text += f"📝 Опис: <i>{bean.get('description')[:50] if bean.get('description') else '—'}...</i>\n\n"
    text += "Виберіть параметр для зміни:"
    
    await safe_edit_message(callback.message, text, reply_markup=akb.get_bean_edit_fields_kb(bid), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('bean_fedit_'))
async def edit_bean_single_field_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    bid = parts[2]
    field = parts[3]
    
    field_names = {
        'name': 'назву', 'price': 'ціну', 'photo': 'фото', 'description': 'опис',
        'species': 'склад', 'roast': 'тип обсмаження', 'score': 'оцінку SCA',
        'harvest': 'рік врожаю', 'descriptors': 'дескриптори', 'variety': 'різновид',
        'altitude': 'висоту', 'processing': 'метод обробки'
    }
    
    await state.update_data(edit_bean_id=bid, edit_single_field=field)
    msg = f"📝 Вкажіть нове значення для поля <b>{field_names.get(field, field).upper()}</b>:"
    if field == 'photo': msg = "📸 Скиньте нове ФОТО:"
    
    await callback.message.answer(msg, parse_mode='HTML')
    await state.set_state(AdminStates.editing_bean_field)
    await state.update_data(edit_step='single_field')

@admin_router.callback_query(F.data.startswith('bean_del_confirm_'))
async def delete_bean_confirm(callback: CallbackQuery):
    bid = callback.data.replace('bean_del_confirm_', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🗑 ТАК, ВИДАЛИТИ', callback_data=f'bean_del_final_{bid}')],
        [InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data=f'bean_edit_{bid}')]
    ])
    await safe_edit_message(callback.message, "⚠️ <b>ВИ ВПЕВНЕНІ?</b>\nЦе дію неможливо скасувати.", reply_markup=kb, parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('bean_del_final_'))
async def delete_bean_final(callback: CallbackQuery):
    bid = callback.data.replace('bean_del_final_', '')
    await coffee_beans_db.delete_bean(bid)
    await callback.answer('Сорт видалено!')
    await list_beans_admin(callback)

@admin_router.callback_query(F.data == 'bean_add_cancel')
async def add_bean_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_message(callback.message, '❌ <b>ДОДАВАННЯ СКАСОВАНО</b>', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'bean_add')
async def add_bean_start(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await callback.message.answer('✨ <b>КРОК 1:</b> Вкажіть назву нового сорту\n(напр. <i>Ethiopia Yirgacheffe</i>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_name)

@admin_router.message(AdminStates.adding_bean_name)
async def add_bean_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('📸 <b>КРОК 2:</b> Скиньте фото або відправте <code>-</code> якщо фото немає:', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_photo)

from app.utils.photo_utils import process_photo

@admin_router.message(AdminStates.adding_bean_photo)
async def add_bean_photo(message: Message, state: FSMContext, bot: Bot):
    url = await process_photo(message, bot)
    await state.update_data(image_url=url)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('💰 <b>КРОК 3:</b> Вкажіть ціну за 250г (тільки число):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_price)

@admin_router.message(AdminStates.adding_bean_price)
async def add_bean_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price_250=price)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
        await message.answer('📝 <b>КРОК 4:</b> Напишіть опис кави (кілька речень):', reply_markup=kb, parse_mode='HTML')
        await state.set_state(AdminStates.adding_bean_description)
    except:
        await message.answer('❌ <b>ПОМИЛКА:</b> Вкажіть ціну числом (напр. 250):', parse_mode='HTML')

@admin_router.message(AdminStates.adding_bean_description)
async def add_bean_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('🌿 <b>КРОК 5:</b> Вкажіть склад / вид (напр. <i>100% Арабіка</i>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_species)

@admin_router.message(AdminStates.adding_bean_species)
async def add_bean_species(message: Message, state: FSMContext):
    await state.update_data(species=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('🔥 <b>КРОК 6:</b> Тип обсмаження (напр. <i>Espresso</i> або <i>Filter</i>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_roast)

@admin_router.message(AdminStates.adding_bean_roast)
async def add_bean_roast(message: Message, state: FSMContext):
    await state.update_data(roast=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('📊 <b>КРОК 7:</b> Оцінка якості SCA Score (напр. <i>86.5</i> або <code>0</code>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_score)

@admin_router.message(AdminStates.adding_bean_score)
async def add_bean_score(message: Message, state: FSMContext):
    await state.update_data(quality_score=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('📅 <b>КРОК 8:</b> Рік врожаю (напр. <i>2023</i>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_harvest)

@admin_router.message(AdminStates.adding_bean_harvest)
async def add_bean_harvest(message: Message, state: FSMContext):
    await state.update_data(harvest=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('🍓 <b>КРОК 9:</b> Дескриптори (напр. <i>Цитрус, Шоколад</i>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_descriptors)

@admin_router.message(AdminStates.adding_bean_descriptors)
async def add_bean_descriptors(message: Message, state: FSMContext):
    await state.update_data(descriptors=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('🧬 <b>КРОК 10:</b> Різновид (напр. <i>Heirloom, Typica</i>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_variety)

@admin_router.message(AdminStates.adding_bean_variety)
async def add_bean_variety(message: Message, state: FSMContext):
    await state.update_data(variety=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('⛰ <b>КРОК 11:</b> Висота зростання (напр. <i>1900 м</i>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_altitude)

@admin_router.message(AdminStates.adding_bean_altitude)
async def add_bean_altitude(message: Message, state: FSMContext):
    await state.update_data(altitude=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])
    await message.answer('🧪 <b>КРОК 12:</b> Метод обробки (напр. <i>Митий, Натуральний</i>):', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.adding_bean_processing)

@admin_router.message(AdminStates.adding_bean_processing)
async def add_bean_processing(message: Message, state: FSMContext):
    await state.update_data(processing=message.text)
    data = await state.get_data()
    try:
        await coffee_beans_db.add_bean(
            name=data['name'],
            price_250=data['price_250'],
            image_url=data.get('image_url', ''),
            description=data.get('description', ''),
            species=data.get('species', ''),
            roast=data.get('roast', ''),
            quality_score=data.get('quality_score', '0'),
            harvest=data.get('harvest', ''),
            descriptors=data.get('descriptors', ''),
            variety=data.get('variety', ''),
            altitude=data.get('altitude', ''),
            processing=data.get('processing', '')
        )
        await message.answer('✅ <b>УСПІХ:</b> Сорт успішно додано до каталогу!', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')
        await state.clear()
    except Exception as e:
        logger.error(f"Error adding bean: {e}")
        await message.answer('❌ <b>ПОМИЛКА:</b> Не вдалося зберегти сорт. Спробуйте ще раз.', parse_mode='HTML')
        await state.clear()

@admin_router.callback_query(F.data.startswith('bean_full_edit_'))
async def edit_bean_full_start(callback: CallbackQuery, state: FSMContext):
    bid = callback.data.replace('bean_full_edit_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if not bean:
        await callback.answer('Сорт не знайдено.')
        return
    
    await state.update_data(edit_bean_id=bid)
    await callback.message.answer(f"📝 <b>РЕДАГУВАННЯ: {bean['name']}</b>\n\nВкажіть НОВУ назву або <code>.</code>:", parse_mode='HTML')
    await state.set_state(AdminStates.editing_bean_field)
    await state.update_data(edit_step='name')

@admin_router.message(AdminStates.editing_bean_field)
async def edit_bean_field_logic(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    step = data.get('edit_step')
    bid = data.get('edit_bean_id')
    val = (message.text or "").strip()
    
    if step == 'single_field':
        field = data.get('edit_single_field')
        update = {}
        
        if field == 'photo':
            url = await process_photo(message, bot)
            update['image_url'] = url
        elif field == 'price':
            try: update['price_250'] = int(val)
            except:
                await message.answer('❌ <b>ПОМИЛКА:</b> Введіть число для ціни:')
                return
        elif field == 'score':
            update['quality_score'] = val
        else:
            update[field] = val
        
        await coffee_beans_db.update_bean(bid, update)
        bean = await coffee_beans_db.get_bean_by_id(bid)
        
        text = f"✅ Параметр <b>{field.upper()}</b> оновлено!\n\n"
        text += f"⚙️ <b>РЕДАГУВАННЯ: {bean['name']}</b>\n"
        text += f"💰 Ціна: <b>{bean.get('price_250')} ₴</b>\n"
        text += f"📊 Оцінка: <b>{bean.get('quality_score') or '—'}</b>\n"
        text += f"🔥 Обсмаження: <b>{bean.get('roast') or '—'}</b>\n"
        
        await message.answer(text, parse_mode='HTML', reply_markup=akb.get_bean_edit_fields_kb(bid))
        await state.clear()
        return

    skip = (val == '.')
    
    if step == 'name':
        if not skip: await state.update_data(name=val)
        await message.answer('Нове фото або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='photo')
    
    elif step == 'photo':
        if not skip:
            url = await process_photo(message, bot)
            await state.update_data(image_url=url)
        await message.answer('Нова ціна або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='price')

    elif step == 'price':
        if not skip:
            try:
                await state.update_data(price_250=int(val))
            except:
                await message.answer('Ціна має бути числом. Спробуйте ще раз або <code>.</code>:', parse_mode='HTML')
                return
        await message.answer('Новий ОПИС або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='description')
        
    elif step == 'description':
        if not skip: await state.update_data(description=val)
        await message.answer('Новий склад або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='species')
        
    elif step == 'species':
        if not skip: await state.update_data(species=val)
        await message.answer('Нове обсмаження або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='roast')
        
    elif step == 'roast':
        if not skip: await state.update_data(roast=val)
        await message.answer('Нова оцінка або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='score')
        
    elif step == 'score':
        if not skip: await state.update_data(quality_score=val)
        await message.answer('Новий врожай або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='harvest')
        
    elif step == 'harvest':
        if not skip: await state.update_data(harvest=val)
        await message.answer('Нові дескриптори або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='descriptors')
        
    elif step == 'descriptors':
        if not skip: await state.update_data(descriptors=val)
        await message.answer('Новий різновид або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='variety')
        
    elif step == 'variety':
        if not skip: await state.update_data(variety=val)
        await message.answer('Нова висота або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='altitude')
        
    elif step == 'altitude':
        if not skip: await state.update_data(altitude=val)
        await message.answer('Новий метод обробки або <code>.</code>:', parse_mode='HTML')
        await state.update_data(edit_step='processing')
        
    elif step == 'processing':
        if not skip: await state.update_data(processing=val)
        
        update = {}
        latest_data = await state.get_data()
        fields = ['name', 'image_url', 'description', 'species', 'roast', 'quality_score', 'harvest', 'descriptors', 'variety', 'altitude', 'processing', 'price_250']
        for f in fields:
            if f in latest_data: update[f] = latest_data[f]
        
        if update:
            await coffee_beans_db.update_bean(bid, update)
            await message.answer('✅ Сорт оновлено!', reply_markup=akb.get_beans_manage_kb())
        else:
            await message.answer('Змін не внесено.', reply_markup=akb.get_beans_manage_kb())
            
        await state.clear()


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
    # DISABLED
    return
