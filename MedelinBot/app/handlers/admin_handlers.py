
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from app.keyboards import admin_keyboards as akb

from app.keyboards import user_keyboards as kb

from app.common.config import DEVELOPER_IDS

from app.databases.orders_database import orders_db

from app.databases.active_bookings_database import active_bookings_db

from app.databases.active_orders_database import active_orders_db

from app.databases.admin_database import admin_db

from app.databases.user_database import user_db

from app.databases.location_database import location_db

from app.databases.socials_database import socials_db

from app.databases.guest_messages_database import guest_messages_db

from app.databases.coffee_beans_database import coffee_beans_db

from app.utils.phone_utils import normalize_phone

from app.utils.data_cache import public_data_cache

from app.utils.photo_utils import process_photo

from app.utils.payment_refunds import refund_telegram_payment

from app.utils.message_utils import safe_edit_message

import re, time, asyncio

from aiogram.filters import CommandStart

admin_router = Router()

ROLE_LEVELS = {

    'developer': 100,

    'owner': 80,

    'boss': 80,

    'delivery_manager': 40,

    'courier': 20

}

def can_manage(caller_role: str, target_role: str) -> bool:
    caller_role = (caller_role or '').strip().lower()
    target_role = (target_role or '').strip().lower()

    if caller_role == 'developer': return True
    if target_role == 'developer': return False
    if caller_role in ('owner', 'boss'): 
        return target_role not in ('owner', 'boss', 'developer')
    
    return ROLE_LEVELS.get(caller_role, 0) > ROLE_LEVELS.get(target_role, 0)

@admin_router.message(CommandStart())

async def admin_start_cmd(message: Message, state: FSMContext):

    await state.clear()

    if await admin_db.is_admin(message.from_user.id):
        await admin_panel_enter(message, state)
    else:
        await message.answer("🔒 <b>ДОСТУП ОБМЕЖЕНО</b>\nЦей бот призначений тільки для адміністрації.", parse_mode='HTML')

class AdminStates(StatesGroup):

    adding_admin_id = State()

    adding_admin_name = State()

    adding_admin_role = State()

    adding_admin_location = State()

    adding_admin_confirm = State()

class BeanStates(StatesGroup):

    waiting_name = State()

    waiting_price = State()

    waiting_desc = State()

    waiting_volume = State()

    waiting_image = State()

    edit_waiting_value = State()

class LocationStates(StatesGroup):

    waiting_name = State()

    waiting_address = State()

    waiting_schedule = State()

    waiting_phone = State()

    waiting_email = State()

    waiting_maps_url = State()

    waiting_atmosphere = State()

    waiting_amenities = State()

    waiting_image = State()

    waiting_max_tables = State()

    waiting_confirm = State()

    edit_select = State()

    edit_field = State()

    edit_value = State()

class SocialStates(StatesGroup):

    waiting_name = State()

    waiting_url = State()

    edit_select = State()

    edit_field = State()

    edit_value = State()

def extract_coords_from_maps(url: str) -> tuple[float, float] | None:

    if not url: return None

    m = re.search('@(-?\\d+\\.\\d+),(-?\\d+\\.\\d+)', url)

    if m: return (float(m.group(1)), float(m.group(2)))

    m = re.search('!3d(-?\\d+\\.\\d+)!4d(-?\\d+\\.\\d+)', url)

    if m: return (float(m.group(1)), float(m.group(2)))

    m = re.search('q=(-?\\d+\\.\\d+),(-?\\d+\\.\\d+)', url)

    if m: return (float(m.group(1)), float(m.group(2)))

    return None

async def get_user_role(user_id):
    role = await admin_db.get_admin_role(user_id)
    return (role or 'delivery_manager').strip().lower()

async def restart_fsm_on_command(message: Message, state: FSMContext) -> bool:

    text = (message.text or '').strip()

    if not text.startswith('/'): return False

    await state.clear()

    if text.split()[0].lower() == '/start':

        await admin_start_cmd(message, state)

    return True

async def deliver_guest_message(bot: Bot, order: dict | None, text_html: str, site_text: str, reply_callback_data: str | None=None) -> str:

    if not order: return 'missing_order'

    telegram_target = None

    if order.get('user_id'):

        try: telegram_target = int(order['user_id'])

        except: telegram_target = None

    if telegram_target is None and order.get('username'):

        tg_username = str(order.get('username') or '').lstrip('@').strip()

        found_user = await user_db.get_user_by_username(tg_username) if tg_username else None

        if found_user: telegram_target = int(found_user[0])

    if telegram_target is not None:

        reply_markup = None
        # Повідомлення від адміна гостю прибрали (підтримка вимкнена)
        # але ми залишаємо цей метод для сервісних сповіщень (Прийнято/Відхилено)

        telegram_ok = False
        try:
            await bot.send_message(telegram_target, text_html, parse_mode='HTML', reply_markup=reply_markup)
            telegram_ok = True
        except:
            telegram_ok = False

    return 'both' if telegram_target and telegram_ok else 'site'

