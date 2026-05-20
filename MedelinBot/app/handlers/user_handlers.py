
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup

from aiogram.exceptions import TelegramBadRequest

from aiogram.filters import CommandStart

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from app.keyboards import user_keyboards as kb

from app.keyboards import admin_keyboards as akb

from app.common.config import WORK_START_HOUR, WORK_END_HOUR

from app.databases.menu_database import menu_db, parse_gramovka_grams, strip_gramovka, clean_coffee_name

from app.databases.user_database import user_db

from app.databases.orders_database import orders_db

from app.databases.active_bookings_database import active_bookings_db

from app.databases.active_orders_database import active_orders_db

from app.databases.admin_database import admin_db

from app.databases.location_database import location_db

from app.databases.coffee_beans_database import coffee_beans_db

from app.databases.socials_database import socials_db

from app.handlers.order_handlers import send_beans_invoice, send_order_invoice

from app.utils.logger import log_activity

from app.utils.time_utils import is_working_hours, get_closed_message

from app.utils.message_utils import safe_edit_message

import datetime

from urllib.parse import quote_plus

user_router = Router()

class BookingStates(StatesGroup):

    choosing_location = State()

    choosing_date = State()

    choosing_time = State()

    choosing_people_count = State()

    entering_wishes = State()

    entering_phone = State()

    booking_summary = State()

    browsing_menu = State()

class CoffeeBeanStates(StatesGroup):

    choosing_beans = State()

    choosing_weight = State()

    choosing_delivery_type = State()

    choosing_location = State()

    entering_np_city = State()

    entering_np_warehouse = State()

    entering_phone = State()

@user_router.message(F.text == '🏠 НА ГОЛОВНУ')

