from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from app.utils.paths import get_uploads_dir

from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter, Command

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
import re
import aiohttp

import time

logger = logging.getLogger(__name__)

admin_router = Router()

@admin_router.message(StateFilter('*'), F.text.in_(['☕️ КАВА В ЗЕРНАХ', '📍 НАШІ ЗАКЛАДИ', '📞 КОНТАКТИ', '🔐 АДМІН-ПАНЕЛЬ', '🏠 НА ГОЛОВНУ', '❌ СКАСУВАТИ']))
async def admin_global_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        
    is_admin = await admin_db.is_admin(message.from_user.id)
    
    if message.text == '🔐 АДМІН-ПАНЕЛЬ':
        if is_admin: return await show_admin_panel(message)
        else: return await message.answer("🔒 У вас немає доступу до адмін-панелі.")
        
    if message.text == '📞 КОНТАКТИ':
        if is_admin: return await manage_contacts_msg(message)
        # Regular users should fall through to user_handlers, but we need to trigger it
        from app.handlers.user_handlers import show_contacts
        return await show_contacts(message)
        
    if message.text == '🏠 НА ГОЛОВНУ':
        from app.handlers.user_handlers import cmd_start_msg
        return await cmd_start_msg(message, is_admin)

    if message.text == '📍 НАШІ ЗАКЛАДИ':
        from app.handlers.user_handlers import show_locations
        return await show_locations(message)

    if message.text == '☕️ КАВА В ЗЕРНАХ':
        from app.handlers.user_handlers import show_coffee_menu
        return await show_coffee_menu(message)
        
    if current_state is not None:
        await message.answer("❌ Дію скасовано.")

class AdminStates(StatesGroup):
    # Staff management
    adding_staff_identifier = State()
    adding_staff_name = State()
    confirming_staff = State()
    
    # Other states
    adding_admin_id = State()
    adding_admin_role = State()
    choosing_admin_locations = State()
    
    # Bean management states
    adding_bean_name = State()
    editing_bean_field = State()
    restocking_bean = State()
    
    # Location management states
    adding_location_name = State()
    editing_location_field = State()

    # Contact management states
    adding_contact_name = State()
    editing_contact_field = State()

    # Broadcasting
    broadcasting = State()

CONTACT_ADD_STEPS = [
    ('name', '🏷 <b>Введіть назву контакту:</b>'),
    ('url', '🔗 <b>Введіть URL або дані:</b>')
]

@admin_router.message(Command('broadcast'))
async def cmd_broadcast(message: Message, state: FSMContext):
    is_admin = await admin_db.is_admin(message.from_user.id)
    if not is_admin: return
    await message.answer("📝 <b>РОЗСИЛКА</b>\n\nВведіть текст повідомлення, яке отримають УСІ користувачі бота (або ❌ СКАСУВАТИ):", parse_mode='HTML')
    await state.set_state(AdminStates.broadcasting)

@admin_router.message(AdminStates.broadcasting)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.text == '❌ СКАСУВАТИ':
        await state.clear()
        return await message.answer("❌ Розсилку скасовано.")
        
    uids = await user_db.get_all_user_ids()
    await message.answer(f"🚀 Починаю розсилку на {len(uids)} користувачів...")
    
    count = 0
    for uid in uids:
        try:
            await bot.send_message(uid, message.text)
            count += 1
            await asyncio.sleep(0.05) # Rate limiting
        except:
            pass
            
    await message.answer(f"✅ Розсилка завершена! Отримали: {count}/{len(uids)}")
    await state.clear()

@admin_router.message(Command('stats'))
async def cmd_stats(message: Message):
    role = await get_user_role(message.from_user.id)
    if role != 'developer': return

    from app.databases.sales_database import sales_db
    sales = await sales_db.get_all_sales()

    total_sales = len([s for s in sales if s.get('record_type') == 'sale'])
    total_revenue = sum(s.get('total', 0) or (s.get('price', 0) * s.get('quantity', 1)) for s in sales if s.get('record_type') == 'sale')

    text = (
        f"📊 <b>СТАТИСТИКА ПРОДАЖІВ</b>\n\n"
        f"💰 Загальна виручка: <b>{int(total_revenue)} грн</b>\n"
        f"📦 Всього продажів: <b>{total_sales}</b>"
    )
    await message.answer(text, parse_mode='HTML')

def _guess_contact_emoji(name: str, url: str) -> str:
    n = name.lower()
    u = url.lower()
    
    # 0. Phone (Check first to avoid 'теле' conflict)
    clean_u = re.sub(r'[\s\-()]+', '', u)
    is_phone_name = any(k in n for k in ['телефон', 'phone', 'номер'])
    is_phone_url = u.startswith('tel:') or clean_u.startswith('+') or (clean_u.isdigit() and len(clean_u) >= 9)
    if is_phone_name or is_phone_url:
        return '📞'

    # 1. Instagram
    if any(k in n for k in ['insta', 'інста']) or 'instagram' in u: return '📸'
    # 2. Facebook
    if any(k in n for k in ['face', 'фейс', 'фб']) or 'facebook' in u or 'fb.' in u: return '👥'
    # 3. Telegram
    if any(k in n for k in ['telegram', 'тг']) or 't.me' in u: return '✈️'
    # 4. Viber
    if any(k in n for k in ['viber', 'вайбер']) or 'viber' in u: return '💜'
    # 5. YouTube
    if any(k in n for k in ['tube', 'ютуб']) or 'youtu' in u: return '📺'
    # 6. TikTok
    if any(k in n for k in ['tik', 'тік']) or 'tiktok' in u: return '🎵'
    # 7. Email
    if any(k in n for k in ['mail', 'мейл', 'пошт']) or '@' in u or 'mailto:' in u: return '📧'
    
    return '🔗'

