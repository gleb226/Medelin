
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from app.utils.paths import get_uploads_dir

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

from app.common.config import DEVELOPER_IDS, WEB_APP_URL

from app.databases.mongo_client import get_db
from app.utils.photo_utils import process_photo

import logging
from pathlib import Path

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
    editing_bean_field = State()
    
    # Location management states
    adding_location_name = State()
    editing_location_field = State()

LOCATION_ADD_STEPS = [
    ('name', '📝 <b>Введіть назву локації:</b>'),
    ('address', '🏠 <b>Введіть адресу:</b>'),
    ('schedule', '📅 <b>Введіть графік роботи</b> (напр. Пн-Нд 08:00-20:00):'),
    ('phone', '📞 <b>Введіть номер телефону:</b>'),
    ('email', '📧 <b>Введіть email:</b>'),
    ('google_maps_url', '🗺 <b>Введіть посилання на Google Maps:</b>'),
    ('photo', '📸 <b>Надішліть фото локації</b> (або - якщо немає):'),
    ('amenities', '✨ <b>Зручності</b> (через кому):'),
    ('atmosphere', '☁️ <b>Опис атмосфери:</b>')
]

LOCATION_EDIT_FIELDS = [field for field, _ in LOCATION_ADD_STEPS]

def _location_list_kb(locations: list[dict]) -> InlineKeyboardMarkup:
    keyboard = []
    # Grid: 2 columns
    row = []
    for l in locations:
        lid = str(l['_id'])
        name = l.get('name', '')[:25]
        row.append(InlineKeyboardButton(text=name, callback_data=f'loc_open_{lid}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text='➕ ДОДАТИ НОВУ ЛОКАЦІЮ', callback_data='location_new')])
    keyboard.append([InlineKeyboardButton(text='⬅️ НАЗАД В МЕНЮ', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def _location_card_text(loc: dict) -> str:
    lines = [
        f"📍 <b>{html.escape(str(loc.get('name') or 'Без назви'))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"🏠 Адреса: <b>{html.escape(str(loc.get('address') or '—'))}</b>",
        f"📅 Графік: <b>{html.escape(str(loc.get('schedule') or '—'))}</b>",
        f"📞 Тел: <code>{html.escape(str(loc.get('phone') or '—'))}</code>",
        f"📧 Email: <code>{html.escape(str(loc.get('email') or '—'))}</code>",
        f"🗺 Google Maps: <a href=\"{loc.get('google_maps_url', '#')}\">Відкрити</a>",
        f"✨ Зручності: <b>{html.escape(', '.join(loc.get('amenities', [])) if isinstance(loc.get('amenities'), list) else str(loc.get('amenities', '—')))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"☁️ <b>Атмосфера:</b>",
        f"{html.escape(str(loc.get('atmosphere') or '—'))}"
    ]
    return '\n'.join(lines)

async def show_locations_page(callback: CallbackQuery):
    locations = await location_db.get_all_locations()
    text = "📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ:</b>"
    if not locations:
        text += "\n\nСписок порожній."
    await safe_edit_message(callback.message, text, reply_markup=_location_list_kb(locations), parse_mode='HTML')
    await callback.answer()

async def show_location_card(target, loc: dict):
    text = _location_card_text(loc)
    kb = akb.get_location_card_kb(str(loc['_id']))
    
    image = str(loc.get('image_url') or '').strip()
    photo = None
    
    if image:
        if image.startswith('/uploads/') or image.startswith('/photos/'):
            # (Reuse existing logic for resolving local path)
            site_dir = Path("/usr/share/nginx/html")
            if not site_dir.exists():
                from app.utils.paths import get_site_dir
                site_dir = get_site_dir()
            uploads_dir = get_uploads_dir()
            if image.startswith('/uploads/'):
                filename = image.replace('/uploads/', '')
                local_path = uploads_dir / filename
            else:
                filename = image.lstrip('/')
                local_path = site_dir / filename
            if local_path.exists():
                photo = FSInputFile(local_path)
            elif WEB_APP_URL:
                photo = f"{WEB_APP_URL.rstrip('/')}{image}"
        elif image.startswith('http'):
            photo = image
        elif len(image) > 10 and '/' not in image:
            photo = image

    try:
        if photo:
            if isinstance(target, Message):
                await target.answer_photo(photo, caption=text, reply_markup=kb, parse_mode='HTML')
            else:
                await target.message.answer_photo(photo, caption=text, reply_markup=kb, parse_mode='HTML')
            return
    except Exception as e:
        logger.warning(f"Failed to send location photo: {e}")

    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode='HTML', disable_web_page_preview=True)
    else:
        await target.message.answer(text, reply_markup=kb, parse_mode='HTML', disable_web_page_preview=True)

# Location Handlers

@admin_router.callback_query(F.data == 'locations_list')
async def list_locations_cb(callback: CallbackQuery):
    await show_locations_page(callback)

@admin_router.callback_query(F.data == 'location_new')
async def add_location_new(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(loc_mode='add', loc_step_index=0, loc_steps=LOCATION_ADD_STEPS)
    await callback.message.answer('➕ <b>ДОДАВАННЯ ЛОКАЦІЇ</b>', parse_mode='HTML')
    await _ask_location_step(callback.message, state)
    await state.set_state(AdminStates.adding_location_name)
    await callback.answer()

async def _ask_location_step(message: Message, state: FSMContext):
    data = await state.get_data()
    step_index = int(data.get('loc_step_index', 0))
    steps = data.get('loc_steps') or LOCATION_ADD_STEPS
    field, prompt = steps[step_index]
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='location_cancel')]])
    await message.answer(prompt, reply_markup=cancel_kb, parse_mode='HTML')

@admin_router.callback_query(F.data == 'location_cancel')
async def location_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_message(callback.message, '❌ Дію скасовано.', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_open_'))
async def open_location_card(callback: CallbackQuery):
    lid = callback.data.replace('loc_open_', '')
    loc = await location_db.get_location_by_id(lid)
    if not loc:
        await callback.answer('Локацію не знайдено.', show_alert=True)
        return
    try:
        await callback.message.delete()
    except:
        pass
    await show_location_card(callback.message, loc)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_del_confirm_'))
async def delete_location_confirm(callback: CallbackQuery):
    lid = callback.data.replace('loc_del_confirm_', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🗑 ТАК, ВИДАЛИТИ', callback_data=f'loc_del_final_{lid}')],
        [InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data=f'loc_open_{lid}')]
    ])
    await safe_edit_message(callback.message, "Видалити цю локацію?", reply_markup=kb)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_del_final_'))