@admin_router.message(F.text == '↩️ НА ГОЛОВНУ')

async def back_to_main_from_admin(message: Message, state: FSMContext):

    await state.clear()

    await admin_panel_enter(message, state)

@admin_router.callback_query(F.data == 'back_main_menu_only')

async def back_to_main_cb(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    try: await callback.message.delete()

    except: pass

    await admin_panel_enter(callback.message, state)

@admin_router.message(F.text == '🔄 СИНХРОНІЗУВАТИ САЙТ')
async def sync_website_handler(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) not in ('boss', 'owner', 'developer'): return
    
    await message.answer('⏳ <b>СИНХРОНІЗАЦІЯ З САЙТОМ РОЗПОЧАТА...</b>\nЦе може зайняти до 30 секунд.', parse_mode='HTML')
    
    try:
        await public_data_cache.warm_all()
        from pathlib import Path
        import asyncio
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        try:
            proc_git = await asyncio.create_subprocess_exec('git', '--version', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc_git.wait()
        except Exception:
            await message.answer('❌ <b>ПОМИЛКА:</b> Git не встановлений.', parse_mode='HTML')
            return

        commands = [
            ['git', 'add', 'MedelinSite/cache/*.json'],
            ['git', 'commit', '-m', f"Manual sync from bot by {message.from_user.id}"],
            ['git', 'push', 'origin', 'release']
        ]
        
        results = []
        for cmd in commands:
            process = await asyncio.create_subprocess_exec(*cmd, cwd=str(root_dir), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            results.append(f"<code>{' '.join(cmd)}</code>: {'✅' if process.returncode == 0 else '⚠️'}")

        await message.answer('✅ <b>СИНХРОНІЗАЦІЮ ЗАВЕРШЕНО!</b>\n\n' + '\n'.join(results), parse_mode='HTML')
    except Exception as e:
        await message.answer(f'❌ <b>ПОМИЛКА:</b>\n<code>{str(e)}</code>', parse_mode='HTML')

@admin_router.message(F.text.in_([kb.BTN_ADMIN, '🔐 АДМІН-ПАНЕЛЬ', '🛰 АДМІН-ПАНЕЛЬ']))

async def admin_panel_enter(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    await state.clear()

    role = await get_user_role(message.from_user.id)
    role_name = akb.ROLE_NAMES.get(role, role).upper()

    is_on_shift = await admin_db.is_on_shift(message.from_user.id)
    shift_info = ""
    if is_on_shift == 'NP':
        shift_info = f"\nАктивна зміна: <b>НОВА ПОШТА</b>"
    elif isinstance(is_on_shift, str) and is_on_shift not in ("True", "1", "False", "0"):
        loc = await location_db.get_location_by_id(is_on_shift)
        if loc:
            shift_info = f"\nАктивна зміна: <b>{loc['name']}</b>"

    await message.answer(f'🔐 <b>ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ</b>\nВаша роль: <b>{role_name}</b>{shift_info}', reply_markup=akb.get_main_admin_menu(bool(is_on_shift), role), parse_mode='HTML')

@admin_router.message(F.text == '🟢 ПОЧАТИ ЗМІНУ')
async def start_shift(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    role = await get_user_role(message.from_user.id)
    if role != 'delivery_manager': return
    await state.clear()
    
    await admin_db.set_shift_status(message.from_user.id, 'NP')
    await message.answer('🟢 <b>ЗМІНУ РОЗПОЧАТО!</b>\nВи будете отримувати замовлення з Нової Пошти.', reply_markup=akb.get_main_admin_menu(True, role), parse_mode='HTML')

@admin_router.message(F.text == '🔴 ЗАВЕРШИТИ ЗМІНУ')
async def end_shift(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    role = await get_user_role(message.from_user.id)
    await admin_db.set_shift_status(message.from_user.id, False)
    await message.answer('🔴 <b>ЗМІНУ ЗАВЕРШЕНО!</b>', reply_markup=akb.get_main_admin_menu(False, role), parse_mode='HTML')

@admin_router.message(F.text == '🆕 НОВІ ЗАПИТИ')

async def show_new_bookings(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    await state.clear()

    role = await get_user_role(message.from_user.id)

    if role in ('boss', 'owner', 'developer'):
        bookings = await orders_db.get_new_orders()
    elif role == 'delivery_manager':
        all_orders = await orders_db.get_new_orders()
        bookings = [o for o in all_orders if o.get('order_type') in ('nova_poshta', 'beans_delivery') or o.get('location_id') == 'NP']
    else:
        shift_loc = await admin_db.is_on_shift(message.from_user.id)
        if isinstance(shift_loc, str) and shift_loc not in ("True", "1", "False", "0"):
            bookings = await orders_db.get_new_orders_by_locations([shift_loc])
        else:
            loc_ids = await admin_db.get_locations_for_admin(message.from_user.id)
            bookings = await orders_db.get_new_orders_by_locations(loc_ids) if loc_ids else await orders_db.get_new_orders()

    if not bookings:

        await message.answer('📭 <b>Наразі немає нових запитів.</b>', parse_mode='HTML')

        return

    locations_dict = await location_db.get_locations_dict()

    for b in bookings:

        if b.get('order_type') in ('nova_poshta', 'beans_delivery') or b.get('location_id') == 'NP':
            loc_name = 'Нова Пошта'
            wishes = b.get('wishes') or ''
            if 'НП:' in wishes:
                loc_name = f"Нова Пошта — {wishes.split('НП:', 1)[1].split('|', 1)[0].strip()}"
        else:
            loc_name = locations_dict.get(b['location_id'], {}).get('name', '—')

        order_id = b.get('order_id') or str(b['_id'])

        t = f"📥 <b>НОВИЙ ЗАПИТ</b>\n\n👤 <b>КЛІЄНТ:</b> {b['fullname']}\n📞 <code>{b['phone']}</code>\n🏛 <b>Заклад:</b> {loc_name}\n"
        date_time = b.get('date_time')
        people_count = b.get('people_count')
        if date_time and str(date_time).lower() not in ('none', '—', '', 'зараз', 'по готовності'):
            t += f"🕔 <b>Час:</b> {date_time}\n"
        if people_count and str(people_count).lower() not in ('none', '—', '', '0'):
            t += f"👥 <b>Гостей:</b> {people_count}\n"
        t += f"🥘 <b>Замовлення:</b> {b['cart']}"

        await message.answer(t, reply_markup=akb.get_booking_manage_kb(order_id, b.get('user_id')), parse_mode='HTML')

@admin_router.message(F.text == '⚡️ АКТИВНІ')

async def show_active_panel(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    await message.answer('⚡️ <b>АКТИВНІ ЗАПИСИ</b>\nОберіть розділ:', reply_markup=akb.get_active_types_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'active_panel')

async def show_active_panel_cb(callback: CallbackQuery):

    await safe_edit_message(callback.message, '⚡️ <b>АКТИВНІ ЗАПИСИ</b>\nОберіть розділ:', reply_markup=akb.get_active_types_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'active_bookings')

async def list_active_bookings(callback: CallbackQuery):

    await list_active_orders(callback)

@admin_router.callback_query(F.data == 'active_orders')

async def list_active_orders(callback: CallbackQuery):

    role = await get_user_role(callback.from_user.id)

    if role in ('boss', 'owner', 'developer'):
        locs = None
    elif role == 'delivery_manager':
        locs = ['NP']
    else:
        shift_loc = await admin_db.is_on_shift(callback.from_user.id)
        if isinstance(shift_loc, str) and shift_loc not in ("True", "1", "False", "0"):
            locs = [shift_loc]
        else:
            locs = await admin_db.get_locations_for_admin(callback.from_user.id) or None

    orders = await active_orders_db.get_active_orders(locs)

    if not orders:

        await callback.answer('Немає активних замовлень.')

        return

    await safe_edit_message(callback.message, '🛍 <b>АКТИВНІ ЗАМОВЛЕННЯ:</b>\nНатисніть для завершення:', reply_markup=akb.get_active_orders_list_kb(orders), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('finish_book_'))

async def finish_booking(callback: CallbackQuery):

    bid = callback.data.replace('finish_book_', '')

    await active_bookings_db.remove_booking(bid)

    await callback.answer('Бронь завершена!')

    await list_active_bookings(callback)

@admin_router.callback_query(F.data.startswith('finish_order_'))

async def finish_order(callback: CallbackQuery):

    oid = callback.data.replace('finish_order_', '')

    await active_orders_db.remove_order(oid)

    await callback.answer('Замовлення виконано!')

    await list_active_orders(callback)

@admin_router.message(F.text == '☕ ЗЕРНО')

async def show_beans_panel(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    if await get_user_role(message.from_user.id) not in ('boss', 'owner', 'developer'): return

    await state.clear()

    await message.answer('☕ <b>КЕРУВАННЯ ЗЕРНОМ</b>', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '📍 ЛОКАЦІЇ')

async def show_locs_panel(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    if await get_user_role(message.from_user.id) not in ('boss', 'owner', 'developer'): return

    await state.clear()

    await message.answer('📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ</b>', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '📱 СОЦМЕРЕЖІ')

async def show_socs_panel(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    if await get_user_role(message.from_user.id) not in ('boss', 'owner', 'developer'): return

    await state.clear()

    await message.answer('📱 <b>КЕРУВАННЯ СОЦМЕРЕЖАМИ</b>', reply_markup=akb.get_socials_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '👥 КОМАНДА')

async def show_team_panel(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    await state.clear()

    role = await get_user_role(message.from_user.id)

    is_privileged = role in ('boss', 'owner', 'developer')

    await message.answer('👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>', reply_markup=akb.get_admin_management_kb(is_privileged), parse_mode='HTML')

@admin_router.callback_query(F.data == 'admin_panel_back')

async def admin_panel_back(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    role = await get_user_role(callback.from_user.id)
    role_name = akb.ROLE_NAMES.get(role, role).upper()

    is_on_shift = await admin_db.is_on_shift(callback.from_user.id)

    try: await callback.message.delete()

    except: pass

    await callback.message.answer(f'🔐 <b>ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ</b>\nВаша роль: <b>{role_name}</b>', reply_markup=akb.get_main_admin_menu(is_on_shift, role), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('adm2_confirm_'))

async def confirm_order_cb(callback: CallbackQuery, bot: Bot):

    oid = callback.data.replace('adm2_confirm_', '')

    order = await orders_db.get_order_by_id(oid)

    if not order:

        await callback.answer('Замовлення не знайдено.')

        return

    await orders_db.update_status(oid, 'confirmed')

    if order.get('order_type') == 'booking':

        text = '✅ <b>ВАШЕ БРОНЮВАННЯ ПІДТВЕРДЖЕНО!</b>\n\nЧекаємо на вас у Medelin! ☕'

    else:

        await active_orders_db.add_active_order(
            oid, order.get('user_id'), order['fullname'], order.get('phone', '—'),
            order['location_id'], order['cart'], order['order_type'],
            order.get('table_number', ''), order.get('total_amount', 0),
            order.get('payment_mode', ''), order.get('wishes', '')
        )

        text = '✅ <b>ВАШЕ ЗАМОВЛЕННЯ ПІДТВЕРДЖЕНО!</b>\n\nМи вже почали готувати. Смачного! ☕'

    await deliver_guest_message(bot, order, text, text)

    await safe_edit_message(callback.message, callback.message.text + '\n\n✅ <b>ПІДТВЕРДЖЕНО</b>', parse_mode='HTML')

    await callback.answer('Підтверджено!')

@admin_router.callback_query(F.data.startswith('adm2_cancel_'))

async def cancel_order_cb(callback: CallbackQuery, bot: Bot):

    oid = callback.data.replace('adm2_cancel_', '')

    order = await orders_db.get_order_by_id(oid)

    if not order:

        await callback.answer('Замовлення не знайдено.')

        return

    await orders_db.update_status(oid, 'cancelled')

    text = '❌ <b>НА ЖАЛЬ, ЗАМОВЛЕННЯ ВІДХИЛЕНО</b>\n\nВибачте за незручності. Спробуйте іншу локацію або час.'

    await deliver_guest_message(bot, order, text, text)

    from app.utils.message_utils import fade_out_message

    await fade_out_message(callback.message, '❌ <b>ВІДХИЛЕНО</b>')

    await callback.answer('Відхилено.')

@admin_router.callback_query(F.data == 'adm_add_new')

async def adm_add_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(AdminStates.adding_admin_id)

    help_text = "🆔 <b>ВВЕДІТЬ ДАНІ НОВОГО СПІВРОБІТНИКА:</b>\n\nTelegram ID, Username або Телефон."

    await callback.message.answer(help_text, reply_markup=akb.get_admin_management_kb(True), parse_mode='HTML')

    await callback.answer()

@admin_router.message(AdminStates.adding_admin_id)

async def adm_add_identity(message: Message, state: FSMContext):

    val = message.text.strip()

    target_uid = None

    target_username = "N/A"

    if val.isdigit(): target_uid = int(val)

    elif val.startswith('@'):

        u = await user_db.get_user_by_username(val.replace('@', ''))

        if u: target_uid, target_username = int(u[0]), val

    elif val.startswith('+') or (val.startswith('380') and len(val) == 12):

        phone = normalize_phone(val)

        u = await user_db.get_user_by_phone(phone)

        if u: target_uid, target_username = int(u[0]), (f"@{u[1]}" if u[1] else "N/A")

    if not target_uid:

        await message.answer("❌ Користувача не знайдено.")

        return

    await state.update_data(new_adm_id=target_uid, new_adm_username=target_username)

    await message.answer(f"👤 Знайдено: <code>{target_uid}</code>\nВведіть Ім'я:", parse_mode='HTML')

    await state.set_state(AdminStates.adding_admin_name)

@admin_router.message(AdminStates.adding_admin_name)

async def adm_add_name(message: Message, state: FSMContext):

    await state.update_data(new_adm_name=message.text)

    caller_role = await get_user_role(message.from_user.id)

    await message.answer("🎭 Оберіть роль:", reply_markup=akb.get_admin_roles_kb(caller_role))

    await state.set_state(AdminStates.adding_admin_role)

@admin_router.callback_query(F.data.startswith('set_role_'), AdminStates.adding_admin_role)

async def adm_add_role(callback: CallbackQuery, state: FSMContext):

    role = callback.data.replace('set_role_', '')

    data = await state.get_data()

    await admin_db.add_admin(data['new_adm_id'], data.get('new_adm_username', 'N/A'), data['new_adm_name'], callback.from_user.id, role, locations=[])

    await safe_edit_message(callback.message, f"✅ Додано!", reply_markup=akb.get_admin_management_kb(True), parse_mode='HTML')

    await state.clear()

    await callback.answer()

@admin_router.callback_query(F.data == 'adm_list')

async def adm_list(callback: CallbackQuery):

    admins = await admin_db.get_admins_with_locations()

    text = "👥 <b>КОМАНДА MEDELIN:</b>\n\n"

    for aid, user, name, role, on_shift, notif, locs in admins:
        role_name = akb.ROLE_NAMES.get(role, role)
        text += f"{'🟢' if on_shift else '🔴'} <b>{name}</b> (@{user or '—'})\nРоль: {role_name}\n\n"

    await safe_edit_message(callback.message, text, reply_markup=akb.get_admin_management_kb(True), parse_mode='HTML')

@admin_router.callback_query(F.data == 'adm_remove')

async def adm_remove_list(callback: CallbackQuery):

    caller_role = await get_user_role(callback.from_user.id)

    all_admins = await admin_db.get_admins_basic()

    removable = [(u, un, d, r) for u, un, d, r in all_admins if can_manage(caller_role, r) and int(u) != int(callback.from_user.id)]

    if not removable:

        await callback.answer("Немає прав.", show_alert=True)

        return

    await safe_edit_message(callback.message, "🗑 Оберіть кого видалити:", reply_markup=akb.get_admins_to_remove_kb(removable), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('adm_del_yes_'))

async def adm_remove_confirm_yes(callback: CallbackQuery):

    uid = int(callback.data.replace('adm_del_yes_', ''))

    await admin_db.remove_admin(uid)

    await callback.answer("Видалено!", show_alert=True)

    await adm_remove_list(callback)

@admin_router.message(BeanStates.waiting_name)
async def bean_add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('💰 Ціна за 250г:')
    await state.set_state(BeanStates.waiting_price)

@admin_router.message(BeanStates.waiting_price)
async def bean_add_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', '.'))
        await state.update_data(price=price)
        await message.answer('📜 Опис:')
        await state.set_state(BeanStates.waiting_desc)
    except: await message.answer('❌ Введіть число.')

@admin_router.message(BeanStates.waiting_desc)
async def bean_add_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer('🖼 Фото або "ні":')
    await state.set_state(BeanStates.waiting_image)

@admin_router.message(BeanStates.waiting_image)
async def bean_add_image(message: Message, state: FSMContext, bot: Bot):
    img = await process_photo(message, bot) if message.photo else ''
    await state.update_data(image_url=img)
    data = await state.get_data()
    await coffee_beans_db.add_bean(data['name'], data['price'], data.get('description', ''), '', '', '', image_url=data.get('image_url', ''), acidity=0, bitterness=0, body=0)
    await public_data_cache.refresh('coffee')
    await message.answer('✅ Додано!', reply_markup=akb.get_beans_manage_kb())
    await state.clear()