def _contact_list_kb(contacts: list[dict], role='owner') -> InlineKeyboardMarkup:
    keyboard = []
    # Grid: 2 columns
    row = []
    for c in contacts:
        cid = str(c['_id'])
        name = c.get('name', 'Без назви')
        url = c.get('url', '')
        emoji = _guess_contact_emoji(name, url)
        btn_text = f"{emoji} {name}"[:25]
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f'con_open_{cid}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    if role != 'developer':
        keyboard.append([InlineKeyboardButton(text='➕ ДОДАТИ КОНТАКТ', callback_data='contact_new')])
    keyboard.append([InlineKeyboardButton(text='⬅️ НАЗАД В МЕНЮ', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def _contact_card_text(con: dict) -> str:
    name = con.get('name', 'Без назви')
    url = con.get('url', '—')
    emoji = _guess_contact_emoji(name, url)
    
    lines = [
        f"📞 <b>КОНТАКТ: {html.escape(str(name))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"Тип: <b>{emoji} {html.escape(str(name))}</b>",
        f"Дані: <code>{html.escape(str(url))}</code>",
        f"━━━━━━━━━━━━━━━",
        f"<i>Цей контакт буде відображатися на сайті та в боті для клієнтів.</i>"
    ]
    return '\n'.join(lines)

async def show_contacts_page(callback: CallbackQuery, role='owner'):
    contacts = await contacts_db.get_all_contacts()
    text = "📞 <b>КЕРУВАННЯ КОНТАКТАМИ:</b>"
    if not contacts:
        text += "\n\nСписок порожній."
    await safe_edit_message(callback.message, text, reply_markup=_contact_list_kb(contacts, role=role), parse_mode='HTML')
    await callback.answer()

async def show_contact_card(target, con: dict, role='owner'):
    text = _contact_card_text(con)
    kb = akb.get_contact_card_kb(str(con['_id']), role=role)
    
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode='HTML', disable_web_page_preview=True)
    else:
        await target.message.answer(text, reply_markup=kb, parse_mode='HTML', disable_web_page_preview=True)

# Contact Handlers

@admin_router.callback_query(F.data == 'contacts_list')
async def list_contacts_cb(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await show_contacts_page(callback, role=role)

@admin_router.callback_query(F.data == 'contact_new')
async def add_contact_new(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    await state.clear()
    await state.update_data(con_mode='add', con_step_index=0)
    await callback.message.answer('➕ <b>ДОДАВАННЯ КОНТАКТУ</b>', parse_mode='HTML')
    await _ask_contact_step(callback.message, state)
    await state.set_state(AdminStates.adding_contact_name)
    await callback.answer()

async def _ask_contact_step(message: Message, state: FSMContext):
    data = await state.get_data()
    step_index = int(data.get('con_step_index', 0))
    _, prompt = CONTACT_ADD_STEPS[step_index]
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='contact_cancel')]])
    await message.answer(prompt, reply_markup=cancel_kb, parse_mode='HTML')

@admin_router.callback_query(F.data == 'contact_cancel')
async def contact_cancel(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    await state.clear()
    await show_contacts_page(callback, role=role)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('con_open_'))
async def open_contact_card(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    cid = callback.data.replace('con_open_', '')
    con = await contacts_db.get_contact_by_id(cid)
    if not con:
        await callback.answer('Контакт не знайдено.', show_alert=True)
        return
    try:
        await callback.message.delete()
    except:
        pass
    await show_contact_card(callback.message, con, role=role)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('con_del_confirm_'))
async def delete_contact_confirm(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    cid = callback.data.replace('con_del_confirm_', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🗑 ТАК, ВИДАЛИТИ', callback_data=f'con_del_final_{cid}')],
        [InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data=f'con_open_{cid}')]
    ])
    await safe_edit_message(callback.message, "Видалити цей контакт?", reply_markup=kb)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('con_del_final_'))
async def delete_contact_final(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer': return
    cid = callback.data.replace('con_del_final_', '')
    await contacts_db.delete_contact(cid)
    await callback.answer('Контакт видалено.')
    await show_contacts_page(callback, role=role)

@admin_router.callback_query(F.data.startswith('con_edit_fields_'))
async def edit_contact_fields_menu(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    cid = callback.data.replace('con_edit_fields_', '')
    con = await contacts_db.get_contact_by_id(cid)
    if not con:
        await callback.answer('Контакт не знайдено.', show_alert=True)
        return
    await safe_edit_message(callback.message, f"⚙️ <b>Оберіть поле для редагування:</b>\n{html.escape(str(con.get('name', '')))}", reply_markup=akb.get_contact_edit_fields_kb(cid), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('con_fedit_'))
async def edit_contact_single_field_start(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer': return
    parts = callback.data.split('_')
    cid = parts[2]
    field = parts[3]
    
    prompts = dict(CONTACT_ADD_STEPS)
    await state.clear()
    await state.update_data(con_mode='single_edit', edit_con_id=cid, edit_single_field=field)
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='contact_cancel')]])
    await callback.message.answer(prompts.get(field, 'Нове значення:'), reply_markup=cancel_kb, parse_mode='HTML')
    await state.set_state(AdminStates.editing_contact_field)
    await callback.answer()