async def delete_location_final(callback: CallbackQuery):
    lid = callback.data.replace('loc_del_final_', '')
    await location_db.delete_location(lid)
    await callback.answer('Локацію видалено.')
    await show_locations_page(callback)

@admin_router.callback_query(F.data.startswith('loc_edit_fields_'))
async def edit_location_fields_menu(callback: CallbackQuery):
    lid = callback.data.replace('loc_edit_fields_', '')
    loc = await location_db.get_location_by_id(lid)
    if not loc:
        await callback.answer('Локацію не знайдено.', show_alert=True)
        return
    await safe_edit_message(callback.message, f"⚙️ <b>Оберіть поле для редагування:</b>\n{html.escape(str(loc.get('name', '')))}", reply_markup=akb.get_location_edit_fields_kb(lid), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_full_edit_'))
async def edit_location_full_start(callback: CallbackQuery, state: FSMContext):
    lid = callback.data.replace('loc_full_edit_', '')
    loc = await location_db.get_location_by_id(lid)
    if not loc:
        await callback.answer('Локацію не знайдено.', show_alert=True)
        return
    await state.clear()
    steps = [(field, f"{prompt}\nПоточне значення: {loc.get(field, '')}") for field, prompt in LOCATION_ADD_STEPS]
    await state.update_data(loc_mode='edit', edit_loc_id=lid, loc_step_index=0, loc_steps=steps)
    await callback.message.answer(f"✏️ <b>РЕДАГУВАННЯ: {html.escape(str(loc.get('name') or ''))}</b>", parse_mode='HTML')
    await _ask_location_step(callback.message, state)
    await state.set_state(AdminStates.editing_location_field)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_fedit_'))
async def edit_location_single_field_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    lid = parts[2]
    field = '_'.join(parts[3:])
    
    prompts = dict(LOCATION_ADD_STEPS)
    await state.clear()
    await state.update_data(loc_mode='single_edit', edit_loc_id=lid, edit_single_field=field)
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='location_cancel')]])
    await callback.message.answer(prompts.get(field, 'Нове значення:'), reply_markup=cancel_kb, parse_mode='HTML')
    await state.set_state(AdminStates.editing_location_field)
    await callback.answer()

