
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from app.keyboards import admin_keyboards as akb

from app.keyboards import user_keyboards as kb

from app.common.config import BOSS_IDS

from app.databases.orders_database import orders_db

from app.databases.active_bookings_database import active_bookings_db

from app.databases.active_orders_database import active_orders_db

from app.databases.admin_database import admin_db

from app.databases.user_database import user_db

from app.databases.menu_database import menu_db

from app.databases.location_database import location_db

from app.databases.socials_database import socials_db

from app.databases.guest_messages_database import guest_messages_db

from app.databases.coffee_beans_database import coffee_beans_db

from app.utils.phone_utils import normalize_phone

from app.utils.data_cache import public_data_cache

from app.utils.payment_refunds import refund_telegram_payment

from app.utils.message_utils import safe_edit_message

import re, time

from aiogram.filters import CommandStart

admin_router = Router()

ROLE_LEVELS = {

    'developer': 100,

    'owner': 80,

    'boss': 80,

    'super': 60,

    'admin': 40,

    'courier': 20,

    'delivery_manager': 20

}

def can_manage(caller_role: str, target_role: str) -> bool:

    if caller_role == 'developer': return True

    if target_role == 'developer': return False

    if caller_role in ('owner', 'boss'): return True

    if target_role in ('owner', 'boss'): return False

    if target_role == 'super': return False

    return ROLE_LEVELS.get(caller_role, 0) > ROLE_LEVELS.get(target_role, 0)

@admin_router.message(CommandStart())

async def admin_start_cmd(message: Message, state: FSMContext):

    await state.clear()

    from app.handlers.user_handlers import cmd_start

    await cmd_start(message, state)

class AdminStates(StatesGroup):

    adding_admin_id = State()

    adding_admin_name = State()

    adding_admin_role = State()

    adding_admin_location = State()

    adding_admin_confirm = State()

    messaging_guest = State()

class MenuStates(StatesGroup):

    waiting_category = State()

    waiting_new_category = State()

    waiting_name = State()

    waiting_price = State()

    waiting_price_250 = State()

    waiting_price_500 = State()

    waiting_price_1000 = State()

    waiting_desc = State()

    waiting_volume = State()

    waiting_calories = State()

    waiting_image = State()

    waiting_confirm = State()

    edit_select_item = State()

    edit_waiting_field = State()

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

    return await admin_db.get_admin_role(user_id)

async def restart_fsm_on_command(message: Message, state: FSMContext) -> bool:

    text = (message.text or '').strip()

    if not text.startswith('/'): return False

    await state.clear()

    if text.split()[0].lower() == '/start':

        from app.handlers.user_handlers import cmd_start

        await cmd_start(message, state)

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

        if reply_callback_data:

            reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='💬 ВІДПОВІСТИ', callback_data=reply_callback_data)]])

        try:

            await bot.send_message(telegram_target, text_html, parse_mode='HTML', reply_markup=reply_markup)

            return 'telegram'

        except: pass

    await guest_messages_db.add_message(order_id=order.get('id'), phone=order.get('phone'), source='admin', text=site_text)

    return 'site'

@admin_router.message(F.text == '📝 ПРИЙНЯТИ ЗАМОВЛЕННЯ')
async def admin_take_order_start(message: Message, state: FSMContext):
    # Адміністратор починає замовлення від імені клієнта (локально в боті)
    await state.clear()
    from app.handlers.user_handlers import open_menu
    await message.answer('📝 <b>ПРИЙОМ ЗАМОВЛЕННЯ (РЕЖИМ АДМІНІСТРАТОРА)</b>\n\nОберіть категорію:', parse_mode='HTML')
    await open_menu(message, state)

@admin_router.message(F.text == '↩️ НА ГОЛОВНУ')

async def back_to_main_from_admin(message: Message, state: FSMContext):

    await state.clear()

    from app.handlers.user_handlers import cmd_start

    await cmd_start(message, state)

@admin_router.callback_query(F.data == 'back_main_menu_only')