async def process_back_to_main(message: Message, state: FSMContext):

    await state.clear()

    is_admin = await admin_db.is_admin(message.from_user.id)

    await message.answer('<i class="fas fa-coffee"></i> <b>ГОЛОВНЕ МЕНЮ</b>', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

@user_router.message(CommandStart())

async def cmd_start(message: Message, state: FSMContext):

    await state.clear()

    await log_activity(message.from_user.id, message.from_user.username, 'start')

    await user_db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)

    is_admin = await admin_db.is_admin(message.from_user.id)

    await message.answer('<i class="fas fa-coffee"></i> <b>ВІТАЄМО В «MEDELIN»!</b>\n\nОберіть дію нижче 👇', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

@user_router.message(F.text.in_([kb.BTN_BOOK_TABLE, '✨ ЗАБРОНЮВАТИ СТОЛИК']))

async def process_booking(message: Message, state: FSMContext):

    if not is_working_hours():

        await message.answer(get_closed_message(), parse_mode='HTML')

        return

    await state.clear()

    await state.update_data(booking_mode=True, fullname=message.from_user.full_name)

    await message.answer('<i class="fas fa-map-marker-alt"></i> <b>ОБЕРІТЬ ЗАКЛАД ДЛЯ БРОНЮВАННЯ:</b>', reply_markup=await kb.get_locations_kb(), parse_mode='HTML')

    await state.set_state(BookingStates.choosing_location)

@user_router.callback_query(F.data.startswith('loc_'), BookingStates.choosing_location)

async def booking_location_chosen(callback: CallbackQuery, state: FSMContext):

    loc_id = callback.data.split('_')[1]

    await state.update_data(location_id=loc_id)

    await safe_edit_message(callback.message, '<i class="fas fa-calendar-alt"></i> <b>ОБЕРІТЬ ДАТУ:</b>', reply_markup=kb.get_date_kb(), parse_mode='HTML')

    await state.set_state(BookingStates.choosing_date)

@user_router.callback_query(F.data.startswith('book_date_'), BookingStates.choosing_date)

async def booking_date_chosen(callback: CallbackQuery, state: FSMContext):

    date_str = callback.data.replace('book_date_', '')

    await state.update_data(booking_date=date_str)

    sel_date = datetime.date.fromisoformat(date_str)

    time_kb = kb.get_time_kb(sel_date)

    if not getattr(time_kb, 'inline_keyboard', None):

        await safe_edit_message(callback.message, 'Немає доступного часу на обрану дату.\nОберіть іншу дату:', reply_markup=kb.get_date_kb(), parse_mode='HTML')

        await state.set_state(BookingStates.choosing_date)

        return

    await safe_edit_message(callback.message, '<i class="fas fa-clock"></i> <b>ОБЕРІТЬ ЧАС:</b>', reply_markup=time_kb, parse_mode='HTML')

    await state.set_state(BookingStates.choosing_time)

@user_router.callback_query(F.data.startswith('book_time_'), BookingStates.choosing_time)

async def booking_time_chosen(callback: CallbackQuery, state: FSMContext):

    time_str = callback.data.replace('book_time_', '')

    data = await state.get_data()

    try:

        sel_date = datetime.date.fromisoformat(data['booking_date'])

        h, m = [int(x) for x in time_str.split(':', 1)]

        sel_dt = datetime.datetime.combine(sel_date, datetime.time(hour=h, minute=m))

        end_hour_raw = int(WORK_END_HOUR)

        if end_hour_raw == 24:

            closing = datetime.datetime.combine(sel_date, datetime.time(hour=0, minute=0)) + datetime.timedelta(days=1)

        else:

            closing = datetime.datetime.combine(sel_date, datetime.time(hour=end_hour_raw, minute=0))

        latest = (closing - datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

        if sel_dt > latest:

            await callback.answer('Останній доступний час — за 1 годину до закриття.', show_alert=True)

            return

        if sel_date == datetime.date.today() and sel_dt < datetime.datetime.now().replace(second=0, microsecond=0):

            await callback.answer('Неможливо обрати час у минулому.', show_alert=True)

            return

    except Exception:

        await callback.answer('Некоректний час.', show_alert=True)

        return

    full_date = f"{datetime.date.fromisoformat(data['booking_date']).strftime('%d.%m')} о {time_str}"

    await state.update_data(date_time=full_date)

    await safe_edit_message(callback.message, f'<i class="fas fa-check-circle"></i> <b>ОБРАНО:</b> {full_date}\n\n<i class="fas fa-users"></i> <b>КІЛЬКІСТЬ ГОСТЕЙ (1-20):</b>', parse_mode='HTML')

    await state.set_state(BookingStates.choosing_people_count)

@user_router.message(BookingStates.choosing_people_count)

async def booking_people_count_entered(message: Message, state: FSMContext):

    if not message.text or not message.text.isdigit() or (not 1 <= int(message.text) <= 20):

        await message.answer('❌ <b>ЧИСЛО ВІД 1 ДО 20.</b>', parse_mode='HTML')

        return

    await state.update_data(people_count=message.text)

    await message.answer('<i class="fas fa-comment-dots"></i> <b>ПОБАЖАННЯ АБО \'ні\':</b>', parse_mode='HTML')

    await state.set_state(BookingStates.entering_wishes)

async def _booking_summary_text(data: dict) -> str:

    loc_id = data.get('location_id')

    loc = await location_db.get_location_by_id(loc_id)

    location_name = loc['name'] if loc else '—'

    wishes = data.get('wishes') or ''

    wishes_line = wishes if wishes else '—'

    cart = data.get('cart', []) or []

    cart_line = ', '.join(cart).upper() if cart else '—'

    pay_hint = '\n\nПісля підтвердження буде сформовано рахунок для оплати.' if cart else ''

    return f"""<i class="fas fa-clipboard-check"></i> <b>ПЕРЕВІРТЕ ДАНІ БРОНІ:</b>\n\n<i class="fas fa-university"></i> <b>ЗАКЛАД:</b> {location_name}\n<i class="fas fa-clock"></i> <b>ЧАС:</b> {data.get('date_time') or '—'}\n<i class="fas fa-users"></i> <b>ГОСТЕЙ:</b> {data.get('people_count') or '—'}\n<i class="fas fa-comment-dots"></i> <b>ПОБАЖАННЯ:</b> {wishes_line}\n<i class="fas fa-utensils"></i> <b>МЕНЮ:</b> {cart_line}\n\nОберіть дію нижче <i class="fas fa-chevron-down"></i>{pay_hint}"""

def _booking_summary_kb() -> InlineKeyboardMarkup:

    rows = [[InlineKeyboardButton(text='✅ ПІДТВЕРДИТИ БРОНЬ', callback_data='booking_confirm')], [InlineKeyboardButton(text='🛍 ДОДАТИ ПОЗИЦІЇ', callback_data='booking_go_menu')], [InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')]]

    return InlineKeyboardMarkup(inline_keyboard=rows)

async def _send_booking_summary(target, state: FSMContext):

    data = await state.get_data()

    text = await _booking_summary_text(data)

    markup = _booking_summary_kb()

    if isinstance(target, CallbackQuery):

        await safe_edit_message(target.message, text, reply_markup=markup, parse_mode='HTML')

    else:

        await target.answer(text, reply_markup=markup, parse_mode='HTML')

    await state.set_state(BookingStates.booking_summary)

@user_router.message(BookingStates.entering_wishes)

async def booking_wishes_entered(message: Message, state: FSMContext, bot: Bot):

    wishes_raw = (message.text or '').strip()

    wishes = '' if wishes_raw.lower() in ('ні', 'нет', 'no', '-', '—') else wishes_raw

    await state.update_data(wishes=wishes)

    phone = await user_db.get_phone(message.from_user.id)

    if phone:

        await state.update_data(phone=phone)

        await _send_booking_summary(message, state)

        return

    await message.answer('☎️ <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН:</b>\n\nНатисніть кнопку нижче або введіть вручну (+380...):', reply_markup=kb.get_phone_kb(), parse_mode='HTML')

    await state.set_state(BookingStates.entering_phone)

@user_router.message(BookingStates.entering_phone)

async def booking_phone_entered(message: Message, state: FSMContext, bot: Bot):

    if message.text == '🏠 НА ГОЛОВНУ':

        await back_to_main(message, state)

        return

    phone = message.contact.phone_number if message.contact else (message.text or '').strip()

    if len(''.join((ch for ch in phone if ch.isdigit()))) < 10:

        await message.answer('❌ <b>НЕКОРЕКТНИЙ ТЕЛЕФОН.</b>\nСпробуйте ще раз у форматі +380...', parse_mode='HTML')

        return

    await state.update_data(phone=phone)

    await user_db.set_phone(message.from_user.id, phone)

    is_admin = await admin_db.is_admin(message.from_user.id)

    await message.answer('✅ Телефон збережено.', reply_markup=kb.get_main_menu(is_admin))

    await _send_booking_summary(message, state)

@user_router.callback_query(F.data == 'booking_confirm', BookingStates.booking_summary)

async def booking_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):

    await callback.answer()

    data = await state.get_data()

    cart = data.get('cart', []) or []

    if cart:

        await callback.message.answer('<b>ПІДТВЕРДЖЕННЯ БРОНЮВАННЯ</b>\n\nДля завершення оформлення потрібна оплата замовлення.\nНатисніть кнопку оплати в рахунку нижче.', parse_mode='HTML')

        await send_order_invoice(callback.from_user, callback.message.chat.id, state, bot)

        return

    await _create_table_booking_and_notify(callback.from_user, callback.message.chat.id, state, bot)

async def _create_table_booking_and_notify(user, chat_id: int, state: FSMContext, bot: Bot):

    data = await state.get_data()

    loc_id = data.get('location_id')

    phone = data.get('phone')

    date_time = data.get('date_time')

    people_count = data.get('people_count')

    wishes = data.get('wishes') or ''

    loc = await location_db.get_location_by_id(loc_id)

    if not loc or not phone or (not date_time) or (not people_count):

        await state.clear()

        is_admin = await admin_db.is_admin(user.id)

        await bot.send_message(chat_id, '❌ <b>БРОНЮВАННЯ НЕ ВДАЛОСЯ.</b>\nСпробуйте ще раз з головного меню.', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

        return

    order_id = await orders_db.add_order(user.id, user.username, user.full_name, phone, loc_id, date_time, str(people_count), wishes if wishes else '—', 'СТОЛИК', 'booking')

    admin_text = f"📅 <b>НОВЕ БРОНЮВАННЯ СТОЛИКА</b>\n\n👤 <b>КЛІЄНТ:</b> {user.full_name}\n📞 <b>ТЕЛЕФОН:</b> <code>{phone}</code>\n🏛 <b>ЗАКЛАД:</b> {loc['name']}\n🕒 <b>ЧАС:</b> {date_time}\n👥 <b>ГОСТЕЙ:</b> {people_count}\n💬 <b>ПОБАЖАННЯ:</b> {(wishes if wishes else '—')}"

    targets = await admin_db.get_notification_targets(loc_id)

    for aid in targets:

        try:

            await bot.send_message(aid, admin_text, reply_markup=akb.get_booking_manage_kb(order_id), parse_mode='HTML')

            await orders_db.mark_admin_notified(order_id, aid)

        except:

            pass

    is_admin = await admin_db.is_admin(user.id)

    await bot.send_message(chat_id, '✅ <b>ЗАПИТ НА БРОНЮВАННЯ ВІДПРАВЛЕНО!</b>\nМи підтвердимо його найближчим часом.' if targets else '🕓 <b>ЗАПИТ НА БРОНЮВАННЯ ЗБЕРЕЖЕНО.</b>\n\nНаразі немає доступних адміністраторів на зміні. Спробуйте трохи пізніше або дочекайтесь.', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

    await state.clear()

@user_router.callback_query(F.data == 'booking_go_menu', BookingStates.booking_summary)

@user_router.callback_query(F.data == 'booking_go_menu', BookingStates.browsing_menu)

async def booking_go_menu(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    await state.update_data(cart=[], booking_mode=True)

    categories = await menu_db.get_categories()

    await safe_edit_message(callback.message, '🍽️ <b>МЕНЮ / ЗАМОВЛЕННЯ</b>\n\nДодайте позиції до броні. Оберіть категорію:', reply_markup=kb.get_categories_kb(categories, booking_mode=True, cart_count=0), parse_mode='HTML')

    await state.set_state(BookingStates.browsing_menu)

@user_router.callback_query(F.data == 'back_to_booking_summary')

async def booking_back_to_summary(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    if not data.get('booking_mode'):

        await callback.answer('Немає активної броні.')

        return

    await callback.answer()

    await _send_booking_summary(callback, state)

@user_router.message(F.text.in_([kb.BTN_MENU, '📜 МЕНЮ', '🍽️ МЕНЮ', 'ЗАМОВИТИ']))

async def open_menu(message: Message, state: FSMContext):

    if not is_working_hours():

        await message.answer(get_closed_message(), parse_mode='HTML')

        return

    data = await state.get_data()

    cart = data.get('cart', [])

    await state.clear()

    await state.update_data(cart=cart, booking_mode=False)

    categories = await menu_db.get_categories()

    await message.answer('🍽️ <b>МЕНЮ / ЗАМОВЛЕННЯ</b>\n\nОберіть категорію:', reply_markup=kb.get_categories_kb(categories, cart_count=len(cart)), parse_mode='HTML')

    await state.set_state(BookingStates.browsing_menu)

@user_router.callback_query(F.data.startswith('cat_'))

async def menu_category(callback: CallbackQuery, state: FSMContext):

    cat_id = callback.data.replace('cat_', '', 1)

    categories = await menu_db.get_categories()

    cat = next((c for c in categories if kb.cat_key(str(c)) == cat_id), None)

    if not cat:

        await callback.answer('Категорію не знайдено.')

        return

    await state.update_data(current_category=cat)

    data = await state.get_data()

    cart = data.get('cart', [])

    booking_mode = bool(data.get('booking_mode'))

    items = await menu_db.get_items_by_category(cat)

    cleaned_items = []

    for item in items:

        item_list = list(item)

        item_list[1] = clean_coffee_name(item_list[1])

        cleaned_items.append(tuple(item_list))

    await safe_edit_message(callback.message, f'🍽️ <b>{cat}</b>\n\nОберіть позицію:', reply_markup=kb.get_items_kb(cleaned_items, cat, cart_count=len(cart), booking_mode=booking_mode), parse_mode='HTML')

@user_router.callback_query(F.data.startswith('item_'))

async def menu_item(callback: CallbackQuery, state: FSMContext):

    item_id = callback.data.replace('item_', '', 1)

    row = await menu_db.get_item_by_id(item_id)

    if not row:

        await callback.answer('Не знайдено.')

        return

    _, category, name, price, description, volume, calories, image_url, composition, strength, sweetness, options = row

    name = clean_coffee_name(name)

    parts = [f'✨ <b>{name}</b>', f'💰 <b>Ціна:</b> {price} ₴']

    if volume:

        parts.append(f'⚖️ <b>Обʼєм:</b> {volume}')

    if calories:

        parts.append(f"🔋 <b>Енерг. цінність:</b> {str(calories).replace('ккал', '').strip()} ккал")

    if strength:

        parts.append(f"💪 <b>Міцність:</b> {'⚡️' * int(strength)}")

    if sweetness:

        parts.append(f"🍭 <b>Солодкість:</b> {'🍬' * int(sweetness)}")

    if composition:

        parts.append(f'📝 <b>Склад:</b> {composition}')

    if description:

        parts.append(f'\n📜 <b>Опис:</b>\n{description}')

    text = '\n'.join(parts)

    category_norm = category.lower().strip()
    is_coffee_or_milk = any(c in category_norm for c in ['кава', 'мілк', 'матча', 'какао', 'декаф'])
    
    if is_coffee_or_milk:
        from app.utils.data_cache import public_data_cache
        # Намагаємось взяти опції з кешу (там вони вже збагачені молоком та дефолтами)
        cached_opts = None
        menu_data = public_data_cache.get('menu')
        if menu_data:
            for section in menu_data:
                for it in section['items']:
                    if it['id'] == item_id:
                        cached_opts = it.get('options')
                        break
                if cached_opts: break
        
        if cached_opts:
            options = cached_opts
        elif not options or not any(o.get('type') == 'milk' for o in options):
            # Якщо в базі порожньо або немає молока - додаємо дефолтний набір
            options = [
                {'type': 'caffeine', 'name': 'Стандарт', 'add_price': 0},
                {'type': 'caffeine', 'name': 'Декаф', 'add_price': 10},
                {'type': 'milk', 'name': 'Звичайне', 'add_price': 0},
                {'type': 'milk', 'name': 'Безлактозне', 'add_price': 15},
            ]

        # Розраховуємо початкову ціну (базова ціна)
        reply_markup = kb.get_item_options_kb(item_id, name, options, current_price=int(price or 0))
    else:
        reply_markup = kb.get_item_actions_kb(item_id)

    if image_url:
        await callback.message.delete()
        await callback.message.answer_photo(photo=image_url, caption=text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await safe_edit_message(callback.message, text, reply_markup=reply_markup, parse_mode='HTML')

@user_router.callback_query(F.data.startswith('opt_'))
async def menu_toggle_option(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    item_id = parts[1]
    opt_data = parts[2] # "type:name"
    
    opt_type, opt_name = opt_data.split(':', 1) if ':' in opt_data else ('addon', opt_data)

    data = await state.get_data()
    item_opts = data.get(f'opts_{item_id}', [])

    # Обробка ексклюзивності для кофеїну та молока
    if opt_type in ('caf', 'milk', 'caffeine'):
        # Видаляємо інші опції того ж типу (враховуючи обидва можливі ключі для кофеїну)
        current_type = 'caf' if opt_type in ('caf', 'caffeine') else 'milk'
        item_opts = [o for o in item_opts if not (o.startswith('caf:') or o.startswith('caffeine:') or o.startswith('milk:')) or not o.startswith(f"{current_type}:")]
        
        # Видаляємо всі опції того ж типу
        if opt_type in ('caf', 'caffeine'):
            item_opts = [o for o in item_opts if not (o.startswith('caf:') or o.startswith('caffeine:'))]
        else:
            item_opts = [o for o in item_opts if not o.startswith('milk:')]
            
        item_opts.append(f"{opt_type}:{opt_name}")
    else:
        # Для додатків (addons) - просто перемикаємо
        full_opt = f"add:{opt_name}"
        if full_opt in item_opts:
            item_opts.remove(full_opt)
        else:
            item_opts.append(full_opt)

    await state.update_data({f'opts_{item_id}': item_opts})
    
    # Отримуємо айтем знову щоб отримати його опції та базову ціну
    row = await menu_db.get_item_by_id(item_id)
    _, category, name, base_price, _, _, _, _, _, _, _, options = row
    
    from app.utils.data_cache import public_data_cache
    cached_opts = None
    menu_data = public_data_cache.get('menu')
    if menu_data:
        for section in menu_data:
            for it in section['items']:
                if it['id'] == item_id:
                    cached_opts = it.get('options')
                    break
            if cached_opts: break
    
    if cached_opts:
        options = cached_opts
    elif not options or not any(o.get('type') == 'milk' for o in options):
        # Fallback на дефолтні
        options = [
            {'type': 'caffeine', 'name': 'Стандарт', 'add_price': 0},
            {'type': 'caffeine', 'name': 'Декаф', 'add_price': 10},
            {'type': 'milk', 'name': 'Звичайне', 'add_price': 0},
            {'type': 'milk', 'name': 'Безлактозне', 'add_price': 15},
        ]
    
    # Розраховуємо поточну ціну
    current_total = int(base_price or 0)
    for o_str in item_opts:
        if ':' in o_str:
            _, o_name = o_str.split(':', 1)
            for opt_obj in options:
                if opt_obj['name'] == o_name:
                    current_total += int(opt_obj.get('add_price') or 0)
                    break

    await callback.message.edit_reply_markup(reply_markup=kb.get_item_options_kb(item_id, name, options, item_opts, current_price=current_total))

@user_router.callback_query(F.data.startswith('add_to_cart_'))
async def menu_add_to_cart(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split('_')
    item_id = data[3]
    row = await menu_db.get_item_by_id(item_id)
    if not row:
        await callback.answer('Не знадено.')
        return

    _, category, name, base_price, _, _, _, _, _, _, _, options = row
    name = clean_coffee_name(name)
    
    from app.utils.data_cache import public_data_cache
    cached_opts = None
    menu_data = public_data_cache.get('menu')
    if menu_data:
        for section in menu_data:
            for it in section['items']:
                if it['id'] == item_id:
                    cached_opts = it.get('options')
                    break
            if cached_opts: break
    
    if cached_opts:
        options = cached_opts
    elif not options or not any(o.get('type') == 'milk' for o in options):
        # Fallback на дефолтні
        options = [
            {'type': 'caffeine', 'name': 'Стандарт', 'add_price': 0},
            {'type': 'caffeine', 'name': 'Декаф', 'add_price': 10},
            {'type': 'milk', 'name': 'Звичайне', 'add_price': 0},
            {'type': 'milk', 'name': 'Безлактозне', 'add_price': 15},
        ]
    
    state_data = await state.get_data()
    item_opts = state_data.get(f'opts_{item_id}', [])

    options_desc = []
    total_extra = 0
    
    for o_str in item_opts:
        if ':' in o_str:
            o_type, o_name = o_str.split(':', 1)
            # Якщо це дефолтна опція, не додаємо в опис
            if (o_name == 'Стандарт' and o_type in ('caf', 'caffeine')) or (o_name == 'Звичайне' and o_type == 'milk'):
                continue
            options_desc.append(o_name)
            
            # Шукаємо ціну опції
            found_price = False
            if options:
                for opt_obj in options:
                    if opt_obj['name'] == o_name:
                        total_extra += int(opt_obj.get('add_price') or 0)
                        found_price = True
                        break
            
            if not found_price:
                # Hardcoded fallback prices
                if o_name == 'Декаф': total_extra += 10
                elif o_type in ('add', 'addon'): total_extra += 10
        else:
            # Старий формат (сумісність)
            opt_map = {'decaf': 'декаф', 'honey': 'мед', 'addmilk': 'молоко'}
            options_desc.append(opt_map.get(o_str, o_str))
            total_extra += 10

    final_name = name
    if options_desc:
        final_name += f" ({', '.join(options_desc)})"

    # Додаємо ціну до імені для розрахунку в кошику
    final_price = int(base_price or 0) + total_extra
    final_item_entry = f"{final_name} [{final_price}]"

    cart = list(state_data.get('cart', []))
    cart.append(final_item_entry)
    await state.update_data(cart=cart)
    await state.update_data({f'opts_{item_id}': []})

    await callback.answer(f'Додано: {final_name}')

    booking_mode = bool(state_data.get('booking_mode'))

    categories = await menu_db.get_categories()

    await safe_edit_message(callback.message, '🍽️ <b>МЕНЮ / ЗАМОВЛЕННЯ</b>\n\nДодано в кошик. Оберіть категорію:', reply_markup=kb.get_categories_kb(categories, booking_mode=booking_mode, cart_count=len(cart)), parse_mode='HTML')

@user_router.callback_query(F.data == 'back_cats')

async def menu_back_to_categories(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    cart = data.get('cart', [])

    booking_mode = bool(data.get('booking_mode'))

    categories = await menu_db.get_categories()

    await safe_edit_message(callback.message, '🍽️ <b>МЕНЮ / ЗАМОВЛЕННЯ</b>\n\nОберіть категорію:', reply_markup=kb.get_categories_kb(categories, booking_mode=booking_mode, cart_count=len(cart)), parse_mode='HTML')

@user_router.callback_query(F.data == 'back_items')

async def menu_back_to_items(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    cart = data.get('cart', [])

    cat = data.get('current_category')

    booking_mode = bool(data.get('booking_mode'))

    if not cat:

        await menu_back_to_categories(callback, state)

        return

    items = await menu_db.get_items_by_category(cat)

    cleaned_items = []

    for item in items:

        item_list = list(item)

        item_list[1] = clean_coffee_name(item_list[1])

        cleaned_items.append(tuple(item_list))

    await safe_edit_message(callback.message, f'🍽️ <b>{cat}</b>\n\nОберіть позицію:', reply_markup=kb.get_items_kb(cleaned_items, cat, cart_count=len(cart), booking_mode=booking_mode), parse_mode='HTML')

@user_router.message(F.text.in_([kb.BTN_LOCATIONS, '🏢 НАШІ ЗАКЛАДИ']))

async def show_locations(message: Message, state: FSMContext):

    await message.answer('📍 <b>НАШІ ЗАКЛАДИ</b>\n\nОберіть заклад:', reply_markup=await kb.get_locations_info_kb(), parse_mode='HTML')

@user_router.callback_query(F.data.startswith('locinfo_'))

async def location_info(callback: CallbackQuery):

    loc_id = callback.data.replace('locinfo_', '', 1)

    if loc_id == 'back':

        await location_info_back(callback)

        return

    loc = await location_db.get_location_by_id(loc_id)

    if not loc:

        await callback.answer('Заклад не знайдено.')

        return

    address = loc.get('address', '—')

    name = loc.get('name', '—')

    schedule = loc.get('schedule', '—')

    phone = loc.get('phone', '+380503775906')

    email = loc.get('email', 'medelin.social@gmail.com')

    maps_url = loc.get('google_maps_url') or f"https://www.google.com/maps/search/?api=1&query={quote_plus(address + ', Uzhhorod')}"

    text = f'🏛 <b>{name}</b>\n\n<i class="fas fa-map-marker-alt"></i> <b>Адреса:</b> <code>{address}</code>\n<i class="fas fa-clock"></i> <b>Графік:</b> <code>{schedule}</code>\n<i class="fas fa-phone"></i> <b>Телефон:</b> <code>{phone}</code>\n<i class="fas fa-envelope"></i> <b>Email:</b> <code>{email}</code>\n\n✨ <i>Чекаємо на вас у гості!</i>'

    kb_info = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🧭 ПОБУДУВАТИ МАРШРУТ', url=maps_url)], [InlineKeyboardButton(text='⬅️ ДО СПИСКУ', callback_data='locinfo_back'), InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')]])

    image_url = loc.get('image_url')

    await callback.answer()

    if image_url:

        await callback.message.delete()

        await callback.message.answer_photo(photo=image_url, caption=text, reply_markup=kb_info, parse_mode='HTML')

    else:

        await safe_edit_message(callback.message, text, reply_markup=kb_info, parse_mode='HTML')

@user_router.callback_query(F.data == 'locinfo_back')

async def location_info_back(callback: CallbackQuery):

    await callback.answer()

    await safe_edit_message(callback.message, '<i class="fas fa-map-marker-alt"></i> <b>НАШІ ЗАКЛАДИ</b>\n\nОберіть заклад:', reply_markup=await kb.get_locations_info_kb(), parse_mode='HTML')

@user_router.message(F.text.in_([kb.BTN_CONTACTS, '📞 КОНТАКТИ']))

async def show_contacts(message: Message, state: FSMContext):

    await message.answer('☎️ <b>КОНТАКТИ</b>\n\n<i class="fas fa-phone"></i> <code>+380503775906</code>\n<i class="fas fa-envelope"></i> <code>medelin.social@gmail.com</code>\n\nОберіть, куди перейти:', reply_markup=await kb.get_contact_kb(), parse_mode='HTML')

@user_router.callback_query(F.data == 'contact_phone')

async def contact_phone(callback: CallbackQuery):

    await callback.answer()

    await callback.message.answer('<i class="fas fa-phone"></i> <b>Телефон:</b> <code>+380503775906</code>', parse_mode='HTML')

@user_router.callback_query(F.data == 'contact_email')

async def contact_email(callback: CallbackQuery):

    await callback.answer()

    await callback.message.answer('<i class="fas fa-envelope"></i> <b>Email:</b> <code>medelin.social@gmail.com</code>', parse_mode='HTML')

@user_router.message(F.text == kb.BTN_BEANS)

async def beans_start(message: Message, state: FSMContext):

    if not is_working_hours():

        await message.answer(get_closed_message(), parse_mode='HTML')

        return

    await state.clear()

    items = await coffee_beans_db.get_all_beans()

    if not items:

        await message.answer('☕️ <b>Кава в зернах</b>\n\nПоки що немає позицій.', parse_mode='HTML')

        return

    text = '<i class="fas fa-coffee"></i> <b>КАВА В ЗЕРНАХ «MEDELIN»</b>\n\nСвіжообсмажена кава для дому або офісу.\n👇 Оберіть сорт для замовлення:'

    beans_list = [(str(b['_id']), clean_coffee_name(b['name'])) for b in items]

    await message.answer(text, reply_markup=kb.get_beans_kb(beans_list), parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.choosing_beans)

@user_router.callback_query(F.data.startswith('bean_'), CoffeeBeanStates.choosing_beans)

async def beans_chosen(callback: CallbackQuery, state: FSMContext):

    bean_id = callback.data.replace('bean_', '', 1)

    bean = await coffee_beans_db.get_bean_by_id(bean_id)

    if not bean:

        await callback.answer('Не знайдено.')

        return

    bean_name = clean_coffee_name(bean['name'])

    await state.update_data(bean_name=bean_name, base_price=bean['price_250'])

    parts = [f'<i class="fas fa-coffee"></i> <b>{bean_name}</b>\n']

    if bean.get('description'):

        parts.append(f"""<i class="fas fa-info-circle"></i> <b>Опис:</b> {bean['description']}""")

    if bean.get('cup_score'):

        parts.append(f"""<i class="fas fa-star"></i> <b>Cup Score:</b> {bean['cup_score']}""")

    if bean.get('harvest'):

        parts.append(f"""<i class="fas fa-calendar-alt"></i> <b>Врожай:</b> {bean['harvest']}""")

    if bean.get('variety'):

        parts.append(f"""<i class="fas fa-leaf"></i> <b>Різновид:</b> {bean['variety']}""")

    if bean.get('processing'):

        parts.append(f"""<i class="fas fa-recycle"></i> <b>Обробка:</b> {bean['processing']}""")

    if bean.get('altitude'):

        parts.append(f"""<i class="fas fa-mountain"></i> <b>Висота:</b> {bean['altitude']}""")

    def render_stars(val):

        n = min(max(int(float(val or 0)), 0), 5)

        return '🌕' * n + '🌑' * (5 - n)

    if any([bean.get('acidity'), bean.get('bitterness'), bean.get('body')]):

        parts.append('\n<b>ХАРАКТЕРИСТИКИ:</b>')

        if bean.get('acidity'):

            parts.append(f"🍋 Кислинка: {render_stars(bean['acidity'])}")

        if bean.get('bitterness'):

            parts.append(f"☕️ Гірчинка: {render_stars(bean['bitterness'])}")

    parts.append('\n⚖️ <b>Оберіть вагу:</b>')

    text = '\n'.join(parts)

    reply_markup = kb.get_beans_weight_kb()

    if bean.get('image_url'):

        await callback.message.delete()

        await callback.message.answer_photo(photo=bean['image_url'], caption=text, reply_markup=reply_markup, parse_mode='HTML')

    else:

        await safe_edit_message(callback.message, text, reply_markup=reply_markup, parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.choosing_weight)

@user_router.callback_query(F.data == 'bean_back')

async def beans_back(callback: CallbackQuery, state: FSMContext):

    items = await coffee_beans_db.get_all_beans()

    beans_list = [(str(b['_id']), clean_coffee_name(b['name'])) for b in items]

    text = '☕️ <b>КАВА В ЗЕРНАХ</b>\n\nОберіть сорт:'

    reply_markup = kb.get_beans_kb(beans_list)

    await safe_edit_message(callback.message, text, reply_markup=reply_markup, parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.choosing_beans)

@user_router.callback_query(F.data.startswith('bean_w_'), CoffeeBeanStates.choosing_weight)

async def beans_weight(callback: CallbackQuery, state: FSMContext):

    weight = callback.data.replace('bean_w_', '', 1)

    await state.update_data(weight=weight)

    await safe_edit_message(callback.message, '🚚 <b>ОБЕРІТЬ СПОСІБ ОТРИМАННЯ:</b>', reply_markup=kb.get_beans_delivery_kb(), parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.choosing_delivery_type)

@user_router.callback_query(F.data == 'bean_del_pickup', CoffeeBeanStates.choosing_delivery_type)

async def beans_del_pickup(callback: CallbackQuery, state: FSMContext):

    await state.update_data(delivery_type='pickup')

    text = '📍 <b>ОБЕРІТЬ ЗАКЛАД ДЛЯ САМОВИВОЗУ:</b>'

    reply_markup = await kb.get_locations_kb()

    await safe_edit_message(callback.message, text, reply_markup=reply_markup, parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.choosing_location)

@user_router.callback_query(F.data == 'bean_del_np', CoffeeBeanStates.choosing_delivery_type)

@user_router.callback_query(F.data == 'bean_del_np', CoffeeBeanStates.entering_np_city)

@user_router.callback_query(F.data == 'bean_del_np', CoffeeBeanStates.entering_np_warehouse)

async def beans_del_np(callback: CallbackQuery, state: FSMContext):

    await state.update_data(delivery_type='nova_poshta')

    text = (

        "🏙 <b>ВВЕДІТЬ НАЗВУ МІСТА</b>\n"

        "Або надішліть вашу <b>геолокацію</b> 📍 за допомогою кнопки нижче, щоб знайти найближчі до вас відділення:"

    )

    await safe_edit_message(callback.message, text, parse_mode='HTML')

    await callback.message.answer("Оберіть дію:", reply_markup=kb.get_location_request_kb())

    await state.set_state(CoffeeBeanStates.entering_np_city)

@user_router.message(F.location, CoffeeBeanStates.entering_np_city)

async def beans_np_location_received(message: Message, state: FSMContext):

    lat, lon = message.location.latitude, message.location.longitude

    await message.answer("🔍 Пошук найближчих відділень...", reply_markup=kb.get_main_menu(await admin_db.is_admin(message.from_user.id)))

    from api import get_np_cities, get_np_warehouses

    async def get_city_name(la, lo):

        import aiohttp

        try:

            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={la}&lon={lo}&zoom=10&accept-language=uk"

            headers = {'User-Agent': 'MedelinBot/1.0'}

            async with aiohttp.ClientSession() as session:

                async with session.get(url, headers=headers, timeout=5) as resp:

                    if resp.status == 200:

                        d = await resp.json()

                        addr = d.get('address', {})

                        return addr.get('city') or addr.get('town') or addr.get('village') or addr.get('suburb') or addr.get('county')

        except: pass

        return None

    city_name_raw = await get_city_name(lat, lon)

    if not city_name_raw:

        await message.answer("❌ Не вдалося автоматично визначити місто. Будь ласка, введіть назву міста вручну:")

        return

    city_name = city_name_raw.split(',')[0].replace('місто ', '').replace('м. ', '').strip()

    cities = await get_np_cities(city_name)

    if not cities:

        await message.answer(f"❌ Місто '{city_name}' не знайдено у базі Нової Пошти. Введіть назву вручну:")

        return

    city = cities[0]

    city_ref = city.get('DeliveryCity', '') or city.get('Ref', '')

    city_present = city.get('Present', city_name)

    await state.update_data(np_city_ref=city_ref, np_city_name=city_present)

    warehouses = await get_np_warehouses(city_ref, None, None)

    if not warehouses:

        await message.answer(f"❌ У місті {city_present} не знайдено відділень.")

        return

    import math

    def dist(la1, lo1, la2, lo2):

        try:

            la1, lo1, la2, lo2 = float(la1), float(lo1), float(la2), float(lo2)

            return math.sqrt((la1-la2)**2 + (lo1-lo2)**2)

        except: return 999999

    valid_warehouses = [w for w in warehouses if w.get('Latitude') and w.get('Longitude')]

    other_warehouses = [w for w in warehouses if not (w.get('Latitude') and w.get('Longitude'))]

    valid_warehouses.sort(key=lambda w: dist(lat, lon, w.get('Latitude', 0), w.get('Longitude', 0)))

    sorted_warehouses = valid_warehouses + other_warehouses

    await state.update_data(np_warehouses_cache=sorted_warehouses[:50])

    text = f"🏢 <b>НАЙБЛИЖЧІ ВІДДІЛЕННЯ У МІСТІ {city_present.upper()}:</b>\nОберіть потрібне зі списку:"

    markup = kb.get_np_warehouses_kb(sorted_warehouses, page=0)

    await message.answer(text, reply_markup=markup, parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.entering_np_warehouse)

@user_router.message(CoffeeBeanStates.entering_np_city)

async def beans_np_city_search(message: Message, state: FSMContext):

    city_query = message.text.strip()

    if len(city_query) < 2:

        await message.answer('Мінімальна довжина запиту — 2 символи.')

        return

    from api import get_np_cities

    cities = await get_np_cities(city_query)

    if not cities:

        await message.answer('❌ Місто не знайдено. Спробуйте іншу назву:')

        return

    if len(cities) == 1:

        city = cities[0]

        city_ref = city.get('DeliveryCity', '') or city.get('Ref', '')

        city_name = city.get('Present', '')

        await state.update_data(np_city_ref=city_ref, np_city_name=city_name)

        await _show_np_warehouses(message, state, city_ref, city_name)

    else:

        await message.answer('🏙 <b>Оберіть місто зі списку:</b>', reply_markup=kb.get_np_cities_kb(cities), parse_mode='HTML')

@user_router.callback_query(F.data.startswith('np_city_'), CoffeeBeanStates.entering_np_city)

async def beans_np_city_selected(callback: CallbackQuery, state: FSMContext):

    city_ref = callback.data.replace('np_city_', '')

    city_name = "Обране місто"

    for row in callback.message.reply_markup.inline_keyboard:

        for button in row:

            if button.callback_data == callback.data:

                city_name = button.text

                break

    await state.update_data(np_city_ref=city_ref, np_city_name=city_name)

    await _show_np_warehouses(callback, state, city_ref, city_name)

async def _show_np_warehouses(target, state: FSMContext, city_ref: str, city_name: str, page: int = 0):

    from api import get_np_warehouses

    warehouses = await get_np_warehouses(city_ref)

    if not warehouses:

        text = f"❌ У місті {city_name} не знайдено відділень. Спробуйте інше місто."

        if isinstance(target, CallbackQuery):

            await safe_edit_message(target.message, text, reply_markup=kb.get_beans_delivery_kb(), parse_mode='HTML')

        else:

            await target.answer(text, reply_markup=kb.get_beans_delivery_kb(), parse_mode='HTML')

        await state.set_state(CoffeeBeanStates.choosing_delivery_type)

        return

    await state.update_data(np_warehouses_cache=warehouses)

    text = f"🏢 <b>ОБЕРІТЬ ВІДДІЛЕННЯ У МІСТІ {city_name.upper()}:</b>"

    markup = kb.get_np_warehouses_kb(warehouses, page=page)

    if isinstance(target, CallbackQuery):

        await safe_edit_message(target.message, text, reply_markup=markup, parse_mode='HTML')

    else:

        await target.answer(text, reply_markup=markup, parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.entering_np_warehouse)

@user_router.message(CoffeeBeanStates.entering_np_warehouse)

async def beans_np_warehouse_text(message: Message, state: FSMContext, bot: Bot):

    query = message.text.strip()

    data = await state.get_data()

    city_ref = data.get('np_city_ref')

    city_name = data.get('np_city_name', 'місті')

    if query == '🏠 НА ГОЛОВНУ':

        await back_to_main(message, state)

        return

    from api import get_np_warehouses

    warehouses = await get_np_warehouses(city_ref, None, query)

    if not warehouses:

        await message.answer(f"❌ За запитом '{query}' нічого не знайдено у {city_name}. Спробуйте ще раз або оберіть зі списку:")

        return

    await state.update_data(np_warehouses_cache=warehouses)

    text = f"🔎 <b>РЕЗУЛЬТАТИ ПОШУКУ У {city_name.upper()}:</b>\nЗнайдено: {len(warehouses)}"

    markup = kb.get_np_warehouses_kb(warehouses, page=0)

    await message.answer(text, reply_markup=markup, parse_mode='HTML')

@user_router.callback_query(F.data.startswith('np_wh_page_'), CoffeeBeanStates.entering_np_warehouse)

async def beans_np_wh_pagination(callback: CallbackQuery, state: FSMContext):

    page = int(callback.data.replace('np_wh_page_', ''))

    data = await state.get_data()

    warehouses = data.get('np_warehouses_cache', [])

    city_name = data.get('np_city_name', 'місті')

    markup = kb.get_np_warehouses_kb(warehouses, page=page)

    await safe_edit_message(callback.message, f"🏢 <b>ОБЕРІТЬ ВІДДІЛЕННЯ У МІСТІ {city_name.upper()}:</b>", reply_markup=markup, parse_mode='HTML')

@user_router.callback_query(F.data.startswith('np_wh_'), CoffeeBeanStates.entering_np_warehouse)

async def beans_np_warehouse_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):

    wh_ref = callback.data.replace('np_wh_', '')

    data = await state.get_data()

    warehouses = data.get('np_warehouses_cache', [])

    warehouse_name = "Обране відділення"

    for wh in warehouses:

        if wh.get('Ref') == wh_ref:

            warehouse_name = wh.get('Description')

            break

    await state.update_data(np_warehouse=warehouse_name)

    phone = await user_db.get_phone(callback.from_user.id)

    if phone:

        await state.update_data(phone=phone)

        await send_beans_invoice(callback.from_user, callback.message.chat.id, state, bot)

        return

    await callback.message.answer('☎️ <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН:</b>\n\nНатисніть кнопку нижче або введіть вручну (+380...):', reply_markup=kb.get_phone_kb(), parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.entering_phone)

@user_router.message(CoffeeBeanStates.entering_np_warehouse)

async def beans_np_warehouse_text(message: Message, state: FSMContext, bot: Bot):

    warehouse = message.text.strip()

    await state.update_data(np_warehouse=warehouse)

    phone = await user_db.get_phone(message.from_user.id)

    if phone:

        await state.update_data(phone=phone)

        await send_beans_invoice(message.from_user, message.chat.id, state, bot)

        return

    await message.answer('☎️ <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН:</b>\n\nНатисніть кнопку нижче або введіть вручну (+380...):', reply_markup=kb.get_phone_kb(), parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.entering_phone)

@user_router.callback_query(F.data.startswith('loc_'), CoffeeBeanStates.choosing_location)

async def beans_location(callback: CallbackQuery, state: FSMContext, bot: Bot):

    loc_id = callback.data.split('_')[1]

    await state.update_data(location_id=loc_id)

    phone = await user_db.get_phone(callback.from_user.id)

    if phone:

        await state.update_data(phone=phone)

        await send_beans_invoice(callback.from_user, callback.message.chat.id, state, bot)

        return

    await callback.message.answer('☎️ <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН:</b>\n\nНатисніть кнопку нижче або введіть вручну (+380...):', reply_markup=kb.get_phone_kb(), parse_mode='HTML')

    await state.set_state(CoffeeBeanStates.entering_phone)

@user_router.message(CoffeeBeanStates.entering_phone)

async def beans_phone(message: Message, state: FSMContext, bot: Bot):

    if message.text == '🏠 НА ГОЛОВНУ':

        await back_to_main(message, state)

        return

    phone = message.contact.phone_number if message.contact else (message.text or '').strip()

    if len(''.join((ch for ch in phone if ch.isdigit()))) < 10:

        await message.answer('❌ <b>НЕКОРЕКТНИЙ ТЕЛЕФОН.</b>\nСпробуйте ще раз у форматі +380...', parse_mode='HTML')

        return

    await state.update_data(phone=phone)

    await user_db.set_phone(message.from_user.id, phone)

    is_admin = await admin_db.is_admin(message.from_user.id)

    await message.answer('✅ Телефон збережено.', reply_markup=kb.get_main_menu(is_admin))

    await send_beans_invoice(message.from_user, message.chat.id, state, bot)

@user_router.callback_query(F.data == 'back_main_menu_only')

async def back_to_main_cb(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    is_admin = await admin_db.is_admin(callback.from_user.id)

    try:

        await callback.message.delete()

    except Exception:

        pass

    await callback.message.answer('☕️ <b>ГОЛОВНЕ МЕНЮ</b>', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

    await callback.answer()

async def back_to_main(message: Message, state: FSMContext):

    await state.clear()

    is_admin = await admin_db.is_admin(message.from_user.id)

    await message.answer('☕️ <b>ГОЛОВНЕ МЕНЮ</b>', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')