@admin_router.message(AdminStates.adding_location_name)
@admin_router.message(AdminStates.editing_location_field)
async def location_flow_input(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    mode = data.get('loc_mode')
    
    if mode == 'single_edit':
        field = data.get('edit_single_field')
        if field == 'photo':
            value = await process_photo(message, bot)
            if not value:
                await message.answer('Не вдалося отримати фото. Надішліть фото з галереї або посилання.')
                return
        else:
            value = (message.text or '').strip()
            if not value: return
            if field == 'amenities':
                value = [s.strip() for s in value.split(',') if s.strip()]
        
        update_field = 'image_url' if field == 'photo' else field
        await location_db.update_location(data['edit_loc_id'], {update_field: value})
        loc = await location_db.get_location_by_id(data['edit_loc_id'])
        await message.answer('✅ Поле оновлено.')
        await state.clear()
        if loc: await show_location_card(message, loc)
        return

    steps = data.get('loc_steps') or LOCATION_ADD_STEPS
    step_index = int(data.get('loc_step_index', 0))
    field, _ = steps[step_index]
    
    if field == 'photo':
        value = await process_photo(message, bot)
        if not value and (message.text or '').strip() != '-':
            await message.answer('Надішліть фото або - для пропуску.')
            return
        await state.update_data(image_url=value)
    else:
        value = (message.text or '').strip()
        if not value: return
        if field == 'amenities':
            value = [s.strip() for s in value.split(',') if s.strip()]
        await state.update_data(**{field: value})
    
    step_index += 1
    if step_index >= len(steps):
        # Finish flow
        data = await state.get_data()
        payload = {f: data[f] for f, _ in LOCATION_ADD_STEPS if f in data}
        if data.get('image_url'): payload['image_url'] = data['image_url']
        
        if mode == 'edit':
            lid = data['edit_loc_id']
            await location_db.update_location(lid, payload)
            loc = await location_db.get_location_by_id(lid)
            await message.answer('✅ Локацію оновлено.')
            if loc: await show_location_card(message, loc)
        else:
            lid = await location_db.add_location(**payload)
            loc = await location_db.get_location_by_id(lid)
            await message.answer('✅ Локацію додано.')
            if loc: await show_location_card(message, loc)
        await state.clear()
        return
    
    await state.update_data(loc_step_index=step_index)
    await _ask_location_step(message, state)

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
    await safe_edit_message(callback.message, f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>\n\nВиберіть розділ керування:', reply_markup=akb.get_admin_main_inline_kb(role), parse_mode='HTML')


# --- ORDERS BLOCK ---

@admin_router.message(F.text == '🆕 НОВІ')
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
        await message.answer('🆕 <b>НОВІ:</b>\nНаразі нових замовлень немає.', parse_mode='HTML')
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

@admin_router.message(F.text == '📦 АКТИВНІ')
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
        await message.answer('📦 <b>АКТИВНІ:</b>\nНаразі активних замовлень немає.', parse_mode='HTML')
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
    beans = _sorted_beans(await coffee_beans_db.get_all_beans(), 'commercial')
    text = "<b>КОМЕРЦІЙНА КАВА</b>\nСпочатку Espresso, потім Filter."
    if not beans:
        text += "\n\nСписок порожній."
    await message.answer(text, reply_markup=_bean_list_kb(beans, 'commercial'), parse_mode='HTML')

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
    await show_beans_page(callback, 'commercial')

@admin_router.callback_query(F.data == 'locations_manage')
async def manage_locations_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, '📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ:</b>', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'contacts_manage')
async def manage_contacts_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, '📞 <b>КЕРУВАННЯ КОНТАКТАМИ:</b>', reply_markup=akb.get_contacts_manage_kb(), parse_mode='HTML')

