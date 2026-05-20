
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from app.common.config import WORK_START_HOUR, WORK_END_HOUR

from app.databases.location_database import location_db

from app.databases.socials_database import socials_db

import datetime

import hashlib

BTN_BOOK_TABLE = '📅 ЗАБРОНЮВАТИ СТОЛИК'

BTN_MENU = '🍽️ МЕНЮ / ЗАМОВЛЕННЯ'

BTN_BEANS = '☕️ КАВА В ЗЕРНАХ'

BTN_LOCATIONS = '📍 НАШІ ЗАКЛАДИ'

BTN_CONTACTS = '☎️ КОНТАКТИ'

BTN_ADMIN = '🔐 АДМІН-ПАНЕЛЬ'

def _clamp_hour(hour: int, *, allow_24: bool=False) -> int:

    try:

        hour = int(hour)

    except Exception:

        return 0

    if allow_24 and hour == 24:

        return 24

    return max(0, min(23, hour))

def cat_key(category: str) -> str:

    return hashlib.blake2s(category.encode('utf-8'), digest_size=6).hexdigest()

def get_main_menu(is_admin: bool=False):

    keyboard = [[KeyboardButton(text=BTN_BOOK_TABLE)], [KeyboardButton(text=BTN_MENU)], [KeyboardButton(text=BTN_BEANS)], [KeyboardButton(text=BTN_LOCATIONS), KeyboardButton(text=BTN_CONTACTS)]]

    if is_admin:

        keyboard.append([KeyboardButton(text=BTN_ADMIN)])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_date_kb():

    today = datetime.date.today()

    tomorrow = today + datetime.timedelta(days=1)

    day_after = today + datetime.timedelta(days=2)

    keyboard = [[InlineKeyboardButton(text=f"🗓 Сьогодні, {today.strftime('%d.%m')}", callback_data=f'book_date_{today.isoformat()}')], [InlineKeyboardButton(text=f"🗓 Завтра, {tomorrow.strftime('%d.%m')}", callback_data=f'book_date_{tomorrow.isoformat()}')], [InlineKeyboardButton(text=f"🗓 Післязавтра, {day_after.strftime('%d.%m')}", callback_data=f'book_date_{day_after.isoformat()}')]]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_time_kb(selected_date: datetime.date | None=None):

    times = []

    now = datetime.datetime.now()

    selected_date = selected_date or now.date()

    start_hour = _clamp_hour(WORK_START_HOUR)

    end_hour_raw = _clamp_hour(WORK_END_HOUR, allow_24=True)

    t = datetime.datetime.combine(selected_date, datetime.time(hour=start_hour, minute=0))

    if selected_date == now.date():

        t = max(t, _ceil_to_next_half_hour(now))

    if end_hour_raw == 24:

        closing = datetime.datetime.combine(selected_date, datetime.time(hour=0, minute=0)) + datetime.timedelta(days=1)

    else:

        closing = datetime.datetime.combine(selected_date, datetime.time(hour=_clamp_hour(end_hour_raw), minute=0))

    end = (closing - datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    while t <= end:

        times.append(t.strftime('%H:%M'))

        t += datetime.timedelta(minutes=30)

    keyboard = []

    cols = 3

    for i in range(0, len(times), cols):

        row = [InlineKeyboardButton(text=tm, callback_data=f'book_time_{tm}') for tm in times[i:i + cols]]

        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def _ceil_to_next_half_hour(dt: datetime.datetime) -> datetime.datetime:

    dt = dt.replace(second=0, microsecond=0)

    minute = dt.minute

    if minute == 0 or minute == 30:

        return dt

    if minute < 30:

        return dt.replace(minute=30)

    return (dt + datetime.timedelta(hours=1)).replace(minute=0)

async def get_locations_kb():

    keyboard = []

    row = []

    locations = await location_db.get_all_locations()

    for loc in locations:

        loc_id = str(loc['_id'])

        name = loc['name'].replace('Medelin ', '')

        row.append(InlineKeyboardButton(text=f'📍 {name}', callback_data=f'loc_{loc_id}'))

        if len(row) == 2:

            keyboard.append(row)

            row = []

    if row:

        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_item_options_kb(item_id, item_name, options, current_options=None, current_price=None):
    current_options = current_options or []
    btn_text = f'✅ ДОДАТИ В КОШИК ({current_price}₴)' if current_price else '✅ ДОДАТИ В КОШИК'
    keyboard = [[InlineKeyboardButton(text=btn_text, callback_data=f'add_to_cart_{item_id}')]]
    
    # Сортуємо опції за типами
    caffeine_opts = [o for o in options if o.get('type') == 'caffeine']
    milk_opts = [o for o in options if o.get('type') == 'milk']
    addon_opts = [o for o in options if o.get('type') == 'addon']

    if caffeine_opts:
        row = []
        for o in caffeine_opts:
            name = o['name']
            is_active = any(name in opt for opt in current_options) or (name == 'Стандарт' and not any(co['name'] in opt for co in caffeine_opts for opt in current_options))
            # Для простоти, якщо нічого не обрано, Стандарт вважається обраним
            prefix = '✅ ' if is_active else ''
            row.append(InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"opt_{item_id}_caf:{name}"))
        keyboard.append(row)

    if milk_opts:
        # Для бота показуємо лише стандартні варіанти молока
        filtered_milk = [o for o in milk_opts if o['name'] in ['Звичайне', 'Безлактозне']]
        row = []
        for o in filtered_milk:
            name = o['name']
            # Позначаємо "Звичайне" як активне, якщо нічого не обрано
            is_active = any(name in opt for opt in current_options) or (name == 'Звичайне' and not any(f"milk:" in opt for opt in current_options))
            prefix = '✅ ' if is_active else ''
            row.append(InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"opt_{item_id}_milk:{name}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row: keyboard.append(row)

    if addon_opts:
        row = []
        for o in addon_opts:
            name = o['name']
            price = o.get('add_price', 0)
            is_active = any(name in opt for opt in current_options)
            prefix = '✅ ' if is_active else ''
            price_text = f" (+{price}₴)" if price > 0 else ""
            row.append(InlineKeyboardButton(text=f"{prefix}{name}{price_text}", callback_data=f"opt_{item_id}_add:{name}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row: keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data=f'item_{item_id}')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_categories_kb(categories, booking_mode=False, cart_count=0):

    keyboard = []

    row = []

    emoji_map = {'Кава': '☕', 'До кави': '➕', 'Декаф': '🍃', 'Мілк': '🥛', 'Десерти': '🍰', 'Напої': '🍹', 'Масала': '🌶️', 'Фреш': '🍊', 'Чай': '🍵', 'Напої': '🥤', 'Матча': '🍵', 'Какао': '🍫'}

    fixed_order = ['Кава', 'До Кави', 'Декаф', 'Десерти', 'Напої', 'Масала', 'Фреш', 'Чай', 'Мілк', 'Матча', 'Какао']

    def normalize_cat(cat):

        cat = str(cat)

        for emoji in emoji_map.values():

            cat = cat.replace(emoji, '').strip()

        if cat == 'Мільк':

            return 'Мілк'

        return cat

    sorted_cats = sorted(categories, key=lambda x: fixed_order.index(normalize_cat(x)) if normalize_cat(x) in fixed_order else 999)

    filtered_cats = [c for c in sorted_cats if 'зерн' not in c.lower()]

    for cat in filtered_cats:

        cat_s = normalize_cat(cat)

        emoji = emoji_map.get(cat_s, '🍽️')

        row.append(InlineKeyboardButton(text=f'{emoji} {cat_s}', callback_data=f'cat_{cat_key(cat_s)}'))

        if len(row) == 2:

            keyboard.append(row)

            row = []

    if row:

        keyboard.append(row)

    if cart_count > 0 and (not booking_mode):

        keyboard.append([InlineKeyboardButton(text=f'🛍 КОШИК ({cart_count})', callback_data='checkout_order')])

    bt, bd = ('⬅️ ДО БРОНІ', 'back_to_booking_summary') if booking_mode else ('🏠 НА ГОЛОВНУ', 'back_main_menu_only')

    keyboard.append([InlineKeyboardButton(text=bt, callback_data=bd)])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_items_kb(items, category, cart_count=0, booking_mode=False):
    keyboard = []
    
    # Фільтруємо "не стандартні" версії за назвою, якщо вони є окремими позиціями
    filtered_items = []
    cat_lower = category.lower().strip()
    is_customizable_cat = any(x in cat_lower for x in ['кава', 'мілк', 'матча', 'какао'])
    
    for item in items:
        name_lower = item[1].lower()
        if 'подвій' in name_lower or 'double' in name_lower:
            continue
        
        # Фільтруємо flavored версії для категорій, де є вибір молока/сиропів
        if is_customizable_cat:
            if any(x in name_lower for x in ['бананов', 'ванільн', 'полуничн', 'шоколадн', 'кокосов', 'мигдалев', 'вівсян', 'великий', 'солев', 'солон']):
                # Якщо це flavored або не стандартна версія, ми її пропускаємо
                # Винятки для базових напоїв, якщо вони містять ці слова
                if name_lower not in ['какао', 'матча лате', 'матча тонік']:
                    continue
                
        filtered_items.append(item)

    sorted_items = sorted(filtered_items, key=lambda x: x[1])
    row = []
    for item in sorted_items:

        btn_text = f'{truncate(item[1])} - {item[2]}'

        row.append(InlineKeyboardButton(text=btn_text, callback_data=f'item_{item[0]}'))

        if len(row) == 2:

            keyboard.append(row)

            row = []

    if row:

        keyboard.append(row)

    if cart_count > 0 and (not booking_mode):

        keyboard.append([InlineKeyboardButton(text=f'🛍 КОШИК ({cart_count})', callback_data='checkout_order')])

    keyboard.append([InlineKeyboardButton(text='⬅️ ДО КАТЕГОРІЙ', callback_data='back_cats')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def truncate(text, length=22):

    if len(text) <= length:

        return text

    return text[:length - 1] + '…'

def get_item_actions_kb(item_id):

    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='➕ ДОДАТИ В КОШИК', callback_data=f'add_to_cart_{item_id}')], [InlineKeyboardButton(text='⬅️ ДО СПИСКУ', callback_data='back_items')]])

def get_beans_kb(items):

    keyboard = []

    row = []

    for item in items:

        name = truncate(item[1], 25)

        row.append(InlineKeyboardButton(text=f'☕️ {name}', callback_data=f'bean_{item[0]}'))

        if len(row) == 2:

            keyboard.append(row)

            row = []

    if row:

        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_beans_weight_kb():

    weights = ['250', '500', '1000']

    keyboard = [[InlineKeyboardButton(text=f'⚖️ {w} г', callback_data=f'bean_w_{w}') for w in weights]]

    keyboard.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='bean_back')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_beans_delivery_kb():

    keyboard = [

        [InlineKeyboardButton(text='🚶 САМОВИВІЗ', callback_data='bean_del_pickup')],

        [InlineKeyboardButton(text='🚚 НОВА ПОШТА', callback_data='bean_del_np')],

        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='bean_back')]

    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_np_cities_kb(cities: list):

    keyboard = []

    for city in cities:

        city_name = city.get('Present', '')

        city_ref = city.get('DeliveryCity', '') or city.get('Ref', '')

        if city_name and city_ref:

            keyboard.append([InlineKeyboardButton(text=city_name, callback_data=f"np_city_{city_ref}")])

    keyboard.append([InlineKeyboardButton(text='⬅️ ПОШУК ЗНОВУ', callback_data='bean_del_np')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_np_warehouses_kb(warehouses: list, page: int = 0):

    keyboard = []

    per_page = 8

    start = page * per_page

    end = start + per_page

    current_batch = warehouses[start:end]

    for wh in current_batch:

        wh_name = wh.get('Description', '')

        wh_ref = wh.get('Ref', '')

        if wh_name and wh_ref:

            short_name = truncate(wh_name, 35)

            keyboard.append([InlineKeyboardButton(text=short_name, callback_data=f"np_wh_{wh_ref}")])

    nav_row = []

    if page > 0:

        nav_row.append(InlineKeyboardButton(text='⬅️', callback_data=f"np_wh_page_{page-1}"))

    if end < len(warehouses):

        nav_row.append(InlineKeyboardButton(text='➡️', callback_data=f"np_wh_page_{page+1}"))

    if nav_row:

        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text='⬅️ ЗМІНИТИ МІСТО', callback_data='bean_del_np')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_location_request_kb():

    keyboard = [[KeyboardButton(text='📍 НАДІСЛАТИ ГЕОЛОКАЦІЮ', request_location=True)], [KeyboardButton(text='🏠 НА ГОЛОВНУ')]]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_phone_kb():

    keyboard = [[KeyboardButton(text='📱 НАДІСЛАТИ НОМЕР', request_contact=True)], [KeyboardButton(text='🏠 НА ГОЛОВНУ')]]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

async def get_contact_kb():

    socials = await socials_db.get_all_socials()

    keyboard = []

    row = []

    for s in socials:

        keyboard.append([InlineKeyboardButton(text=s['name'].upper(), url=s['url'])])

    keyboard.append([InlineKeyboardButton(text='📞 ТЕЛЕФОН', callback_data='contact_phone')])

    keyboard.append([InlineKeyboardButton(text='✉️ EMAIL', callback_data='contact_email')])

    keyboard.append([InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_locations_info_kb():

    keyboard = []

    row = []

    locations = await location_db.get_all_locations()

    for loc in locations:

        loc_id = str(loc['_id'])

        row.append(InlineKeyboardButton(text=f"📍 {loc['name']}", callback_data=f'locinfo_{loc_id}'))

        if len(row) == 2:

            keyboard.append(row)

            row = []

    if row:

        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
