
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

    messaging_guest = State()

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
    return (role or 'admin').strip().lower()

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

        if reply_callback_data:

            reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='💬 ВІДПОВІСТИ', callback_data=reply_callback_data)]])

        telegram_ok = False
        try:
            await bot.send_message(telegram_target, text_html, parse_mode='HTML', reply_markup=reply_markup)
            telegram_ok = True
        except:
            telegram_ok = False

    phone = order.get('phone')
    order_id = order.get('order_id') or order.get('_id')

    # Статусні повідомлення (Прийнято/Відхилено) не додаємо в базу чатів,
    # щоб вони не створювали "пустих" діалогів в адмін-панелі.
    # Залишаємо лише відправку в Telegram клієнту.
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
        # 1. Refresh all cache
        await public_data_cache.warm_all()
        
        # 2. Try to run git commands
        from pathlib import Path
        import asyncio
        
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        
        # Перевіряємо чи є гіт
        try:
            proc_git = await asyncio.create_subprocess_exec('git', '--version', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc_git.wait()
        except Exception:
            await message.answer('❌ <b>ПОМИЛКА:</b> Git не встановлений на сервері або недоступний. Зверніться до розробника.', parse_mode='HTML')
            return

        # Виконуємо синхронізацію
        commands = [
            ['git', 'add', 'MedelinSite/cache/*.json'],
            ['git', 'commit', '-m', f"Manual sync from bot by {message.from_user.id}"],
            ['git', 'push', 'origin', 'release']
        ]
        
        results = []
        for cmd in commands:
            process = await asyncio.create_subprocess_exec(
                *cmd, 
                cwd=str(root_dir), 
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            results.append(f"<code>{' '.join(cmd)}</code>: {'✅' if process.returncode == 0 else '⚠️'}")
            if process.returncode != 0 and 'push' in cmd:
                 results.append(f"<i>Error: {stderr.decode().strip()}</i>")

        await message.answer('✅ <b>СИНХРОНІЗАЦІЮ ЗАВЕРШЕНО!</b>\n\n' + '\n'.join(results), parse_mode='HTML')
        
    except Exception as e:
        await message.answer(f'❌ <b>КРИТИЧНА ПОМИЛКА:</b>\n<code>{str(e)}</code>', parse_mode='HTML')

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

@admin_router.callback_query(F.data.startswith('admin_auth_confirm_'))
async def admin_auth_confirm(callback: CallbackQuery):
    user_id = int(callback.data.split('_')[-1])
    await admin_db.confirm_auth_request(user_id)
    await callback.message.edit_text("✅ Вхід в адмін-панель підтверджено.")
    await callback.answer("Підтверджено")

@admin_router.callback_query(F.data.startswith('admin_auth_reject_'))
async def admin_auth_reject(callback: CallbackQuery):
    await callback.message.edit_text("❌ Вхід відхилено.")
    await callback.answer("Відхилено")

@admin_router.message(F.text == '🟢 ПОЧАТИ ЗМІНУ')
async def start_shift(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    role = await get_user_role(message.from_user.id)
    if role not in ('boss', 'owner', 'developer'): return
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
        # Delivery manager sees orders with specific types or location
        all_orders = await orders_db.get_new_orders()
        bookings = [o for o in all_orders if o.get('order_type') in ('nova_poshta', 'beans_delivery') or o.get('location_id') == 'NP']
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

        if b.get('order_type') in ('nova_poshta', 'beans_delivery') or b.get('location_id') == 'NP':
            loc_name = 'Нова Пошта'
            wishes = b.get('wishes') or ''
            if 'НП:' in wishes:
                loc_name = f"Нова Пошта — {wishes.split('НП:', 1)[1].split('|', 1)[0].strip()}"
        else:
            loc_name = locations_dict.get(b['location_id'], {}).get('name', '—')

        order_id = b.get('order_id') or str(b['_id'])

        t = f"📥 <b>НОВИЙ ЗАПИТ</b>\n\n👤 <b>Клієнт:</b> {b['fullname']}\n📞 <code>{b['phone']}</code>\n🏛 <b>Заклад:</b> {loc_name}\n"
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

@admin_router.message(F.text == '💬 ПІДТРИМКА')
async def show_support_panel(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) not in ('super', 'boss', 'owner', 'developer'): return
    
    await state.clear()
    chats = await guest_messages_db.get_unique_chats()
    if not chats:
        await message.answer('📭 <b>Наразі немає повідомлень у підтримці.</b>', parse_mode='HTML')
        return
        
    await message.answer('💬 <b>ПІДТРИМКА / ЧАТИ З КОРИСТУВАЧАМИ</b>\nОберіть чат для перегляду:', reply_markup=akb.get_support_chats_kb(chats), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('support_chat_'))
async def view_support_chat(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    phone = parts[2]
    oid = parts[3]
    
    messages = await guest_messages_db.get_messages(phone, order_id=None if oid == 'none' else oid)
    await guest_messages_db.mark_messages_read(phone, order_id=None if oid == 'none' else oid)
    
    text = f"💬 <b>ЧАТ: {phone}</b>\n"
    if oid != 'none':
        text += f"📦 Замовлення: #{oid[-6:]}\n"
    text += "────────────────────\n"
    
    if not messages:
        text += "<i>Повідомлень немає або чат очищено.</i>"
    else:
        for m in messages:
            sender = "👤 Гість" if m['source'] == 'guest' else "👨‍💼 Адмін"
            time_str = m['created_at'].strftime('%d.%m %H:%M')
            text += f"<b>{sender}</b> ({time_str}):\n{m['text']}\n\n"

    # Знаходимо user_id по телефону
    user = await user_db.get_user_by_phone(phone)
    uid_str = str(user[0]) if user else "none"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💬 ВІДПОВІСТИ', callback_data=f'adm_msg_{uid_str}_{oid}')],
        [InlineKeyboardButton(text='🗑 ОЧИСТИТИ ЧАТ', callback_data=f'support_clear_{phone}_{oid}')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='adm_support_back')]
    ])

    await safe_edit_message(callback.message, text, reply_markup=markup, parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('support_clear_'))
async def clear_support_chat(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    phone = parts[2]
    oid = parts[3]

    await callback.answer("⏳ Очищення...")

    # Видалення з БД ТІЛЬКИ ЦЬОГО ЧАТУ
    from app.databases.mongo_client import get_db
    from app.utils.phone_utils import normalize_phone
    db = await get_db()
    
    # Створюємо фільтр чітко за телефоном та order_id
    query = {'phone_digits': normalize_phone(phone)}
    if oid != 'none':
        query['order_id'] = oid
    else:
        # Якщо oid немає, видаляємо лише ті, де order_id порожній
        query['order_id'] = {'$in': [None, 'none', '']}
        
    await db.guest_messages.delete_many(query)

    await callback.message.edit_text("✅ <b>ЧАТ ОЧИЩЕНО!</b>", parse_mode='HTML')
    import asyncio
    await asyncio.sleep(0.8)
    await back_to_support_list(callback, state)

@admin_router.callback_query(F.data == 'adm_support_back')
async def back_to_support_list(callback: CallbackQuery, state: FSMContext):
    chats = await guest_messages_db.get_unique_chats()
    await safe_edit_message(callback.message, '💬 <b>ПІДТРИМКА / ЧАТИ З КОРИСТУВАЧАМИ</b>\nОберіть чат для перегляду:', reply_markup=akb.get_support_chats_kb(chats), parse_mode='HTML')

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

        res = await deliver_guest_message(bot, order, text_html, message.text, reply_callback_data=f'guest_reply_to_admin_{message.from_user.id}_{oid}')

        if res in ('telegram', 'both'): await message.answer('✅ Надіслано в Telegram.')

        elif res == 'site': await message.answer('✅ Надіслано на сайт.')

        else: await message.answer('❌ Помилка.')

    elif uid and uid != 'none' and uid != 'None':

        try:
            # If the admin replies to a super chat message without an order (oid == none), send it back with a guest_reply_to_admin callback
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='💬 ВІДПОВІСТИ', callback_data=f'guest_reply_to_admin_{message.from_user.id}_none')]])
            await bot.send_message(int(uid), text_html, parse_mode='HTML', reply_markup=markup)

            await message.answer('✅ Надіслано в Telegram.')

        except Exception as e:
            from app.utils.admin_notifications import send_developer_error
            await send_developer_error(f"Error sending message to guest {uid}: {str(e)}")
            await message.answer('❌ Не вдалося.')

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
async def adm_remove_confirm_ask(callback: CallbackQuery):
    uid = int(callback.data.replace('adm_delete_', ''))
    if str(uid) in DEVELOPER_IDS:
        await callback.answer("❌ Неможливо видалити розробника!", show_alert=True)
        return
    admin = await admin_db.get_admin_by_id(uid)
    if not admin:
        await callback.answer("❌ Цього адміністратора вже видалено або не знайдено.", show_alert=True)
        await adm_remove_list(callback)
        return
    name = admin.get('display_name') or admin.get('username') or str(uid)
    await safe_edit_message(callback.message, f"❓ Ви впевнені, що хочете видалити <b>{name}</b> з команди?", reply_markup=akb.get_yes_no_kb(f'adm_del_yes_{uid}', 'adm_remove'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('adm_del_yes_'))
async def adm_remove_confirm_yes(callback: CallbackQuery):
    uid = int(callback.data.replace('adm_del_yes_', ''))
    caller_role = await get_user_role(callback.from_user.id)
    target_admin = await admin_db.get_admin_by_id(uid)
    if not target_admin:
        await callback.answer("❌ Адміністратора не знайдено.", show_alert=True)
        await adm_remove_list(callback)
        return
    if not can_manage(caller_role, target_admin.get('role', 'admin')):
        await callback.answer("❌ Недостатньо прав!", show_alert=True)
        return
    await admin_db.remove_admin(uid)
    await callback.answer("Видалено!", show_alert=True)
    await adm_remove_list(callback)



@admin_router.callback_query(F.data.startswith('beans_del_it_'))

async def beans_del_confirm_ask(callback: CallbackQuery):

    bid = callback.data.replace('beans_del_it_', '')

    bean = await coffee_beans_db.get_bean_by_id(bid)

    await safe_edit_message(callback.message, f"❓ Ви впевнені, що хочете видалити зерно <b>{bean['name']}</b>?", reply_markup=akb.get_yes_no_kb(f'beans_del_yes_{bid}', 'beans_del'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('beans_del_yes_'))

async def beans_del_confirm_yes(callback: CallbackQuery):

    bid = callback.data.replace('beans_del_yes_', '')

    await coffee_beans_db.delete_bean(bid)

    await callback.answer('Видалено!')

    await beans_del_start(callback)

@admin_router.callback_query(F.data == 'locs_del')

async def locs_del_start(callback: CallbackQuery):

    locs = await location_db.get_all_locations()

    if not locs:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '🗑 Оберіть локацію для ВИДАЛЕННЯ:', reply_markup=akb.get_locations_list_kb(locs, 'locs_del_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('locs_del_it_'))

async def locs_del_confirm_ask(callback: CallbackQuery):

    lid = callback.data.replace('locs_del_it_', '')

    loc = await location_db.get_location_by_id(lid)

    await safe_edit_message(callback.message, f"❓ Ви впевнені, що хочете видалити локацію <b>{loc['name']}</b>?", reply_markup=akb.get_yes_no_kb(f'locs_del_yes_{lid}', 'locs_del'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('locs_del_yes_'))

async def locs_del_confirm_yes(callback: CallbackQuery):

    lid = callback.data.replace('locs_del_yes_', '')

    await location_db.delete_location(lid)

    await callback.answer('Видалено!')

    await locs_del_start(callback)

@admin_router.callback_query(F.data == 'soc_edit')

async def edit_socials_start(callback: CallbackQuery):

    socs = await socials_db.get_all_socials()

    if not socs:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '✏️ Редагування соцмережі:', reply_markup=akb.get_socials_list_kb(socs, 'soc_edt_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('soc_edt_it_'))

async def edit_social_sel(callback: CallbackQuery, state: FSMContext):

    sid = callback.data.replace('soc_edt_it_', '')

    soc = await socials_db.get_social_by_id(sid)

    await state.update_data(edit_id=sid)

    kb_edit = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Назву', callback_data='ed_s_name'), InlineKeyboardButton(text='URL посилання', callback_data='ed_s_url')], [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='soc_edit')]])

    await safe_edit_message(callback.message, f"Редагування <b>{soc['name']}</b>", reply_markup=kb_edit, parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('ed_s_'))

async def edit_social_field_start(callback: CallbackQuery, state: FSMContext):

    field = callback.data.replace('ed_s_', '')

    await state.update_data(edit_field=field)

    await callback.message.answer('✏️ Введіть нове значення:')

    await state.set_state(SocialStates.edit_value)

    await callback.answer()

@admin_router.message(SocialStates.edit_value)

async def edit_social_value_save(message: Message, state: FSMContext):

    if await restart_fsm_on_command(message, state): return

    data = await state.get_data()

    field = data.get('edit_field')

    await socials_db.update_social(data.get('edit_id'), {field: message.text.strip()})

    await message.answer('✅ Оновлено!', reply_markup=akb.get_socials_manage_kb(), parse_mode='HTML')

    await state.clear()

@admin_router.message(BeanStates.waiting_name)

async def bean_add_name(message: Message, state: FSMContext):

    await state.update_data(name=message.text)

    await message.answer('💰 Введіть ціну за 250г (грн):')

    await state.set_state(BeanStates.waiting_price)

@admin_router.message(BeanStates.waiting_price)

async def bean_add_price(message: Message, state: FSMContext):

    text = (message.text or '').strip().replace(',', '.')

    try:

        price = float(text)

        if price < 0: raise ValueError

        await state.update_data(price=price)

        await message.answer('📜 Введіть опис (або "ні"):')

        await state.set_state(BeanStates.waiting_desc)

    except ValueError:

        await message.answer('❌ Будь ласка, введіть коректне число (ціну). Наприклад: 120 або 150.50')

@admin_router.message(BeanStates.waiting_desc)

async def bean_add_desc(message: Message, state: FSMContext):

    val = (message.text or '').strip()

    await state.update_data(description='' if val.lower() in ('ні', 'немає', '-') else val)

    await message.answer('⚖️ Обʼєм/Вага (н-р: 250 мл, або "ні"):')

    await state.set_state(BeanStates.waiting_volume)

@admin_router.message(BeanStates.waiting_volume)

async def bean_add_volume(message: Message, state: FSMContext):

    val = (message.text or '').strip()

    await state.update_data(volume='' if val.lower() in ('ні', 'немає', '-') else val)

    await message.answer('🖼 Надішліть фото (файл або посилання) або "ні":')

    await state.set_state(BeanStates.waiting_image)

@admin_router.message(BeanStates.waiting_image, F.photo | F.document | F.text)

async def bean_add_image(message: Message, state: FSMContext, bot: Bot):

    if await restart_fsm_on_command(message, state): return

    img = ''

    if not (message.text and message.text.lower() in ('ні', 'немає', '-')):

        img = await process_photo(message, bot)

    await state.update_data(image_url=img)

    data = await state.get_data()

    text = f"🔍 <b>ПЕРЕВІРКА:</b>\n\n📁 {data.get('category', 'Зерно')}\n✨ {data['name']}\n💰 {data['price']} грн"

    await message.answer(text, reply_markup=akb.get_yes_no_kb('m_save', 'beans_back'), parse_mode='HTML')

@admin_router.callback_query(F.data == 'm_save')

async def bean_add_save(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    await coffee_beans_db.add_bean(data['name'], data['price'], data.get('description', ''), '', '', '', image_url=data.get('image_url', ''), acidity=0, bitterness=0, body=0)

    await public_data_cache.refresh('coffee')

    await safe_edit_message(callback.message, '✅ ЗЕРНО ДОДАНО! Тепер ви можете доповнити деталі через редагування.', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

    await state.clear()

@admin_router.message(BeanStates.edit_waiting_value, F.photo | F.document | F.text)

async def bean_edit_value_save(message: Message, state: FSMContext, bot: Bot):

    if await restart_fsm_on_command(message, state): return

    data = await state.get_data()

    field = data.get('edit_field')

    val = (await process_photo(message, bot)) if field == 'image_url' else (message.text or '').strip()

    if not val and field != 'image_url':
        await message.answer('❌ Значення не може бути порожнім.')
        return

    bid = data.get('edit_bean_id')

    if bid:

        upd = {field: val}

        if field == 'price_250':

            try:

                val_f = float(val.replace(',', '.'))
                p = coffee_beans_db.calculate_prices(val_f)

                upd = {'price_250': p['250'], 'price_500': p['500'], 'price_1000': p['1000']}

            except ValueError:
                await message.answer('❌ Введіть коректне число для ціни.')
                return
        
        elif field in ('acidity', 'bitterness', 'body'):
            try: upd[field] = int(val)
            except ValueError:
                await message.answer('❌ Введіть ціле число (0-5).')
                return

        await coffee_beans_db.update_bean(bid, upd)

        await public_data_cache.refresh('coffee')

        await message.answer('✅ Оновлено зерно!', reply_markup=akb.get_beans_manage_kb())

    await state.clear()

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

    name = (data.get('name') or '').strip()
    url = (message.text or '').strip()

    def _guess_social_name(url_raw: str) -> str | None:
        u = (url_raw or '').strip().lower()
        if 'instagram.' in u: return 'Instagram'
        if 'tiktok.' in u: return 'TikTok'
        if 'facebook.' in u or 'fb.' in u: return 'Facebook'
        if 'youtube.' in u or 'youtu.be' in u: return 'YouTube'
        if 'telegram.' in u or 't.me/' in u: return 'Telegram'
        if 'viber.' in u: return 'Viber'
        if 'github.' in u: return 'GitHub'
        return None

    guessed = _guess_social_name(url)
    if guessed:
        name = guessed

    await socials_db.add_social(name, url)

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

@admin_router.message(LocationStates.waiting_image, F.photo | F.document | F.text)

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

    coords = extract_coords_from_maps((data.get('google_maps_url') or '').strip())
    coordinates = {'lat': coords[0], 'lon': coords[1]} if coords else None

    await location_db.add_location(
        name=(data.get('name') or '').strip(),
        address=(data.get('address') or '').strip(),
        schedule=(data.get('schedule') or '').strip(),
        phone=(data.get('phone') or '').strip(),
        email=(data.get('email') or '').strip(),
        google_maps_url=(data.get('google_maps_url') or '').strip(),
        max_tables=int(data.get('max_tables') or 10),
        coordinates=coordinates,
        image_url=(data.get('image_url') or '').strip(),
        amenities=data.get('amenities') or [],
        atmosphere=(data.get('atmosphere') or '').strip(),
    )

    await public_data_cache.refresh('locations')

    await safe_edit_message(callback.message, '✅ ДОДАНО!', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

    await state.clear()

@admin_router.callback_query(F.data == 'locs_edit')

async def edit_locations_start(callback: CallbackQuery):

    locs = await location_db.get_all_locations()

    if not locs:

        await callback.answer('Порожньо.')

        return

    await safe_edit_message(callback.message, '✏️ Оберіть локацію для редагування:', reply_markup=akb.get_locations_list_kb(locs, 'locs_edt_it'), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('locs_edt_it_'))

async def edit_location_sel(callback: CallbackQuery, state: FSMContext):

    lid = callback.data.replace('locs_edt_it_', '')

    loc = await location_db.get_location_by_id(lid)

    await state.update_data(edit_id=lid)

    kb_edit = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назву', callback_data='ed_l_name'), InlineKeyboardButton(text='Адресу', callback_data='ed_l_address')],
        [InlineKeyboardButton(text='Графік', callback_data='ed_l_schedule'), InlineKeyboardButton(text='Телефон', callback_data='ed_l_phone')],
        [InlineKeyboardButton(text='Email', callback_data='ed_l_email'), InlineKeyboardButton(text='Maps URL', callback_data='ed_l_google_maps_url')],
        [InlineKeyboardButton(text='Столики', callback_data='ed_l_max_tables'), InlineKeyboardButton(text='Зручності', callback_data='ed_l_amenities')],
        [InlineKeyboardButton(text='Атмосфера', callback_data='ed_l_atmosphere')],
        [InlineKeyboardButton(text='🖼 Фото', callback_data='ed_l_image_url'), InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='locs_edit')],
    ])

    await safe_edit_message(callback.message, f"Редагування <b>{loc['name']}</b>", reply_markup=kb_edit, parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('ed_l_'))

async def edit_location_field_start(callback: CallbackQuery, state: FSMContext):

    field = callback.data.replace('ed_l_', '')

    await state.update_data(edit_field=field)

    await callback.message.answer('✏️ Введіть нове значення:')

    await state.set_state(LocationStates.edit_value)

    await callback.answer()

@admin_router.message(LocationStates.edit_value, F.photo | F.document | F.text)

async def edit_location_value_save(message: Message, state: FSMContext, bot: Bot):

    if await restart_fsm_on_command(message, state): return

    data = await state.get_data()

    field = data.get('edit_field')

    val = (await process_photo(message, bot)) if field == 'image_url' else (message.text or '').strip()

    upd = {field: val}

    if field == 'max_tables':
        try:
            n = int(str(val).strip())
            if n <= 0 or n > 500:
                raise ValueError
            upd[field] = n
        except Exception:
            await message.answer('❌ Введіть коректне число столиків (1-500).', parse_mode='HTML')
            return

    if field == 'amenities':
        items = [x.strip() for x in str(val).split(',') if x.strip()]
        upd[field] = items

    if field == 'google_maps_url':

        c = extract_coords_from_maps(val)

        if c: upd['coordinates'] = {'lat': c[0], 'lon': c[1]}

    await location_db.update_location(data.get('edit_id'), upd)

    await public_data_cache.refresh('locations')

    await message.answer(f'✅ Оновлено!', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

    await state.clear()

class MenuCategoryStates(StatesGroup):
    waiting_add_cat_name = State()
    waiting_edit_cat_selection = State()
    waiting_edit_cat_new_name = State()
    waiting_del_cat_selection = State()

@admin_router.callback_query(F.data == 'menu_cats_manage')
async def menu_cats_manage(callback: CallbackQuery):
    await callback.answer('❌ Керування категоріями вимкнено.', show_alert=True)
    await safe_edit_message(callback.message, '📋 <b>КЕРУВАННЯ МЕНЮ</b>', reply_markup=akb.get_menu_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'menu_cats')
async def menu_cats_list(callback: CallbackQuery):
    await callback.answer('❌ Керування категоріями вимкнено.', show_alert=True)

@admin_router.callback_query(F.data == 'menu_cat_add')
async def menu_cat_add_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer('❌ Керування категоріями вимкнено.', show_alert=True)

@admin_router.message(MenuCategoryStates.waiting_add_cat_name)
async def menu_cat_add_name(message: Message, state: FSMContext):
    await message.answer('❌ Керування категоріями вимкнено.', parse_mode='HTML')
    await state.clear()

@admin_router.callback_query(F.data == 'menu_cat_edit')
async def menu_cat_edit_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer('❌ Керування категоріями вимкнено.', show_alert=True)

@admin_router.callback_query(MenuCategoryStates.waiting_edit_cat_selection, F.data.startswith('m_edit_cat_'))
async def menu_cat_edit_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer('❌ Керування категоріями вимкнено.', show_alert=True)
    await state.clear()

@admin_router.message(MenuCategoryStates.waiting_edit_cat_new_name)
async def menu_cat_edit_new_name(message: Message, state: FSMContext):
    await message.answer('❌ Керування категоріями вимкнено.', parse_mode='HTML')
    await state.clear()

@admin_router.callback_query(F.data == 'menu_cat_del')
async def menu_cat_del_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer('❌ Керування категоріями вимкнено.', show_alert=True)

@admin_router.callback_query(MenuCategoryStates.waiting_del_cat_selection, F.data.startswith('m_del_cat_full_'))
async def menu_cat_del_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer('❌ Керування категоріями вимкнено.', show_alert=True)
    await state.clear()

@admin_router.callback_query(MenuCategoryStates.waiting_del_cat_selection, F.data == 'm_del_cat_confirm')
async def menu_cat_del_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer('❌ Керування категоріями вимкнено.', show_alert=True)
    await state.clear()