BEAN_ADD_STEPS = [
    ('name', '📝 <b>Введіть назву кави:</b>'),
    ('photo', '📸 <b>Надішліть фото кави</b> (або - якщо немає):'),
    ('price_250', '💰 <b>Ціна за 250 г</b> (тільки число):'),
    ('roast', '🔥 <b>Обсмаження</b> (Espresso або Filter):'),
    ('quality_score', '📊 <b>Оцінка якості</b> (число для specialty, - для комерційної):'),
    ('species', '🌿 <b>Склад / Вид</b> (напр. Арабіка 100%):'),
    ('descriptors', '🍓 <b>Дескриптори:</b>'),
    ('variety', '🧬 <b>Різновид:</b>'),
    ('altitude', '⛰ <b>Висота:</b>'),
    ('processing', '🧪 <b>Метод обробки:</b>'),
    ('harvest', '📅 <b>Врожай:</b>'),
    ('description', '📖 <b>Опис:</b>')
]

BEAN_EDIT_FIELDS = [field for field, _ in BEAN_ADD_STEPS]

def _bean_score(bean: dict) -> str:
    return str(bean.get('quality_score') or bean.get('cup_score') or '').strip()

def _bean_category(bean: dict) -> str:
    category = str(bean.get('category') or '').strip().lower()
    if category in ('commercial', 'specialty'):
        return category
    score = _bean_score(bean)
    if not score or score == '-':
        return 'commercial'
    try:
        return 'specialty' if float(score.replace(',', '.')) >= 80 else 'commercial'
    except ValueError:
        return 'commercial'

def _roast_rank(bean: dict) -> int:
    roast = str(bean.get('roast') or '').strip().lower()
    if 'espresso' in roast or 'еспрес' in roast:
        return 0
    if 'filter' in roast or 'фільтр' in roast:
        return 1
    return 2

def _sorted_beans(beans: list[dict], category: str) -> list[dict]:
    return sorted(
        [b for b in beans if _bean_category(b) == category],
        key=lambda b: (_roast_rank(b), str(b.get('name') or '').casefold())
    )