@admin_router.message(AdminStates.adding_contact_name)
@admin_router.message(AdminStates.editing_contact_field)
async def contact_flow_input(message: Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role == 'developer': return
    data = await state.get_data()
    mode = data.get('con_mode')
    
    if mode == 'single_edit':
        field = data.get('edit_single_field')
        value = (message.text or '').strip()
        if not value: return
        
        await contacts_db.update_contact(data['edit_con_id'], {field: value})
        con = await contacts_db.get_contact_by_id(data['edit_con_id'])
        await message.answer('✅ Контакт оновлено.')
        await state.clear()
        if con: await show_contact_card(message, con, role=role)
        return

    step_index = int(data.get('con_step_index', 0))
    field, _ = CONTACT_ADD_STEPS[step_index]
    
    value = (message.text or '').strip()
    if not value: return
    await state.update_data(**{field: value})
    
    step_index += 1
    if step_index >= len(CONTACT_ADD_STEPS):
        # Finish flow
        data = await state.get_data()
        payload = {f: data[f] for f, _ in CONTACT_ADD_STEPS if f in data}
        
        await contacts_db.add_contact(**payload)
        await message.answer('✅ Контакт додано/оновлено.')
        await state.clear()
        # Triggering list instead of card because add_contact uses name as key and might not return ID easily here
        contacts = await contacts_db.get_all_contacts()
        await message.answer("📞 <b>КЕРУВАННЯ КОНТАКТАМИ:</b>", reply_markup=_contact_list_kb(contacts, role=role), parse_mode='HTML')
        return
    
    await state.update_data(con_step_index=step_index)
    await _ask_contact_step(message, state)

LOCATION_ADD_STEPS = [
    ('name', '📝 <b>Введіть назву локації:</b>'),
    ('address', '🏠 <b>Введіть адресу:</b>'),
    ('schedule', '📅 <b>Введіть графік роботи</b> (напр. Пн-Нд 08:00-20:00):'),
    ('google_maps_url', '🗺 <b>Введіть посилання на Google Maps:</b>'),
    ('photo', '📸 <b>Надішліть фото локації</b> (або - якщо немає):'),
    ('amenities', '✨ <b>Зручності</b> (через кому):'),
    ('atmosphere', '☁️ <b>Опис атмосфери:</b>')
]

LOCATION_EDIT_FIELDS = [field for field, _ in LOCATION_ADD_STEPS]

def _location_list_kb(locations: list[dict], role='owner') -> InlineKeyboardMarkup:
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
    
    if role != 'developer':
        keyboard.append([InlineKeyboardButton(text='➕ ДОДАТИ НОВУ ЛОКАЦІЮ', callback_data='location_new')])
    keyboard.append([InlineKeyboardButton(text='⬅️ НАЗАД В МЕНЮ', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def _location_card_text(loc: dict) -> str:
    lines = [
        f"📍 <b>{html.escape(str(loc.get('name') or 'Без назви'))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"🏠 Адреса: <b>{html.escape(str(loc.get('address') or '—'))}</b>",
        f"📅 Графік: <b>{html.escape(str(loc.get('schedule') or '—'))}</b>",
        f"🗺 Google Maps: <a href=\"{loc.get('google_maps_url', '#')}\">Відкрити</a>",
        f"✨ Зручності: <b>{html.escape(', '.join(loc.get('amenities', [])) if isinstance(loc.get('amenities'), list) else str(loc.get('amenities', '—')))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"☁️ <b>Атмосфера:</b>",
        f"{html.escape(str(loc.get('atmosphere') or '—'))}"
    ]
    return '\n'.join(lines)

async def show_locations_page(callback: CallbackQuery, role='owner'):
    locations = await location_db.get_all_locations()
    text = "📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ:</b>"
    if not locations:
        text += "\n\nСписок порожній."
    await safe_edit_message(callback.message, text, reply_markup=_location_list_kb(locations, role=role), parse_mode='HTML')
    await callback.answer()

async def show_location_card(target, loc: dict, role='owner'):
    text = _location_card_text(loc)
    kb = akb.get_location_card_kb(str(loc['_id']), role=role)
    
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
    role = await get_user_role(callback.from_user.id)
    await show_locations_page(callback, role=role)

@admin_router.callback_query(F.data == 'location_new')
async def add_location_new(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
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
    role = await get_user_role(callback.from_user.id)
    await state.clear()
    await show_locations_page(callback, role=role)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_open_'))
async def open_location_card(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    lid = callback.data.replace('loc_open_', '')
    loc = await location_db.get_location_by_id(lid)
    if not loc:
        await callback.answer('Локацію не знайдено.', show_alert=True)
        return
    try:
        await callback.message.delete()
    except:
        pass
    await show_location_card(callback.message, loc, role=role)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_del_confirm_'))
async def delete_location_confirm(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    lid = callback.data.replace('loc_del_confirm_', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🗑 ТАК, ВИДАЛИТИ', callback_data=f'loc_del_final_{lid}')],
        [InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data=f'loc_open_{lid}')]
    ])
    await safe_edit_message(callback.message, "Видалити цю локацію?", reply_markup=kb)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_del_final_'))
async def delete_location_final(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer': return
    lid = callback.data.replace('loc_del_final_', '')
    await location_db.delete_location(lid)
    await callback.answer('Локацію видалено.')
    await show_locations_page(callback, role=role)

@admin_router.callback_query(F.data.startswith('loc_edit_fields_'))
async def edit_location_fields_menu(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    lid = callback.data.replace('loc_edit_fields_', '')
    loc = await location_db.get_location_by_id(lid)
    if not loc:
        await callback.answer('Локацію не знайдено.', show_alert=True)
        return
    await safe_edit_message(callback.message, f"⚙️ <b>Оберіть поле для редагування:</b>\n{html.escape(str(loc.get('name', '')))}", reply_markup=akb.get_location_edit_fields_kb(lid), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('loc_fedit_'))
async def edit_location_single_field_start(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer': return
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
    role = await get_user_role(message.from_user.id)
    if role == 'developer': return
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
        update = {update_field: value}
        
        # Auto-extract coordinates if editing google_maps_url
        if field == 'google_maps_url':
            coords = await get_coordinates_from_url(value)
            if coords:
                update['coordinates'] = coords
        
        await location_db.update_location(data['edit_loc_id'], update)
        loc = await location_db.get_location_by_id(data['edit_loc_id'])
        await message.answer('✅ Поле оновлено.')
        await state.clear()
        if loc: await show_location_card(message, loc, role=role)
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
        
        # Auto-extract coordinates if we just got a Google Maps URL
        if field == 'google_maps_url':
            coords = await get_coordinates_from_url(value)
            if coords:
                await state.update_data(coordinates=coords)
                logger.info(f"Auto-extracted coordinates: {coords}")
    
    step_index += 1
    if step_index >= len(steps):
        # Finish flow
        data = await state.get_data()
        payload = {f: data[f] for f, _ in LOCATION_ADD_STEPS if f in data}
        if data.get('image_url'): payload['image_url'] = data['image_url']
        if data.get('coordinates'): payload['coordinates'] = data['coordinates']
        
        if mode == 'edit':
            lid = data['edit_loc_id']
            await location_db.update_location(lid, payload)
            loc = await location_db.get_location_by_id(lid)
            await message.answer('✅ Локацію оновлено.')
            if loc: await show_location_card(message, loc, role=role)
        else:
            lid = await location_db.add_location(**payload)
            loc = await location_db.get_location_by_id(lid)
            await message.answer('✅ Локацію додано.')
            if loc: await show_location_card(message, loc, role=role)
        await state.clear()
        return
    
    await state.update_data(loc_step_index=step_index)
    await _ask_location_step(message, state)

async def get_coordinates_from_url(url: str) -> dict | None:
    """
    Extract latitude and longitude from Google Maps URL.
    Supports full, shortened, and view-center URLs.
    """
    if not url:
        return None
    
    # Add protocol if missing
    if not url.startswith('http'):
        if 'google.com' in url or 'goo.gl' in url:
            url = 'https://' + url
        else:
            return None
    
    try:
        current_url = url
        # Follow redirects for shortened links (maps.app.goo.gl, goo.gl)
        if 'goo.gl' in url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, allow_redirects=True, timeout=10) as resp:
                    current_url = str(resp.url)
                    logger.info(f"Resolved shortened URL to: {current_url}")
        
        # 1. Try marker data pattern (e.g. ...!3d48.6118969!4d22.2956774...)
        # This is usually the exact location of the place
        match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', current_url)
        if match:
            coords = {'lat': float(match.group(1)), 'lon': float(match.group(2))}
            logger.info(f"Extracted coords from marker data: {coords}")
            return coords

        # 2. Try @lat,lon format (e.g. .../@48.6188374,22.2568452,14z/...)
        # This is the view center
        match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
        if match:
            coords = {'lat': float(match.group(1)), 'lon': float(match.group(2))}
            logger.info(f"Extracted coords from @ view center: {coords}")
            return coords
        
        # 3. Try q=lat,lon or ll=lat,lon format
        match = re.search(r'[?&](?:q|ll)=(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
        if match:
            coords = {'lat': float(match.group(1)), 'lon': float(match.group(2))}
            logger.info(f"Extracted coords from query pattern: {coords}")
            return coords
            
    except Exception as e:
        logger.error(f"Error extracting coordinates from {url}: {e}")
        
    return None

async def get_user_role(user_id: int) -> str:
    if str(user_id) in DEVELOPER_IDS: return 'developer'
    db = await get_db()
    admin = await db.admins.find_one({'user_id': int(user_id)})
    return admin.get('role', 'user') if admin else 'user'

def get_role_label(role: str) -> str:
    return {
        'developer': 'developer',
        'owner': 'власник',
        'admin': 'адмін'
    }.get(role, role)

@admin_router.message(F.text == '🔐 АДМІН-ПАНЕЛЬ', StateFilter(None))
async def show_admin_panel(message: Message):
    role = await get_user_role(message.from_user.id)
    if role == 'user': return
    label = get_role_label(role)
    await message.answer(f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{label}</b>\n\nВиберіть розділ керування:', reply_markup=akb.get_admin_main_kb(role), parse_mode='HTML')

@admin_router.callback_query(F.data == 'admin_panel_back')
async def back_to_admin_main(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    label = get_role_label(role)
    await safe_edit_message(callback.message, f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{label}</b>\n\nВиберіть розділ керування:', reply_markup=akb.get_admin_main_inline_kb(role), parse_mode='HTML')


# --- ORDERS BLOCK ---

@admin_router.message(F.text == '🆕 НОВІ', StateFilter(None))
async def list_new_orders_msg(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    await show_new_orders(message)

@admin_router.callback_query(F.data == 'new_orders')
async def list_new_orders_cb(callback: CallbackQuery):
    await show_new_orders(callback.message)
    await callback.answer()

async def show_new_orders(message: Message):
    orders = await orders_db.get_new_orders()
    role = await get_user_role(message.from_user.id)
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
        
        kb = akb.get_booking_manage_kb(oid, o.get('user_id') or -1, role=role)
        await message.answer(msg, reply_markup=kb, parse_mode='HTML')

@admin_router.message(F.text == '📦 АКТИВНІ', StateFilter(None))
async def list_active_orders_msg(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    await show_active_orders(message)

@admin_router.callback_query(F.data == 'active_orders')
async def list_active_orders_cb(callback: CallbackQuery):
    await show_active_orders(callback.message)
    await callback.answer()

async def show_active_orders(message: Message):
    orders = await active_orders_db.get_all_active_orders()
    role = await get_user_role(message.from_user.id)
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
        
        kb_finish = akb.get_active_finish_kb(oid, role=role)
        await message.answer(msg, reply_markup=kb_finish, parse_mode='HTML')

@admin_router.message(F.text.startswith('/view_order_'))
async def view_order_details(message: Message, bot: Bot):
    if not await admin_db.is_admin(message.from_user.id): return
    oid = message.text.replace('/view_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await message.answer("Замовлення не знайдено.")
        return
    
    role = await get_user_role(message.from_user.id)
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
    
    kb = akb.get_booking_manage_kb(oid, order.get('user_id') or -1, role=role)
    await message.answer(msg, reply_markup=kb, parse_mode='HTML')

async def _deduct_stock_from_cart(cart_text: str, bot: Bot):
    """Parses cart text and deducts stock for specialty beans. Handles multiples (xN)."""
    if not cart_text: return
    
    # Split by newlines
    lines = cart_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        bean_name = ""
        count = 1
        
        # 1. Bot format: "ЗЕРНА: Name" or "ЗЕРНА: Name x2"
        if 'ЗЕРНА: ' in line:
            raw = line.split('ЗЕРНА: ', 1)[1].strip()
            # Regex to match "Name x2 (price)" or just "Name x2"
            match = re.search(r'^(.*?)(?:\s+x(\d+))?(?:\s+\(.*\))?$', raw, re.IGNORECASE)
            if match:
                bean_name = match.group(1).strip()
                if match.group(2):
                    count = int(match.group(2))
            else:
                bean_name = raw.split('(')[0].strip()
        
        # 2. Site format: "- Name (price грн)" or "- Name x2 (price грн)"
        elif line.startswith('- '):
            # Regex to match "- Name x2 (100 грн)" or "- Name (100 грн)"
            match = re.search(r'^[-•]\s*(.*?)(?:\s+x(\d+))?\s*\((\d+)\s*(?:грн|₴|uah)?\)', line, re.IGNORECASE)
            if match:
                bean_name = match.group(1).strip()
                if match.group(2):
                    count = int(match.group(2))
            else:
                # Fallback: remove "- " and anything after "("
                bean_name = line[2:].strip().split('(')[0].strip()
        
        if bean_name:
            # IMPORTANT: Reload bean from DB to avoid stale stock_packs values if the same bean appears on multiple lines
            db = await get_db()
            bean = await db.coffee_beans.find_one({'name': bean_name})
            
            if bean:
                if _bean_category(bean) == 'specialty':
                    current = bean.get('stock_packs', 0)
                    if current > 0:
                        new_stock = max(0, current - count)
                        await coffee_beans_db.update_bean(str(bean['_id']), {'stock_packs': new_stock})
                        logger.info(f"Deducted {count} stock for {bean_name} ({current} -> {new_stock})")
                        
                        if new_stock == 0:
                            from app.utils.admin_notifications import send_admin_notification
                            
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text='📦 ПОПОВНИТИ ЗАПАС', callback_data=f'bean_restock_{bean["_id"]}')],
                                [InlineKeyboardButton(text='🗑 ВИДАЛИТИ ЛОТ', callback_data=f'bean_del_confirm_{bean["_id"]}')],
                                [InlineKeyboardButton(text='⬅️ В МЕНЮ', callback_data='beans_manage')]
                            ])
                            
                            text = f"⚠️ <b>ЗАПАС ВИЧЕРПАНО!</b>\n\nКава <b>{html.escape(bean_name)}</b> закінчилася і більше не відображається на сайті.\n\nБажаєте поповнити запас чи видалити лот?"
                            await send_admin_notification(text, reply_markup=kb, notification_type='stock_alert')

# --- STAFF MANAGEMENT ---

@admin_router.callback_query(F.data == 'staff_manage')
async def staff_manage_cb(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await callback.message.answer('👤 <b>КЕРУВАННЯ ПЕРСОНАЛОМ:</b>\nДодавання адміністраторів та менеджерів.', reply_markup=akb.get_staff_manage_kb(role=role), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data == 'staff_add')
async def staff_add_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "👤 <b>ДОДАВАННЯ СПІВРОБІТНИКА</b>\n\n"
        "1. Введіть Telegram ID, @username або номер телефону співробітника:\n\n"
        "<i>Співробітник має спочатку натиснути /start у боті.</i>\n"
        "<i>Telegram ID можно дізнатися в @userinfobot або подібних.</i>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='staff_manage')]])
    )
    await state.set_state(AdminStates.adding_staff_identifier)
    await callback.answer()

@admin_router.message(AdminStates.adding_staff_identifier)
async def staff_identifier_input(message: Message, state: FSMContext):
    identifier = (message.text or '').strip()
    if not identifier: return
    
    target = await admin_db.find_admin_by_identifier(identifier)
    if not target:
        # Check in user_db directly if not found in find_admin_by_identifier
        from app.databases.user_database import user_db
        clean_id = identifier.replace('@', '')
        user_info = None
        if identifier.isdigit():
            user_info = await user_db.get_user_by_id(int(identifier))
        if not user_info:
            user_info = await user_db.get_user_by_username(clean_id)
        if not user_info:
            from app.utils.phone_utils import normalize_phone
            norm = normalize_phone(identifier)
            if norm: user_info = await user_db.get_user_by_phone(norm)
            
        if user_info:
            uid, name, uname, uphone = user_info
            target = {'user_id': uid, 'display_name': name or uname or 'Користувач', 'username': uname}

    if not target:
        await message.answer("❌ <b>КОРИСТУВАЧА НЕ ЗНАЙДЕНО</b>\n\nВпевніться, що він натиснув /start у боті та ви ввели вірні дані.", parse_mode='HTML')
        return

    await state.update_data(target_uid=target['user_id'], target_uname=target.get('username'))
    await message.answer(
        f"✅ <b>ЗНАЙДЕНО:</b> {target.get('display_name')} (@{target.get('username') or '—'})\n\n"
        "2. Введіть ім'я для команди (як його будуть бачити інші):",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.adding_staff_name)

@admin_router.message(AdminStates.adding_staff_name)
async def staff_name_input(message: Message, state: FSMContext):
    display_name = (message.text or '').strip()
    if not display_name: return
    
    data = await state.get_data()
    role = await get_user_role(message.from_user.id)
    
    # Role auto-assignment logic:
    # Developer adds -> Owner
    # Owner adds -> Admin
    target_role = 'admin'
    if role == 'developer':
        target_role = 'owner'
    elif role == 'owner':
        target_role = 'admin'
    else:
        await message.answer("❌ У вас немає прав для додавання персоналу.")
        await state.clear()
        return

    await state.update_data(display_name=display_name, target_role=target_role)
    
    role_label = "власник" if target_role == 'owner' else "адмін"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ ТАК, ДОДАТИ', callback_data='staff_confirm_yes')],
        [InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='staff_manage')]
    ])
    
    await message.answer(
        f"👤 <b>ПЕРЕВІРКА ДАНИХ:</b>\n\n"
        f"Користувач: {data.get('target_uname') or data.get('target_uid')}\n"
        f"Ім'я в команді: <b>{display_name}</b>\n"
        f"Роль: <b>{role_label}</b>\n\n"
        f"Додати цього співробітника?",
        parse_mode='HTML',
        reply_markup=kb
    )
    await state.set_state(AdminStates.confirming_staff)

@admin_router.callback_query(AdminStates.confirming_staff, F.data == 'staff_confirm_yes')
async def staff_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = data['target_uid']
    uname = data['target_uname'] or ''
    dname = data['display_name']
    role = data['target_role']
    
    await admin_db.add_admin(uid, uname, dname, callback.from_user.id, role)
    label = get_role_label(role)
    await callback.message.answer(f"✅ Співробітника <b>{dname}</b> додано як <b>{label}</b>.", parse_mode='HTML', reply_markup=akb.get_staff_manage_kb())
    await state.clear()
    await callback.answer()

@admin_router.callback_query(F.data == 'staff_list')
async def staff_list_cb(callback: CallbackQuery):
    admins = await admin_db.get_admins_basic()
    if not admins:
        await callback.message.answer("Список порожній.")
        await callback.answer()
        return
    
    text = "👤 <b>СПИСОК ПЕРСОНАЛУ:</b>\n\n"
    keyboard = []
    
    for uid, uname, dname, role in admins:
        role_label = get_role_label(role)
        
        text += f"• <b>{dname}</b> (@{uname or '—'}) — {role_label}\n"
        keyboard.append([InlineKeyboardButton(text=f"🗑 Видалити {dname}", callback_data=f"staff_del_{uid}")])
    
    keyboard.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='staff_manage')])
    await safe_edit_message(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('staff_del_'))
async def staff_del_confirm(callback: CallbackQuery):
    uid = int(callback.data.replace('staff_del_', ''))
    me_id = callback.from_user.id
    me_role = await get_user_role(me_id)
    
    target = await admin_db.get_admin_by_id(uid)
    if not target:
        await callback.answer("Співробітника не знайдено.")
        return
    
    t_role = target.get('role')
    t_name = target.get('display_name')
    label = get_role_label(t_role)

    # Deletion rules:
    # 1. Developer cannot delete anyone.
    # 2. Owner can delete anyone (Owners, Admins).
    # 3. Owner can delete themselves.
    
    if me_role == 'developer':
        await callback.answer("🛠 Розробник не може видаляти персонал.", show_alert=True)
        return
    
    if me_role != 'owner':
        await callback.answer("❌ Тільки Власник може видаляти персонал.", show_alert=True)
        return
    
    # If we are here, me_role is 'owner'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🗑 ТАК, ВИДАЛИТИ', callback_data=f'staff_finaldel_{uid}')],
        [InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data='staff_list')]
    ])
    
    await safe_edit_message(callback.message, f"Ви впевнені, що хочете видалити співробітника <b>{t_name}</b> ({label})?", reply_markup=kb, parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('staff_finaldel_'))
async def staff_finaldel(callback: CallbackQuery):
    uid = int(callback.data.replace('staff_finaldel_', ''))
    await admin_db.remove_admin(uid)
    await callback.answer("Видалено.")
    await staff_list_cb(callback)

# --- ORDERS BLOCK ACCESS CONTROL ---

@admin_router.callback_query(F.data.startswith('confirm_order_'))
async def confirm_order_handler(callback: CallbackQuery, bot: Bot):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    
    oid = callback.data.replace('confirm_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await callback.answer('Замовлення не знайдено.')
        return
    
    # Check if already confirmed
    if order.get('status') == 'confirmed':
        await callback.answer('Замовлення вже підтверджено.')
        return

    await orders_db.update_status(oid, 'confirmed')
    
    # Bot Sync: Update messages for all admins
    from app.utils.admin_notifications import update_order_notifications
    await update_order_notifications(oid, 'confirmed')
    
    # Deduct specialty stock
    try:
        await _deduct_stock_from_cart(order.get('cart', ''), bot)
    except Exception as e:
        logger.error(f"Failed to deduct stock: {e}")

    # Add to active orders if not there
    await active_orders_db.add_active_order(
        oid, order.get('user_id'), order.get('fullname'), order.get('phone'), 
        order.get('location_id'), order.get('cart'), order.get('order_type'), 
        order.get('total_amount'), 
        order.get('payment_mode'), order.get('wishes')
    )
    
    await callback.answer('Підтверджено!')

@admin_router.callback_query(F.data.startswith('reject_order_'))
async def reject_order_handler(callback: CallbackQuery, bot: Bot):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
        
    oid = callback.data.replace('reject_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await callback.answer('Замовлення не знайдено.')
        return
    
    await orders_db.update_status(oid, 'rejected')
    
    # Bot Sync
    from app.utils.admin_notifications import update_order_notifications
    await update_order_notifications(oid, 'rejected')
    
    await callback.answer('Відхилено.')

@admin_router.callback_query(F.data.startswith('finish_order_'))
async def finish_order_handler(callback: CallbackQuery, bot: Bot):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return

    oid = callback.data.replace('finish_order_', '')
    
    # Add to sales
    order = await active_orders_db.get_active_order_by_id(oid)
    if order:
        from app.databases.sales_database import sales_db
        await sales_db.add_sale(
            order_id=oid,
            user_id=order.get('user_id'),
            fullname=order.get('fullname'),
            items=order.get('cart'),
            total=order.get('total', 0),
            location_id=order.get('location_id')
        )
    
    await active_orders_db.delete_active_order(oid)
    
    # Bot Sync
    from app.utils.admin_notifications import update_order_notifications
    await update_order_notifications(oid, 'completed')
    
    await callback.answer('Замовлення завершено!')
    try:
        await callback.message.delete()
    except:
        pass


# --- CONTENT MANAGEMENT BLOCK ---

@admin_router.message(F.text == '☕️ ЗЕРНА', StateFilter(None))
async def manage_beans_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer'): return
    beans = _sorted_beans(await coffee_beans_db.get_all_beans(), 'commercial')
    text = "<b>КОМЕРЦІЙНА КАВА</b>\nСпочатку Espresso, потім Filter."
    if not beans:
        text += "\n\nСписок порожній."
    await message.answer(text, reply_markup=_bean_list_kb(beans, 'commercial', role=role), parse_mode='HTML')

@admin_router.message(F.text == '📍 ЛОКАЦІЇ', StateFilter(None))
async def manage_locations_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer'): return
    await show_locations_page_message(message, role=role)

async def show_locations_page_message(message: Message, role='owner'):
    locations = await location_db.get_all_locations()
    text = "📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ:</b>"
    if not locations:
        text += "\n\nСписок порожній."
    await message.answer(text, reply_markup=_location_list_kb(locations, role=role), parse_mode='HTML')

@admin_router.message(F.text == '📞 КОНТАКТИ', StateFilter(None))
async def manage_contacts_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer'): return
    contacts = await contacts_db.get_all_contacts()
    text = "📞 <b>КЕРУВАННЯ КОНТАКТАМИ:</b>"
    if not contacts:
        text += "\n\nСписок порожній."
    await message.answer(text, reply_markup=_contact_list_kb(contacts, role=role), parse_mode='HTML')

# --- SYSTEM MANAGEMENT BLOCK ---

@admin_router.message(F.text == '👤 ПЕРСОНАЛ', StateFilter(None))
async def manage_staff_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer'): return
    await message.answer('👤 <b>КЕРУВАННЯ ПЕРСОНАЛОМ:</b>\nДодавання адміністраторів та менеджерів.', reply_markup=akb.get_staff_manage_kb(role=role), parse_mode='HTML')

@admin_router.callback_query(F.data == 'beans_manage')
async def manage_beans_cb(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await show_beans_page(callback, 'commercial', role=role)

@admin_router.callback_query(F.data == 'locations_manage')
async def manage_locations_cb(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await show_locations_page(callback, role=role)

@admin_router.callback_query(F.data == 'contacts_manage')
async def manage_contacts_cb(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await show_contacts_page(callback, role=role)


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
    filtered = [b for b in beans if _bean_category(b) == category]
    if category == 'specialty':
        # Hide specialty if out of stock. Handle None values safely.
        filtered = [b for b in filtered if (b.get('stock_packs') if b.get('stock_packs') is not None else 1) > 0]
    return sorted(
        filtered,
        key=lambda b: (_roast_rank(b), str(b.get('name') or '').casefold())
    )

def _bean_list_kb(beans: list[dict], category: str, role='owner') -> InlineKeyboardMarkup:
    other = 'specialty' if category == 'commercial' else 'commercial'
    other_text = 'ПЕРЕЙТИ ДО СПЕШЕЛТІ' if other == 'specialty' else 'ПЕРЕЙТИ ДО КОМЕРЦІЙНОЇ'
    keyboard = []
    
    # Grid: 2 columns
    row = []
    for i, b in enumerate(beans):
        bid = str(b['_id'])
        name = b.get('name', '')[:25]
        # Show stock for specialty
        if category == 'specialty':
            packs = b.get('stock_packs')
            if packs is None: packs = 0
            name = f"{name} ({packs}📦)"
        row.append(InlineKeyboardButton(text=name, callback_data=f'bean_open_{bid}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text=other_text, callback_data=f'beans_page_{other}')])
    if role != 'developer':
        keyboard.append([InlineKeyboardButton(text='➕ ДОДАТИ НОВУ КАВУ', callback_data='bean_new')])
    keyboard.append([InlineKeyboardButton(text='⬅️ НАЗАД В МЕНЮ', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def _bean_card_text(bean: dict) -> str:
    score = _bean_score(bean) or '—'
    is_specialty = _bean_category(bean) == 'specialty'
    category = 'Комерційна' if not is_specialty else 'Спешелті'
    
    # Auto sorting grade for commercial
    grade_info = ""
    stock_info = ""
    if is_specialty:
        packs = bean.get('stock_packs')
        if packs is None: packs = 0
        stock_info = f"\n📦 Запас: <b>{packs} пачок</b> (≈ {packs*0.25:.1f} кг)"
    elif _bean_category(bean) == 'commercial':
        low_score = score.lower()
        if 'зелен' in low_score or 'green' in low_score: grade_info = " (Зелена)"
        elif 'жовт' in low_score or 'yellow' in low_score: grade_info = " (Жовта)"
        elif 'оранж' in low_score or 'orange' in low_score: grade_info = " (Оранжева)"

    lines = [
        f"<b>{html.escape(str(bean.get('name') or 'Без назви'))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"📊 Категорія: <b>{category}{grade_info}</b>{stock_info}",
        f"💰 Ціна 250г: <b>{bean.get('price_250', 0)} ₴</b>",
        f"🔥 Обсмаження: <b>{html.escape(str(bean.get('roast') or '—'))}</b>"
    ]
    
    if is_specialty:
        lines.append(f"📈 Оцінка: <b>{html.escape(score)}</b>")

    lines.extend([
        f"🌿 Склад: <b>{html.escape(str(bean.get('species') or '—'))}</b>",
        f"🍓 Дескриптори: <b>{html.escape(str(bean.get('descriptors') or '—'))}</b>",
        f"🧬 Різновид: <b>{html.escape(str(bean.get('variety') or '—'))}</b>",
        f"⛰ Висота: <b>{html.escape(str(bean.get('altitude') or '—'))}</b>",
        f"🧪 Обробка: <b>{html.escape(str(bean.get('processing') or '—'))}</b>",
        f"📅 Врожай: <b>{html.escape(str(bean.get('harvest') or '—'))}</b>",
        f"━━━━━━━━━━━━━━━",
        f"📖 <b>Опис:</b>",
        f"{html.escape(str(bean.get('description') or '—'))}"
    ])
    return '\n'.join(lines)

async def show_beans_page(callback: CallbackQuery, category: str = 'commercial', role='owner'):
    beans = _sorted_beans(await coffee_beans_db.get_all_beans(), category)
    title = '<b>КОМЕРЦІЙНА КАВА</b>' if category == 'commercial' else '<b>СПЕШЕЛТІ КАВА</b>'
    text = f"{title}\n<i>Спочатку Espresso, потім Filter.</i>"
    if not beans:
        text += "\n\nСписок порожній."
    await safe_edit_message(callback.message, text, reply_markup=_bean_list_kb(beans, category, role=role), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_edit_fields_'))
async def edit_bean_fields_menu(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    bid = callback.data.replace('bean_edit_fields_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if not bean:
        await callback.answer('Зерно не знайдено.', show_alert=True)
        return
    category = _bean_category(bean)
    await safe_edit_message(callback.message, f"⚙️ <b>Оберіть поле для редагування:</b>\n{html.escape(str(bean.get('name', '')))}", reply_markup=akb.get_bean_edit_fields_kb(bid, category), parse_mode='HTML')
    await callback.answer()

async def show_bean_card(target, bean: dict, role='owner'):
    category = _bean_category(bean)
    is_specialty = category == 'specialty'
    text = _bean_card_text(bean)
    kb = akb.get_bean_card_kb(str(bean['_id']), category, is_specialty, role=role)
    
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

def _parse_stock(text: str) -> int:
    """Parse stock input. Returns number of packs (250g)."""
    text = text.lower().replace(',', '.').strip()
    if 'кг' in text:
        try:
            val = float(text.replace('кг', '').strip())
            return int(val * 4) # 1kg = 4 packs of 250g
        except: return 0
    try:
        # Extract only digits
        digits = re.sub(r'[^\d]', '', text)
        return int(digits) if digits else 0
    except: return 0

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
    if field == 'stock':
        packs = _parse_stock(value)
        if packs <= 0:
            return None, 'Введіть коректну кількість (напр. 5 кг або 20).'
        return packs, None
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
    role = await get_user_role(message.from_user.id)
    data = await state.get_data()
    payload = {field: data[field] for field in BEAN_EDIT_FIELDS if field in data}
    if data.get('image_url'):
        payload['image_url'] = data['image_url']
    
    score = str(payload.get('quality_score') or '').strip()
    is_specialty = False
    try:
        if score != '-' and float(score.replace(',', '.')) >= 80:
            is_specialty = True
    except: pass

    payload['category'] = 'specialty' if is_specialty else 'commercial'
    
    # ONLY ask for stock if it's Specialty and not in data yet
    if is_specialty and 'stock' not in data:
        # We haven't asked for stock yet. Update steps and ask.
        await state.update_data(bean_steps=BEAN_ADD_STEPS + [('stock', '📦 <b>Скільки кави є в наявності?</b>\n\nВведіть у КГ (напр. <code>10 кг</code>) або кількість пачок по 250г (напр. <code>40</code>).')])
        await state.update_data(bean_step_index=len(BEAN_ADD_STEPS))
        await _ask_bean_step(message, state)
        # Ensure we stay in a state that handles this input
        await state.set_state(AdminStates.editing_bean_field)
        return

    # If we are here, it's either commercial or stock is already in data
    payload['stock_packs'] = data.get('stock', 999) if is_specialty else 999

    if data.get('bean_mode') == 'edit':
        bid = data['edit_bean_id']
        await coffee_beans_db.update_bean(bid, payload)
        bean = await coffee_beans_db.get_bean_by_id(bid)
        await message.answer('✅ Зерно оновлено.')
        if bean:
            await show_bean_card(message, bean, role=role)
    else:
        bid = await coffee_beans_db.add_bean(**payload)
        bean = await coffee_beans_db.get_bean_by_id(bid)
        await message.answer('✅ Зерно додано.')
        if bean:
            await show_bean_card(message, bean, role=role)
    await state.clear()

@admin_router.callback_query(F.data.startswith('bean_restock_'))
async def bean_restock_start(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    bid = callback.data.replace('bean_restock_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if not bean:
        await callback.answer('Зерно не знайдено.')
        return
    await state.clear()
    await state.update_data(restock_bid=bid)
    await callback.message.answer(f"📦 <b>ПОПОВНЕННЯ: {html.escape(bean['name'])}</b>\n\nВведіть скільки ДОДАТИ:\n- у КГ (напр. <code>5 кг</code>)\n- або пачок (напр. <code>20</code>)", parse_mode='HTML', reply_markup=_cancel_kb())
    await state.set_state(AdminStates.restocking_bean)
    await callback.answer()

@admin_router.message(AdminStates.restocking_bean)
async def bean_restock_input(message: Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role == 'developer': return
    data = await state.get_data()
    bid = data['restock_bid']
    packs_to_add = _parse_stock(message.text or '')
    if packs_to_add <= 0:
        await message.answer("Будь ласка, введіть число (напр. 5 або 2 кг).")
        return
    
    bean = await coffee_beans_db.get_bean_by_id(bid)
    current = bean.get('stock_packs')
    if current is None: current = 0
    new_total = current + packs_to_add
    await coffee_beans_db.update_bean(bid, {'stock_packs': new_total})
    
    await message.answer(f"✅ Додано <b>{packs_to_add}</b> пачок.\nТепер усього: <b>{new_total}</b>", parse_mode='HTML')
    await state.clear()
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if bean: await show_bean_card(message, bean, role=role)

@admin_router.callback_query(F.data.in_(['beans_list', 'beans_list_edit', 'beans_list_del', 'beans_page_commercial', 'beans_page_specialty']))
async def list_beans_admin(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    category = 'specialty' if callback.data.endswith('specialty') else 'commercial'
    await show_beans_page(callback, category, role=role)

@admin_router.callback_query(F.data == 'bean_add')
async def add_bean_start(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await show_beans_page(callback, 'commercial', role=role)

@admin_router.callback_query(F.data == 'bean_new')
async def add_bean_new(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    await state.clear()
    await state.update_data(bean_mode='add', bean_step_index=0, bean_steps=BEAN_ADD_STEPS)
    await callback.message.answer('➕ <b>ДОДАВАННЯ КАВИ</b>', parse_mode='HTML')
    await _ask_bean_step(callback.message, state)
    await state.set_state(AdminStates.adding_bean_name)
    await callback.answer()

@admin_router.callback_query(F.data == 'bean_add_cancel')
async def add_bean_cancel(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    await state.clear()
    await safe_edit_message(callback.message, '❌ Дію скасовано.', reply_markup=akb.get_beans_manage_kb(role=role), parse_mode='HTML')
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_open_'))
async def open_bean_card(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    bid = callback.data.replace('bean_open_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    if not bean:
        await callback.answer('Зерно не знайдено.', show_alert=True)
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await show_bean_card(callback.message, bean, role=role)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_del_confirm_'))
async def delete_bean_confirm(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer':
        await callback.answer("🛠 У Розробника права тільки на перегляд.", show_alert=True)
        return
    bid = callback.data.replace('bean_del_confirm_', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🗑 ТАК, ВИДАЛИТИ', callback_data=f'bean_del_final_{bid}')],
        [InlineKeyboardButton(text='❌ СКАСУВАТИ', callback_data=f'bean_open_{bid}')]
    ])
    await safe_edit_message(callback.message, "Видалити це зерно?", reply_markup=kb)
    await callback.answer()

@admin_router.callback_query(F.data.startswith('bean_del_final_'))
async def delete_bean_final(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer': return
    bid = callback.data.replace('bean_del_final_', '')
    bean = await coffee_beans_db.get_bean_by_id(bid)
    category = _bean_category(bean or {})
    await coffee_beans_db.delete_bean(bid)
    await callback.answer('Зерно видалено.')
    await show_beans_page(callback, category, role=role)

@admin_router.callback_query(F.data.startswith('bean_fedit_'))
async def edit_bean_single_field_start(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    if role == 'developer': return
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
    role = await get_user_role(callback.from_user.id)
    if role == 'developer': return
    payload = callback.data.replace('bean_set_category_', '')
    bid, category = payload.rsplit('_', 1)
    update = {'category': category}
    if category == 'commercial':
        update['quality_score'] = '-'
    await coffee_beans_db.update_bean(bid, update)
    bean = await coffee_beans_db.get_bean_by_id(bid)
    await callback.answer('Категорію оновлено.')
    if bean:
        await show_bean_card(callback.message, bean, role=role)

@admin_router.message(AdminStates.adding_bean_name)
@admin_router.message(AdminStates.editing_bean_field)
async def bean_flow_input(message: Message, state: FSMContext, bot: Bot):
    role = await get_user_role(message.from_user.id)
    if role == 'developer': return
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
            await show_bean_card(message, bean, role=role)
        return

    steps = data.get('bean_steps') or BEAN_ADD_STEPS
    step_index = int(data.get('bean_step_index', 0))
    field, _ = steps[step_index]
    if field == 'photo':
        value = await process_photo(message, bot)
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
    await admin_db.confirm_auth_request(uid)
    try:
        await bot.send_message(uid, f"✅ <b>ВХІД ПІДТВЕРДЖЕНО!</b>\n\nТепер ви можете повернутися до браузера.", parse_mode='HTML')
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