async def back_to_main_cb(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    from app.handlers.user_handlers import cmd_start

    try: await callback.message.delete()

    except: pass

    callback.message.from_user = callback.from_user

    await cmd_start(callback.message, state)

@admin_router.message(F.text.in_([kb.BTN_ADMIN, '🔐 АДМІН-ПАНЕЛЬ', '🛰 АДМІН-ПАНЕЛЬ']))

async def admin_panel_enter(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    await state.clear()

    role = await get_user_role(message.from_user.id)
    role_name = akb.ROLE_NAMES.get(role, role).upper()

    is_on_shift = await admin_db.is_on_shift(message.from_user.id)
    shift_info = ""
    if isinstance(is_on_shift, str) and is_on_shift not in ("True", "1", "False", "0"):
        loc = await location_db.get_location_by_id(is_on_shift)
        if loc:
            shift_info = f"\nАктивна зміна: <b>{loc['name']}</b>"

    await message.answer(f'🔐 <b>ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ</b>\nВаша роль: <b>{role_name}</b>{shift_info}', reply_markup=akb.get_main_admin_menu(bool(is_on_shift), role), parse_mode='HTML')

@admin_router.message(F.text == '🟢 ПОЧАТИ ЗМІНУ')
async def start_shift(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    role = await get_user_role(message.from_user.id)
    if role != 'admin': return
    await state.clear()
    
    loc_ids = await admin_db.get_locations_for_admin(message.from_user.id)
    if not loc_ids:
        # Якщо список порожній, це означає "Усі заклади"
        all_locs = await location_db.get_all_locations()
        loc_ids = [str(loc['_id']) for loc in all_locs]
        
    if not loc_ids:
        await message.answer('❌ В системі немає жодного закладу.', parse_mode='HTML')
        return
        
    if len(loc_ids) == 1:
        loc_id = loc_ids[0]
        await admin_db.set_shift_status(message.from_user.id, loc_id)
        loc = await location_db.get_location_by_id(loc_id)
        loc_name = loc['name'] if loc else 'Заклад'
        await message.answer(f'🟢 <b>ЗМІНУ РОЗПОЧАТО!</b>\nЗаклад: <b>{loc_name}</b>', reply_markup=akb.get_main_admin_menu(True, role), parse_mode='HTML')
        return
        
    buttons = []
    for lid in loc_ids:
        loc = await location_db.get_location_by_id(lid)
        if loc:
            buttons.append([InlineKeyboardButton(text=f"📍 {loc['name']}", callback_data=f"start_shift_loc_{lid}")])
            
    if not buttons:
        await message.answer('❌ Немає доступних локацій.')
        return
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer('📍 <b>Оберіть заклад для початку зміни:</b>', reply_markup=keyboard, parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('start_shift_loc_'))
async def start_shift_loc_callback(callback: CallbackQuery, state: FSMContext):
    loc_id = callback.data.replace('start_shift_loc_', '')
    role = await get_user_role(callback.from_user.id)
    if role != 'admin': return
    
    await admin_db.set_shift_status(callback.from_user.id, loc_id)
    loc = await location_db.get_location_by_id(loc_id)
    loc_name = loc['name'] if loc else 'Заклад'
    
    await callback.message.delete()
    await callback.message.answer(f'🟢 <b>ЗМІНУ РОЗПОЧАТО!</b>\nЗаклад: <b>{loc_name}</b>', reply_markup=akb.get_main_admin_menu(True, role), parse_mode='HTML')
    await callback.answer()

@admin_router.message(F.text == '🔴 ЗАВЕРШИТИ ЗМІНУ')

async def end_shift(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    role = await get_user_role(message.from_user.id)

    if role != 'admin': return

    await state.clear()

    await admin_db.set_shift_status(message.from_user.id, False)

    await message.answer('🔴 <b>ЗМІНУ ЗАВЕРШЕНО.</b>', reply_markup=akb.get_main_admin_menu(False, role), parse_mode='HTML')

@admin_router.message(F.text == '🆕 НОВІ ЗАПИТИ')

async def show_new_bookings(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    await state.clear()

    role = await get_user_role(message.from_user.id)

    if role in ('super', 'boss', 'owner', 'developer'):
        bookings = await orders_db.get_new_orders()
    elif role == 'delivery_manager':
        # Delivery manager sees only Nova Poshta orders
        all_orders = await orders_db.get_new_orders()
        bookings = [o for o in all_orders if o.get('order_type') == 'nova_poshta']
    else:
        shift_loc = await admin_db.is_on_shift(message.from_user.id)
        if isinstance(shift_loc, str) and shift_loc not in ("True", "1", "False", "0"):
            bookings = await orders_db.get_new_orders_by_locations([shift_loc])
        else:
            loc_ids = await admin_db.get_locations_for_admin(message.from_user.id)
            if loc_ids:
                bookings = await orders_db.get_new_orders_by_locations(loc_ids)
            else:
                # Empty locations list = access to all locations
                bookings = await orders_db.get_new_orders()

    if not bookings:

        await message.answer('📭 <b>Наразі немає нових запитів.</b>', parse_mode='HTML')

        return

    locations_dict = await location_db.get_locations_dict()

    for b in bookings:

        loc_name = locations_dict.get(b['location_id'], {}).get('name', '—')

        order_id = b.get('order_id') or str(b['_id'])

        t = f"📥 <b>НОВИЙ ЗАПИТ</b>\n\n👤 <b>Клієнт:</b> {b['fullname']}\n📞 <code>{b['phone']}</code>\n🏛 <b>Заклад:</b> {loc_name}\n🕔 <b>Час:</b> {b['date_time']}\n👥 <b>Гостей:</b> {b['people_count']}\n🥘 <b>Замовлення:</b> {b['cart']}"

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

    role = await get_user_role(callback.from_user.id)

    if role in ('super', 'boss', 'owner', 'developer'):
        locs = None
    elif role == 'delivery_manager':
        locs = ['NP']
    else:
        shift_loc = await admin_db.is_on_shift(callback.from_user.id)
        if isinstance(shift_loc, str) and shift_loc not in ("True", "1", "False", "0"):
            locs = [shift_loc]
        else:
            locs = await admin_db.get_locations_for_admin(callback.from_user.id) or None

    bookings = await active_bookings_db.get_active_bookings(locs)

    if not bookings:

        await callback.answer('Немає активних броней.')

        return

    await safe_edit_message(callback.message, '📅 <b>АКТИВНІ БРОНІ:</b>\nНатисніть для завершення:', reply_markup=akb.get_active_bookings_list_kb(bookings), parse_mode='HTML')

@admin_router.callback_query(F.data == 'active_orders')

async def list_active_orders(callback: CallbackQuery):

    role = await get_user_role(callback.from_user.id)

    if role in ('super', 'boss', 'owner', 'developer'):
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

@admin_router.message(F.text == '📋 МЕНЮ')

async def show_menu_panel(message: Message, state: FSMContext):

    if not await admin_db.is_admin(message.from_user.id): return

    if await get_user_role(message.from_user.id) not in ('boss', 'owner', 'developer'): return

    await state.clear()

    await message.answer('📋 <b>КЕРУВАННЯ МЕНЮ</b>', reply_markup=akb.get_menu_manage_kb(), parse_mode='HTML')

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

    is_privileged = role in ('super', 'boss', 'owner', 'developer')

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

@admin_router.callback_query(F.data == 'locs_back')

async def back_to_locs_manage(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    await safe_edit_message(callback.message, '📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ</b>', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'menu_back')

async def back_to_menu_manage(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    await safe_edit_message(callback.message, '📋 <b>КЕРУВАННЯ МЕНЮ</b>', reply_markup=akb.get_menu_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'beans_back')

async def back_to_beans_manage(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    await safe_edit_message(callback.message, '☕ <b>КЕРУВАННЯ ЗЕРНОМ</b>', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'adm_back_to_manage')

async def adm_back_manage(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    role = await get_user_role(callback.from_user.id)

    is_privileged = role in ('super', 'boss', 'owner', 'developer')

    await safe_edit_message(callback.message, '👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>', reply_markup=akb.get_admin_management_kb(is_privileged), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('adm2_confirm_'))

async def confirm_order_cb(callback: CallbackQuery, bot: Bot):

    oid = callback.data.replace('adm2_confirm_', '')

    order = await orders_db.get_order_by_id(oid)

    if not order:

        await callback.answer('Замовлення не знайдено.')

        return

    await orders_db.update_status(oid, 'confirmed')

    if order.get('order_type') == 'booking':

        await active_bookings_db.add_booking(oid, order['fullname'], order['location_id'], order['date_time'], order['people_count'])

        text = '✅ <b>ВАШЕ БРОНЮВАННЯ ПІДТВЕРДЖЕНО!</b>\n\nЧекаємо на вас у Medelin! ☕'

    else:

        await active_orders_db.add_order(oid, order['fullname'], order['location_id'], order['order_type'], order['cart'])

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

    await fade_out_message(callback.message, f'❌ <b>ВІДХИЛЕНО #{oid[-6:]}</b>')

    await callback.answer('Відхилено.')

@admin_router.callback_query(F.data.startswith('adm_msg_'))

async def admin_msg_start(callback: CallbackQuery, state: FSMContext):

    parts = callback.data.split('_')

    uid = parts[2]

    oid = parts[3]

    await state.update_data(msg_target_uid=uid, msg_target_oid=oid)

    await state.set_state(AdminStates.messaging_guest)

    await callback.message.answer('📝 Введіть текст повідомлення для гостя:')

    await callback.answer()

@admin_router.message(AdminStates.messaging_guest)

async def admin_msg_send(message: Message, state: FSMContext, bot: Bot):

    if await restart_fsm_on_command(message, state): return

    data = await state.get_data()

    uid = data.get('msg_target_uid')

    oid = data.get('msg_target_oid')

    order = await orders_db.get_order_by_id(oid) if oid != 'none' else None

    text_html = f'📩 <b>ПОВІДОМЛЕННЯ ВІД АДМІНІСТРАЦІЇ</b>\n\n{message.text}'

    if order:

        res = await deliver_guest_message(bot, order, text_html, message.text, reply_callback_data=f'adm_msg_{message.from_user.id}_{oid}')

        if res == 'telegram': await message.answer('✅ Надіслано в Telegram.')

        elif res == 'site': await message.answer('✅ Надіслано на сайт.')

        else: await message.answer('❌ Помилка.')

    elif uid and uid != 'none' and uid != 'None':

        try:

            await bot.send_message(int(uid), text_html, parse_mode='HTML')

            await message.answer('✅ Надіслано в Telegram.')

        except: await message.answer('❌ Не вдалося.')

    await state.clear()

@admin_router.callback_query(F.data == 'adm_add_new')

async def adm_add_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(AdminStates.adding_admin_id)

    help_text = (

        "🆔 <b>ВВЕДІТЬ ДАНІ НОВОГО СПІВРОБІТНИКА:</b>\n\n"

        "Ви можете ввести:\n"

        "1. <b>Telegram ID</b> (н-р: <code>12345678</code>)\n"

        "2. <b>Username</b> (н-р: <code>@username</code>)\n"

        "3. <b>Номер телефону</b> (н-р: <code>+380...</code>)\n\n"

        "🔍 <b>Де взяти Telegram ID?</b>\n"

        "• Скористайтеся ботом @userinfobot або @getmyid_bot\n"

        "• Або попросіть людину написати будь-що сюди — бот автоматично покаже її ID (якщо вона ще не адмін).\n\n"

        "<i>Користувач обов'язково має хоча б раз натиснути /start у цьому боті!</i>"

    )

    await callback.message.answer(help_text, reply_markup=akb.get_admin_management_kb(True), parse_mode='HTML')

    await callback.answer()

@admin_router.message(AdminStates.adding_admin_id)

async def adm_add_identity(message: Message, state: FSMContext):

    val = message.text.strip()

    target_uid = None

    target_username = "N/A"

    if val.isdigit():

        target_uid = int(val)

    elif val.startswith('@'):

        u = await user_db.get_user_by_username(val.replace('@', ''))

        if u: target_uid, target_username = int(u[0]), val

        else:

            await message.answer("❌ Користувача не знайдено в базі. Він має написати боту /start.")

            return

    elif val.startswith('+') or (val.startswith('380') and len(val) == 12):

        phone = normalize_phone(val)

        u = await user_db.get_user_by_phone(phone)

        if u: target_uid, target_username = int(u[0]), (f"@{u[1]}" if u[1] else "N/A")

        else:

            await message.answer("❌ Користувача не знайдено в базі по телефону.")

            return

    else:

        await message.answer("❌ Невірний формат.")

        return

    await state.update_data(new_adm_id=target_uid, new_adm_username=target_username)

    await message.answer(f"👤 Знайдено користувача: <code>{target_uid}</code>\nВведіть його <b>Ім'я для відображення</b>:", parse_mode='HTML')

    await state.set_state(AdminStates.adding_admin_name)

@admin_router.message(AdminStates.adding_admin_name)

async def adm_add_name(message: Message, state: FSMContext):

    await state.update_data(new_adm_name=message.text)

    caller_role = await get_user_role(message.from_user.id)

    await message.answer("🎭 Оберіть роль співробітника:", reply_markup=akb.get_admin_roles_kb(caller_role))

    await state.set_state(AdminStates.adding_admin_role)

@admin_router.callback_query(F.data.startswith('set_role_'), AdminStates.adding_admin_role)

async def adm_add_role(callback: CallbackQuery, state: FSMContext):

    role = callback.data.replace('set_role_', '')

    await state.update_data(new_adm_role=role, selected_loc_ids=[], is_all_locs=False)
    role_name = akb.ROLE_NAMES.get(role, role).upper()

    if role in ('developer', 'owner', 'boss', 'super', 'delivery_manager'):

        data = await state.get_data()

        await admin_db.add_admin(data['new_adm_id'], data.get('new_adm_username', 'N/A'), data['new_adm_name'], callback.from_user.id, role, locations=[])

        await safe_edit_message(callback.message, f"✅ <b>{data['new_adm_name']}</b> додано як <b>{role_name}</b> з повним доступом!", reply_markup=akb.get_admin_management_kb(True), parse_mode='HTML')

        await state.clear()

        await callback.answer()

        return

    all_l = await location_db.get_all_locations()

    await safe_edit_message(callback.message, f"✅ Роль <b>{role_name}</b> обрано.\n\nТепер оберіть локації, до яких співробітник матиме доступ:", reply_markup=akb.get_locations_selection_kb(all_l, [], False), parse_mode='HTML')

    await state.set_state(AdminStates.adding_admin_location)

    await callback.answer()

@admin_router.callback_query(F.data.startswith('adm_loc_toggle_'), AdminStates.adding_admin_location)

async def adm_add_loc_toggle(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    selected = data.get('selected_loc_ids', [])

    is_all = data.get('is_all_locs', False)

    toggle = callback.data.replace('adm_loc_toggle_', '')

    if toggle == 'all':

        is_all = not is_all

    else:

        if toggle in selected:

            selected.remove(toggle)

        else:

            selected.append(toggle)

            is_all = False

    await state.update_data(selected_loc_ids=selected, is_all_locs=is_all)

    all_l = await location_db.get_all_locations()

    await safe_edit_message(callback.message, callback.message.text, reply_markup=akb.get_locations_selection_kb(all_l, selected, is_all), parse_mode='HTML')

    await callback.answer()

@admin_router.callback_query(F.data == 'adm_loc_confirm', AdminStates.adding_admin_location)

async def adm_add_loc_confirm(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    locs = [] if data.get('is_all_locs') else data.get('selected_loc_ids', [])

    await admin_db.add_admin(data['new_adm_id'], data.get('new_adm_username', 'N/A'), data['new_adm_name'], callback.from_user.id, data['new_adm_role'], locations=locs)

    await safe_edit_message(callback.message, f"✅ <b>{data['new_adm_name']}</b> додано!", reply_markup=akb.get_admin_management_kb(True), parse_mode='HTML')

    await state.clear()

    await callback.answer()

@admin_router.callback_query(F.data == 'adm_list')

async def adm_list(callback: CallbackQuery):

    admins = await admin_db.get_admins_with_locations()

    text = "👥 <b>КОМАНДА MEDELIN:</b>\n\n"

    for aid, user, name, role, on_shift, notif, locs in admins:
        role_name = akb.ROLE_NAMES.get(role, role)
        text += f"{'🟢' if on_shift else '🔴'} <b>{name}</b> (@{user or '—'})\nРоль: {role_name} | Лок: {', '.join(locs) if locs else 'Усі'}\n\n"

    await safe_edit_message(callback.message, text, reply_markup=akb.get_admin_management_kb(True), parse_mode='HTML')

@admin_router.callback_query(F.data == 'adm_remove')

async def adm_remove_list(callback: CallbackQuery):

    caller_role = await get_user_role(callback.from_user.id)

    all_admins = await admin_db.get_admins_basic()

    removable = []

    for uid, username, display_name, role in all_admins:

        if can_manage(caller_role, role) and int(uid) != int(callback.from_user.id):

            removable.append((uid, username, display_name, role))

    if not removable:

        await callback.answer("У вас немає прав на видалення будь-кого з команди.", show_alert=True)

        return

    await safe_edit_message(callback.message, "🗑 Оберіть кого видалити:", reply_markup=akb.get_admins_to_remove_kb(removable), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('adm_delete_'))

async def adm_remove_confirm(callback: CallbackQuery):

    uid = int(callback.data.replace('adm_delete_', ''))

    if str(uid) in BOSS_IDS:

        await callback.answer("❌ Неможливо видалити власника!", show_alert=True)

        return

    caller_role = await get_user_role(callback.from_user.id)

    target_admin = await admin_db.get_admin_by_id(uid)

    if not target_admin or not can_manage(caller_role, target_admin.get('role', 'admin')):

        await callback.answer("❌ Недостатньо прав для видалення цього співробітника!", show_alert=True)

        return

    await admin_db.remove_admin(uid)

    await callback.answer("Видалено!")

    await adm_remove_list(callback)

@admin_router.callback_query(F.data == 'menu_cats')

async def menu_cats_list(callback: CallbackQuery):

    cats = await menu_db.get_categories()

    text = "📚 <b>КАТЕГОРІЇ МЕНЮ:</b>\n\n" + "\n".join([f"▫️ {c}" for c in cats])

    await safe_edit_message(callback.message, text, reply_markup=akb.get_menu_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'menu_del')

async def menu_del_start(callback: CallbackQuery):

    cats = await menu_db.get_categories()

    await safe_edit_message(callback.message, '🗑 Оберіть категорію для видалення позиції:', reply_markup=akb.get_category_selection_kb(cats, 'm_del_cat'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('m_del_cat_'))

async def menu_del_items(callback: CallbackQuery):

    cat_id = callback.data.replace('m_del_cat_', '')

    items = await menu_db.get_items_by_category_id(cat_id)

    if not items:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '🗑 Оберіть позицію для ВИДАЛЕННЯ:', reply_markup=akb.get_items_in_category_kb([(i['id'], i['name']) for i in items], 'm_del_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('m_del_it_'))

async def menu_del_confirm(callback: CallbackQuery):

    iid = callback.data.replace('m_del_it_', '')

    await menu_db.delete_item(iid)

    await public_data_cache.refresh('menu')

    await callback.answer('Видалено!')

    await menu_del_start(callback)

@admin_router.callback_query(F.data == 'menu_add')

async def menu_add_start(callback: CallbackQuery, state: FSMContext):

    cats = await menu_db.get_categories()

    await safe_edit_message(callback.message, '📁 Оберіть категорію:', reply_markup=akb.get_category_selection_kb(cats, 'm_add_cat', include_new=True), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('m_add_cat_'))

async def menu_add_cat_chosen(callback: CallbackQuery, state: FSMContext):

    cat_id = callback.data.replace('m_add_cat_', '')

    if cat_id == 'NEW':

        await callback.message.answer('📝 Введіть назву нової категорії:')

        await state.set_state(MenuStates.waiting_new_category)

    else:

        cats = await menu_db.get_categories()

        from app.keyboards.user_keyboards import cat_key

        cat_name = next((c for c in cats if cat_key(str(c)) == cat_id), cat_id)

        await state.update_data(category=cat_name)

        await callback.message.answer('📝 Введіть назву позиції:')

        await state.set_state(MenuStates.waiting_name)

    await callback.answer()

@admin_router.message(MenuStates.waiting_new_category)

async def menu_add_new_cat(message: Message, state: FSMContext):

    await state.update_data(category=message.text)

    await message.answer('📝 Введіть назву позиції:')

    await state.set_state(MenuStates.waiting_name)

@admin_router.message(MenuStates.waiting_name)

async def menu_add_name(message: Message, state: FSMContext):

    await state.update_data(name=message.text)

    await message.answer('💰 Введіть ціну (грн):')

    await state.set_state(MenuStates.waiting_price)

@admin_router.message(MenuStates.waiting_price)

async def menu_add_price(message: Message, state: FSMContext):

    await state.update_data(price=message.text)

    await message.answer('📜 Введіть опис (або "ні"):')

    await state.set_state(MenuStates.waiting_desc)

@admin_router.message(MenuStates.waiting_desc)

async def menu_add_desc(message: Message, state: FSMContext):

    val = (message.text or '').strip()

    await state.update_data(description='' if val.lower() in ('ні', 'немає', '-') else val)

    await message.answer('⚖️ Обʼєм/Вага (н-р: 250 мл, або "ні"):')

    await state.set_state(MenuStates.waiting_volume)

@admin_router.message(MenuStates.waiting_volume)

async def menu_add_volume(message: Message, state: FSMContext):

    val = (message.text or '').strip()

    await state.update_data(volume='' if val.lower() in ('ні', 'немає', '-') else val)

    await message.answer('🖼 Надішліть фото (файл або посилання) або "ні":')

    await state.set_state(MenuStates.waiting_image)

@admin_router.message(MenuStates.waiting_image, F.photo | F.text)

async def menu_add_image(message: Message, state: FSMContext, bot: Bot):

    if await restart_fsm_on_command(message, state): return

    img = ''

    if not (message.text and message.text.lower() in ('ні', 'немає', '-')):

        from app.utils.photo_utils import process_photo

        img = await process_photo(message, bot)

    await state.update_data(image_url=img)

    data = await state.get_data()

    text = f"🔍 <b>ПЕРЕВІРКА:</b>\n\n📁 {data['category']}\n✨ {data['name']}\n💰 {data['price']} грн"

    await message.answer(text, reply_markup=akb.get_yes_no_kb('m_save', 'menu_back'), parse_mode='HTML')

@admin_router.callback_query(F.data == 'm_save')

async def menu_add_save(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    if data.get('bean_mode'):

        await coffee_beans_db.add_bean(data['name'], data['price'], data.get('description', ''), 'Сорт', 'Смак', 'Обсмажка', image_url=data.get('image_url', ''))

        await safe_edit_message(callback.message, '✅ ЗЕРНО ДОДАНО!', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

    else:

        await menu_db.add_item(data['category'], data['name'], data['price'], data.get('description', ''), data.get('volume', ''), 0, data.get('image_url', ''))

        await public_data_cache.refresh('menu')

        await safe_edit_message(callback.message, '✅ СТРАВУ ДОДАНО!', reply_markup=akb.get_menu_manage_kb(), parse_mode='HTML')

    await state.clear()

@admin_router.callback_query(F.data == 'menu_edit')

async def menu_edit_start(callback: CallbackQuery):

    cats = await menu_db.get_categories()

    await safe_edit_message(callback.message, '✏️ Оберіть категорію:', reply_markup=akb.get_category_selection_kb(cats, 'm_edt_cat'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('m_edt_cat_'))

async def menu_edit_items(callback: CallbackQuery):

    cat_id = callback.data.replace('m_edt_cat_', '')

    items = await menu_db.get_items_by_category_id(cat_id)

    if not items:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '✏️ Оберіть позицію:', reply_markup=akb.get_items_in_category_kb([(i['id'], i['name']) for i in items], 'm_edt_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('m_edt_it_'))

async def menu_edit_fields(callback: CallbackQuery, state: FSMContext):

    iid = callback.data.replace('m_edt_it_', '')

    item = await menu_db.get_item_by_id(iid)

    await state.update_data(edit_id=iid)

    kb_edt = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text='Назву', callback_data='ed_m_name'), InlineKeyboardButton(text='Ціну', callback_data='ed_m_price')],

        [InlineKeyboardButton(text='Опис', callback_data='ed_m_description'), InlineKeyboardButton(text='🖼 Фото', callback_data='ed_m_image_url')],

        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='menu_edit')]

    ])

    await safe_edit_message(callback.message, f"Редагування <b>{item[2]}</b>", reply_markup=kb_edt, parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('ed_m_'))

async def menu_edit_field_start(callback: CallbackQuery, state: FSMContext):

    field = callback.data.replace('ed_m_', '')

    await state.update_data(edit_field=field)

    await callback.message.answer('✏️ Введіть нове значення:')

    await state.set_state(MenuStates.edit_waiting_value)

    await callback.answer()

@admin_router.callback_query(F.data == 'beans_add')

async def beans_add_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(MenuStates.waiting_name)

    await state.update_data(bean_mode=True, category="Кава в зернах")

    await callback.message.answer('📝 Введіть назву сорту (н-р: Brazil Santos):')

    await callback.answer()

@admin_router.callback_query(F.data == 'beans_list')

async def beans_list(callback: CallbackQuery):

    beans = await coffee_beans_db.get_all_beans()

    if not beans:

        await callback.answer('Порожньо.')

        return

    text = '☕ <b>СПИСОК ЗЕРНА:</b>\n\n' + '\n'.join([f"▫️ {b['name']} - {b['price_250']} грн" for b in beans])

    await safe_edit_message(callback.message, text, reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'beans_del')

async def beans_del_start(callback: CallbackQuery):

    beans = await coffee_beans_db.get_all_beans()

    if not beans:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '🗑 Оберіть зерно для ВИДАЛЕННЯ:', reply_markup=akb.get_beans_list_kb(beans, 'beans_del_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('beans_del_it_'))

async def beans_del_confirm(callback: CallbackQuery):

    bid = callback.data.replace('beans_del_it_', '')

    await coffee_beans_db.delete_bean(bid)

    await callback.answer('Видалено!')

    await beans_del_start(callback)

@admin_router.callback_query(F.data == 'beans_edit')

async def beans_edit_start(callback: CallbackQuery):

    beans = await coffee_beans_db.get_all_beans()

    if not beans:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '✏️ Оберіть зерно для редагування:', reply_markup=akb.get_beans_list_kb(beans, 'beans_edt_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('beans_edt_it_'))

async def beans_edit_sel(callback: CallbackQuery, state: FSMContext):

    bid = callback.data.replace('beans_edt_it_', '')

    bean = await coffee_beans_db.get_bean_by_id(bid)

    await state.update_data(edit_bean_id=bid)

    kb_edit = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text='Назву', callback_data='ed_b_name'), InlineKeyboardButton(text='Ціну 250г', callback_data='ed_b_price_250')],

        [InlineKeyboardButton(text='Опис', callback_data='ed_b_description'), InlineKeyboardButton(text='🖼 Фото', callback_data='ed_b_image_url')],

        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='beans_edit')]

    ])

    await safe_edit_message(callback.message, f"Редагування <b>{bean['name']}</b>", reply_markup=kb_edit, parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('ed_b_'))

async def beans_edit_field_start(callback: CallbackQuery, state: FSMContext):

    field = callback.data.replace('ed_b_', '')

    await state.update_data(edit_field=field, bean_edit_mode=True)

    await callback.message.answer('✏️ Введіть нове значення:')

    await state.set_state(MenuStates.edit_waiting_value)

    await callback.answer()

@admin_router.message(MenuStates.edit_waiting_value, F.photo | F.text)

async def admin_edit_value_save(message: Message, state: FSMContext, bot: Bot):

    if await restart_fsm_on_command(message, state): return

    data = await state.get_data()

    field, is_bean = data.get('edit_field'), (data.get('bean_edit_mode') or data.get('bean_mode'))

    val = (await process_photo(message, bot)) if field == 'image_url' else (message.text or '').strip()

    if is_bean:

        bid = data.get('edit_bean_id')

        if bid:

            upd = {field: val}

            if field == 'price_250':

                try:

                    p = coffee_beans_db.calculate_prices(float(val))

                    upd = {'price_250': p['250'], 'price_500': p['500'], 'price_1000': p['1000']}

                except: pass

            await coffee_beans_db.update_bean(bid, upd)

            await message.answer('✅ Оновлено зерно!', reply_markup=akb.get_beans_manage_kb())

    else:

        iid = data.get('edit_id')

        await menu_db.update_item(iid, {field: val})

        await public_data_cache.refresh('menu')

        await message.answer('✅ Оновлено страву!', reply_markup=akb.get_menu_manage_kb())

    await state.clear()

async def process_photo(message: Message, bot: Bot) -> str:

    from app.utils.photo_utils import process_photo as pp

    return await process_photo(message, bot)

@admin_router.callback_query(F.data == 'soc_list')

async def list_socials(callback: CallbackQuery):

    socs = await socials_db.get_all_socials()

    text = '📱 <b>СОЦМЕРЕЖІ:</b>\n\n' + '\n'.join([f"▫️ {s['name']}: {s['url']}" for s in socs]) if socs else "Порожньо."

    await safe_edit_message(callback.message, text, reply_markup=akb.get_socials_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'soc_add')

async def add_social_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(SocialStates.waiting_name)

    await callback.message.answer('✏️ Назва соцмережі (н-р: Instagram):')

    await callback.answer()

@admin_router.message(SocialStates.waiting_name)

async def add_social_name(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(name=message.text)

    await message.answer('🔗 URL посилання:')

    await state.set_state(SocialStates.waiting_url)

@admin_router.message(SocialStates.waiting_url)

async def add_social_url(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    data = await state.get_data()

    await socials_db.add_social(data['name'], message.text)

    await public_data_cache.refresh('socials')

    await message.answer('✅ Додано!', reply_markup=akb.get_socials_manage_kb(), parse_mode='HTML')

    await state.clear()

@admin_router.callback_query(F.data == 'soc_del')

async def del_social_start(callback: CallbackQuery):

    socs = await socials_db.get_all_socials()

    if not socs:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '🗑 Оберіть для ВИДАЛЕННЯ:', reply_markup=akb.get_socials_list_kb(socs, 'soc_del_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('soc_del_it_'))

async def del_social_confirm(callback: CallbackQuery):

    sid = callback.data.replace('soc_del_it_', '')

    await socials_db.delete_social(sid)

    await public_data_cache.refresh('socials')

    await callback.answer('Видалено!')

    await del_social_start(callback)

@admin_router.callback_query(F.data == 'soc_back')

async def back_to_soc_manage(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    await safe_edit_message(callback.message, '📱 <b>КЕРУВАННЯ СОЦМЕРЕЖАМИ</b>', reply_markup=akb.get_socials_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'locs_list')

async def list_locations(callback: CallbackQuery):

    locs = await location_db.get_all_locations()

    text = '📍 <b>СПИСОК ЛОКАЦІЙ:</b>\n\n' + '\n'.join([f"▫️ {l['name']} ({l['address']})" for l in locs]) if locs else "Порожньо."

    await safe_edit_message(callback.message, text, reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'locs_add')

async def add_location_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(LocationStates.waiting_name)

    await callback.message.answer('✏️ Назва локації (н-р: Medelin на Закарпатській):')

    await callback.answer()

@admin_router.message(LocationStates.waiting_name)

async def add_loc_name(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(name=message.text)

    await message.answer('📍 Адреса:')

    await state.set_state(LocationStates.waiting_address)

@admin_router.message(LocationStates.waiting_address)

async def add_loc_address(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(address=message.text)

    await message.answer('🕒 Графік роботи:')

    await state.set_state(LocationStates.waiting_schedule)

@admin_router.message(LocationStates.waiting_schedule)

async def add_loc_schedule(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(schedule=message.text)

    await message.answer('📞 Телефон:')

    await state.set_state(LocationStates.waiting_phone)

@admin_router.message(LocationStates.waiting_phone)

async def add_loc_phone(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(phone=message.text)

    await message.answer('📧 Email:')

    await state.set_state(LocationStates.waiting_email)

@admin_router.message(LocationStates.waiting_email)

async def add_loc_email(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(email=message.text)

    await message.answer('🗺 Google Maps URL:')

    await state.set_state(LocationStates.waiting_maps_url)

@admin_router.message(LocationStates.waiting_maps_url)

async def add_loc_maps(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(google_maps_url=message.text)

    await message.answer('✨ Атмосфера:')

    await state.set_state(LocationStates.waiting_atmosphere)

@admin_router.message(LocationStates.waiting_atmosphere)

async def add_loc_atmosphere(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(atmosphere=message.text)

    await message.answer('🛋 Зручності (через кому):')

    await state.set_state(LocationStates.waiting_amenities)

@admin_router.message(LocationStates.waiting_amenities)

async def add_loc_amenities(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    await state.update_data(amenities=[a.strip() for a in message.text.split(',') if a.strip()])

    await message.answer('🖼 Фото (файл або URL):')

    await state.set_state(LocationStates.waiting_image)

@admin_router.message(LocationStates.waiting_image, F.photo | F.text)

async def add_loc_image(message: Message, state: FSMContext, bot: Bot):

    if await restart_fsm_on_command(message, state): return

    img = await process_photo(message, bot)

    await state.update_data(image_url=img)

    await message.answer('🔢 Кількість столиків:')

    await state.set_state(LocationStates.waiting_max_tables)

@admin_router.message(LocationStates.waiting_max_tables)

async def add_loc_tables(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    try:

        val = int(message.text)

        await state.update_data(max_tables=val)

        data = await state.get_data()

        text = f"🔍 <b>ПЕРЕВІРКА:</b>\n\n📍 {data['name']}\n🏠 {data['address']}"

        await message.answer(text, reply_markup=akb.get_yes_no_kb('loc_save', 'locs_back'), parse_mode='HTML')

    except: await message.answer('❌ Введіть число.')

@admin_router.callback_query(F.data == 'loc_save')

async def save_new_location(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    coords = extract_coords_from_maps(data.get('google_maps_url', ''))

    await location_db.add_location(name=data['name'], address=data['address'], schedule=data['schedule'], phone=data['phone'], email=data['email'], google_maps_url=data['google_maps_url'], max_tables=data['max_tables'], coordinates={'lat': coords[0], 'lon': coords[1]} if coords else None, image_url=data.get('image_url', ''), amenities=data.get('amenities', []), atmosphere=data.get('atmosphere', ''))

    await public_data_cache.refresh('locations')

    await safe_edit_message(callback.message, '✅ ДОДАНО!', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

    await state.clear()

@admin_router.callback_query(F.data == 'locs_edit')

async def edit_locations_start(callback: CallbackQuery):

    locs = await location_db.get_all_locations()

    if not locs:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '✏️ Редагування локації:', reply_markup=akb.get_locations_list_kb(locs, 'locs_edt_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('locs_edt_it_'))

async def edit_location_sel(callback: CallbackQuery, state: FSMContext):

    lid = callback.data.replace('locs_edt_it_', '')

    loc = await location_db.get_location_by_id(lid)

    await state.update_data(edit_id=lid)

    kb_edit = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Назву', callback_data='ed_l_name'), InlineKeyboardButton(text='Адресу', callback_data='ed_l_address')], [InlineKeyboardButton(text='Графік', callback_data='ed_l_schedule')], [InlineKeyboardButton(text='🖼 Фото', callback_data='ed_l_image_url'), InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='locs_edit')]])

    await safe_edit_message(callback.message, f"Редагування <b>{loc['name']}</b>", reply_markup=kb_edit, parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('ed_l_'))

async def edit_location_field_start(callback: CallbackQuery, state: FSMContext):

    field = callback.data.replace('ed_l_', '')

    await state.update_data(edit_field=field)

    await callback.message.answer('✏️ Введіть нове значення:')

    await state.set_state(LocationStates.edit_value)

    await callback.answer()

@admin_router.message(LocationStates.edit_value, F.photo | F.text)

async def edit_location_value_save(message: Message, state: FSMContext, bot: Bot):

    if await restart_fsm_on_command(message, state): return

    data = await state.get_data()

    field = data.get('edit_field')

    val = (await process_photo(message, bot)) if field == 'image_url' else (message.text or '').strip()

    upd = {field: val}

    if field == 'google_maps_url':

        c = extract_coords_from_maps(val)

        if c: upd['coordinates'] = {'lat': c[0], 'lon': c[1]}

    await location_db.update_location(data.get('edit_id'), upd)

    await public_data_cache.refresh('locations')

    await message.answer(f'✅ Оновлено!', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

    await state.clear()