def _bean_list_kb(beans: list[dict], category: str) -> InlineKeyboardMarkup:
    other = 'specialty' if category == 'commercial' else 'commercial'
    other_text = 'ПЕРЕЙТИ ДО СПЕШЕЛТІ' if other == 'specialty' else 'ПЕРЕЙТИ ДО КОМЕРЦІЙНОЇ'
    keyboard = []
    
    # Grid: 2 columns
    row = []
    for i, b in enumerate(beans):
        bid = str(b['_id'])
        name = b.get('name', '')[:25]
        row.append(InlineKeyboardButton(text=name, callback_data=f'bean_open_{bid}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text=other_text, callback_data=f'beans_page_{other}')])
    keyboard.append([InlineKeyboardButton(text='➕ ДОДАТИ НОВУ КАВУ', callback_data='bean_new')])
    keyboard.append([InlineKeyboardButton(text='⬅️ НАЗАД В МЕНЮ', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def _bean_card_text(bean: dict) -> str:
    score = _bean_score(bean) or '—'
    category = 'Комерційна' if _bean_category(bean) == 'commercial' else 'Спешелті'
    
    # Auto sorting grade for commercial
    grade_info = ""
    if _bean_category(bean) == 'commercial':
        low_score = score.lower()
        if 'зелен' in low_score or 'green' in low_score: grade_info = " (Зелена)"
        elif 'жовт' in low_score or 'yellow' in low_score: grade_info = " (Жовта)"
        elif 'оранж' in low_score or 'orange' in low_score: grade_info = " (Оранжева)"

    lines = [
        f"<b>{html.escape(str(bean.get('name') or 'Без назви'))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"📊 Категорія: <b>{category}{grade_info}</b>",
        f"💰 Ціна 250г: <b>{bean.get('price_250', 0)} ₴</b>",
        f"🔥 Обсмаження: <b>{html.escape(str(bean.get('roast') or '—'))}</b>",
        f"📈 Оцінка: <b>{html.escape(score)}</b>",
        f"🌿 Склад: <b>{html.escape(str(bean.get('species') or '—'))}</b>",
        f"🍓 Дескриптори: <b>{html.escape(str(bean.get('descriptors') or '—'))}</b>",
        f"🧬 Різновид: <b>{html.escape(str(bean.get('variety') or '—'))}</b>",
        f"⛰ Висота: <b>{html.escape(str(bean.get('altitude') or '—'))}</b>",
        f"🧪 Обробка: <b>{html.escape(str(bean.get('processing') or '—'))}</b>",
        f"📅 Врожай: <b>{html.escape(str(bean.get('harvest') or '—'))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"📖 <b>Опис:</b>",
        f"{html.escape(str(bean.get('description') or '—'))}"
    ]
    return '\n'.join(lines)

async def show_beans_page(callback: CallbackQuery, category: str = 'commercial'):
    beans = _sorted_beans(await coffee_beans_db.get_all_beans(), category)
    title = '<b>КОМЕРЦІЙНА КАВА</b>' if category == 'commercial' else '<b>СПЕШЕЛТІ КАВА</b>'
    text = f"{title}\n<i>Спочатку Espresso, потім Filter.</i>"
    if not beans:
        text += "\n\nСписок порожній."
    await safe_edit_message(callback.message, text, reply_markup=_bean_list_kb(beans, category), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_edit_fields_'))
async def edit_bean_fields_menu(callback: CallbackQuery):
    bid = callback.data.replace('bean_edit_fields_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if not bean:
        await callback.answer('Зерно не знайдено.', show_alert=True)
        return
    category = _bean_category(bean)
    await safe_edit_message(callback.message, f"⚙️ <b>Оберіть поле для редагування:</b>\n{html.escape(str(bean.get('name', '')))}", reply_markup=akb.get_bean_edit_fields_kb(bid, category), parse_mode='HTML')
    await callback.answer()

async def show_bean_card(target, bean: dict):
    category = _bean_category(bean)
    text = _bean_card_text(bean)
    kb = akb.get_bean_card_kb(str(bean['_id']), category)
    
    image = str(bean.get('image_url') or '').strip()
    photo = None
    
    logger.info(f"Showing bean card for {bean.get('name')}. Image URL in DB: {image}")

    if image:
        if image.startswith('/uploads/') or image.startswith('/photos/'):
            # Resolve local path based on site_dir and uploads_dir
            site_dir = Path("/usr/share/nginx/html")
            if not site_dir.exists():
                from app.utils.paths import get_site_dir
                site_dir = get_site_dir()
            
            uploads_dir = get_uploads_dir()
            
            if image.startswith('/uploads/'):
                filename = image.replace('/uploads/', '')
                local_path = uploads_dir / filename
            else: # /photos/
                filename = image.lstrip('/')
                local_path = site_dir / filename
            
            logger.info(f"Checking local photo at: {local_path}")
            
            if local_path.exists():
                photo = FSInputFile(local_path)
            elif WEB_APP_URL:
                # Fallback to web URL if local file not found
                photo = f"{WEB_APP_URL.rstrip('/')}{image}"
                logger.info(f"Photo not found locally, using web URL: {photo}")
            else:
                logger.warning(f"Photo file not found: {filename}")
        elif image.startswith('http'):
            photo = image
        elif len(image) > 10 and '/' not in image: # Likely file_id
            photo = image

    if photo:
        try:
            if isinstance(target, Message):
                await target.answer_photo(photo, caption=text, reply_markup=kb, parse_mode='HTML')
            else: # CallbackQuery
                await target.message.answer_photo(photo, caption=text, reply_markup=kb, parse_mode='HTML')
            return
        except Exception as e:
            logger.warning(f"Failed to send bean photo: {e}")

    # Fallback to text if no photo found or failed to send
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode='HTML')
    else:
        await target.message.answer(text, reply_markup=kb, parse_mode='HTML')

def _cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='bean_add_cancel')]])

def _validate_bean_value(field: str, value: str, data: dict):
    value = (value or '').strip()
    if field == 'price_250':
        if not value.isdigit():
            return None, 'Введіть ціну цілим числом.'
        return int(value), None
    if field == 'quality_score':
        if value == '-':
            return '-', None
        low = value.lower()
        # Quality colors for commercial
        for color in ['зелена', 'жовта', 'оранжева', 'зелен', 'жовт', 'оранж']:
            if color in low:
                return value, None
        try:
            return str(float(value.replace(',', '.'))).rstrip('0').rstrip('.'), None
        except ValueError:
            return None, 'Оцінка якості має бути числом, дефісом або кольором (зелена/жовта/оранжева).'
    if field == 'roast':
        low = value.lower()
        if 'espresso' in low or 'еспрес' in low:
            return 'Espresso', None
        if 'filter' in low or 'фільтр' in low:
            return 'Filter', None
        return None, 'Введіть Espresso або Filter.'
    if not value:
        return None, 'Поле не може бути порожнім.'
    if value == '-':
        return None, 'Дефіс дозволений тільки для оцінки якості.'
    return value, None

async def _ask_bean_step(message: Message, state: FSMContext):
    data = await state.get_data()
    step_index = int(data.get('bean_step_index', 0))
    steps = data.get('bean_steps') or BEAN_ADD_STEPS
    field, prompt = steps[step_index]
    await message.answer(prompt, reply_markup=_cancel_kb(), parse_mode='HTML')

async def _finish_bean_flow(message: Message, state: FSMContext):
    data = await state.get_data()
    payload = {field: data[field] for field in BEAN_EDIT_FIELDS if field in data}
    if data.get('image_url'):
        payload['image_url'] = data['image_url']
    score = str(payload.get('quality_score') or '').strip()
    payload['category'] = 'commercial' if score == '-' else 'specialty'
    if data.get('bean_mode') == 'edit':
        bid = data['edit_bean_id']
        await coffee_beans_db.update_bean(bid, payload)
        bean = await coffee_beans_db.get_bean_by_id(bid)
        await message.answer('✅ Зерно оновлено.')
        if bean:
            await show_bean_card(message, bean)
    else:
        bid = await coffee_beans_db.add_bean(**payload)
        bean = await coffee_beans_db.get_bean_by_id(bid)
        await message.answer('✅ Зерно додано.')
        if bean:
            await show_bean_card(message, bean)
    await state.clear()

@admin_router.callback_query(F.data.in_(['beans_list', 'beans_list_edit', 'beans_list_del', 'beans_page_commercial', 'beans_page_specialty']))
async def list_beans_admin(callback: CallbackQuery):
    category = 'specialty' if callback.data.endswith('specialty') else 'commercial'
    await show_beans_page(callback, category)

@admin_router.callback_query(F.data == 'bean_add')
async def add_bean_start(callback: CallbackQuery):
    await show_beans_page(callback, 'commercial')

@admin_router.callback_query(F.data == 'bean_new')
async def add_bean_new(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(bean_mode='add', bean_step_index=0, bean_steps=BEAN_ADD_STEPS)
    await callback.message.answer('➕ <b>ДОДАВАННЯ КАВИ</b>', parse_mode='HTML')
    await _ask_bean_step(callback.message, state)
    await state.set_state(AdminStates.adding_bean_name)
    await callback.answer()

@admin_router.callback_query(F.data == 'bean_add_cancel')
async def add_bean_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_message(callback.message, '❌ Дію скасовано.', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_open_'))
async def open_bean_card(callback: CallbackQuery):
    bid = callback.data.replace('bean_open_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if not bean:
        await callback.answer('Зерно не знайдено.', show_alert=True)
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await show_bean_card(callback.message, bean)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_del_confirm_'))
async def delete_bean_confirm(callback: CallbackQuery):
    bid = callback.data.replace('bean_del_confirm_', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🗑 ТАК, ВИДАЛИТИ', callback_data=f'bean_del_final_{bid}')],
        [InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data=f'bean_open_{bid}')]
    ])
    await safe_edit_message(callback.message, "Видалити це зерно?", reply_markup=kb)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_del_final_'))
async def delete_bean_final(callback: CallbackQuery):
    bid = callback.data.replace('bean_del_final_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    category = _bean_category(bean or {})
    await coffee_beans_db.delete_bean(bid)
    await callback.answer('Зерно видалено.')
    await show_beans_page(callback, category)

@admin_router.callback_query(F.data.startswith('bean_full_edit_'))
async def edit_bean_full_start(callback: CallbackQuery, state: FSMContext):
    bid = callback.data.replace('bean_full_edit_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if not bean:
        await callback.answer('Зерно не знайдено.', show_alert=True)
        return
    await state.clear()
    steps = [(field, f"{prompt}\nПоточне значення: {bean.get('price_250') if field == 'price_250' else bean.get('image_url') if field == 'photo' else bean.get(field, '')}") for field, prompt in BEAN_ADD_STEPS]
    await state.update_data(bean_mode='edit', edit_bean_id=bid, bean_step_index=0, bean_steps=steps)
    await callback.message.answer(f"✏️ <b>РЕДАГУВАННЯ: {html.escape(str(bean.get('name') or ''))}</b>", parse_mode='HTML')
    await _ask_bean_step(callback.message, state)
    await state.set_state(AdminStates.editing_bean_field)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_fedit_'))
async def edit_bean_single_field_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    bid = parts[2]
    raw_field = '_'.join(parts[3:]) # Support fields with underscores
    field_map = {'price': 'price_250', 'score': 'quality_score', 'photo': 'photo'}
    field = field_map.get(raw_field, raw_field)
    prompts = dict(BEAN_ADD_STEPS)
    if field == 'category':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Комерційна', callback_data=f'bean_set_category_{bid}_commercial')],
            [InlineKeyboardButton(text='Спешелті', callback_data=f'bean_set_category_{bid}_specialty')]
        ])
        await callback.message.answer('Оберіть категорію:', reply_markup=kb)
        await callback.answer()
        return
    await state.clear()
    await state.update_data(bean_mode='single_edit', edit_bean_id=bid, edit_single_field=field)
    await callback.message.answer(prompts.get(field, 'Нове значення:'), reply_markup=_cancel_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.editing_bean_field)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_set_category_'))
async def set_bean_category(callback: CallbackQuery):
    payload = callback.data.replace('bean_set_category_', '')
    bid, category = payload.rsplit('_', 1)
    update = {'category': category}
    if category == 'commercial':
        update['quality_score'] = '-'
    await coffee_beans_db.update_bean(bid, update)
    bean = await coffee_beans_db.get_bean_by_id(bid)
    await callback.answer('Категорію оновлено.')
    if bean:
        await show_bean_card(callback.message, bean)

@admin_router.message(AdminStates.adding_bean_name)
@admin_router.message(AdminStates.editing_bean_field)
async def bean_flow_input(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    mode = data.get('bean_mode')
    if mode == 'single_edit':
        field = data.get('edit_single_field')
        if field == 'photo':
            value = await process_photo(message, bot)
            if not value:
                await message.answer('Не вдалося отримати фото. Надішліть фото з галереї або посилання.')
                return
        else:
            value, error = _validate_bean_value(field, message.text or '', data)
            if error:
                await message.answer(error)
                return
        update_field = 'image_url' if field == 'photo' else field
        update = {update_field: value}
        if update_field == 'quality_score':
            update['category'] = 'commercial' if value == '-' else 'specialty'
        await coffee_beans_db.update_bean(data['edit_bean_id'], update)
        bean = await coffee_beans_db.get_bean_by_id(data['edit_bean_id'])
        await message.answer('✅ Поле оновлено.')
        await state.clear()
        if bean:
            await show_bean_card(message, bean)
        return

    steps = data.get('bean_steps') or BEAN_ADD_STEPS
    step_index = int(data.get('bean_step_index', 0))
    field, _ = steps[step_index]
    if field == 'photo':
        value = await process_photo(message, bot)
        # value is "" if process_photo failed OR if user sent "-"
        if not value and (message.text or '').strip() != '-':
            await message.answer('Не вдалося отримати фото. Надішліть фото з галереї або посилання (або - для пропуску).')
            return
        await state.update_data(image_url=value)
    else:
        value, error = _validate_bean_value(field, message.text or '', data)
        if error:
            await message.answer(error)
            return
        await state.update_data(**{field: value})
    step_index += 1
    if step_index >= len(steps):
        await _finish_bean_flow(message, state)
        return
    await state.update_data(bean_step_index=step_index)
    await _ask_bean_step(message, state)


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
