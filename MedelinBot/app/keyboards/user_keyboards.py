
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from app.common.config import WORK_START_HOUR, WORK_END_HOUR

from app.databases.location_database import location_db

from app.databases.contacts_database import contacts_db

import datetime

import hashlib

def truncate(text, length):
    return text[:length] + '..' if len(text) > length else text

BTN_BEANS = '☕️ КАВА В ЗЕРНАХ'

BTN_LOCATIONS = '📍 НАШІ ЗАКЛАДИ'

BTN_CONTACTS = '📞 КОНТАКТИ'

BTN_ADMIN = '🔐 АДМІН-ПАНЕЛЬ'

def _clamp_hour(hour: int, *, allow_24: bool=False) -> int:

    try:

        hour = int(hour)

    except Exception:

        return 0

    if allow_24 and hour == 24:

        return 24

    return max(0, min(23, hour))

def get_main_menu(is_admin: bool=False):
    keyboard = [
        [KeyboardButton(text=BTN_BEANS)],
        [KeyboardButton(text=BTN_LOCATIONS), KeyboardButton(text=BTN_CONTACTS)]
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

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

def get_beans_kb(items):
    keyboard = []
    row = []
    for item in items:
        name = truncate(item[1], 18)
        row.append(InlineKeyboardButton(text=f'☕️ {name}', callback_data=f'bean_{item[0]}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_beans_weight_kb():
    keyboard = [
        [InlineKeyboardButton(text='⚖️ 250г', callback_data='bean_w_250')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='bean_back')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_beans_delivery_kb():
    keyboard = [
        [InlineKeyboardButton(text='🚚 НОВА ПОШТА', callback_data='bean_del_np')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='bean_back')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_beans_payment_kb():
    keyboard = [
        [InlineKeyboardButton(text='💳 ОПЛАТИТИ ЗАРАЗ', callback_data='bean_pay_card')],
        [InlineKeyboardButton(text='📦 НАКЛАДЕНИЙ ПЛАТІЖ', callback_data='bean_pay_cash')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='bean_back')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_location_request_kb():
    keyboard = [[KeyboardButton(text='📍 НАДІСЛАТИ ГЕОЛОКАЦІЮ', request_location=True)], [KeyboardButton(text='🏠 НА ГОЛОВНУ')]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_np_cities_kb(cities):
    keyboard = []
    for city in cities[:8]:
        name = city.get('Present', 'Місто')
        ref = city.get('DeliveryCity', '') or city.get('Ref', '')
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f'np_city_{ref}')])
    keyboard.append([InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_np_warehouses_kb(warehouses, page=0):
    keyboard = []
    per_page = 6
    start = page * per_page
    end = start + per_page
    
    for wh in warehouses[start:end]:
        name = wh.get('Description', 'Відділення')
        ref = wh.get('Ref', '')
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f'np_wh_{ref}')])
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text='⬅️', callback_data=f'np_wh_page_{page-1}'))
    if end < len(warehouses):
        nav_row.append(InlineKeyboardButton(text='➡️', callback_data=f'np_wh_page_{page+1}'))
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_phone_kb():
    keyboard = [[KeyboardButton(text='☎️ НАДІСЛАТИ НОМЕР ТЕЛЕФОНУ', request_contact=True)], [KeyboardButton(text='🏠 НА ГОЛОВНУ')]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

async def get_contact_kb():
    socials = await contacts_db.get_all_contacts()
    keyboard = []
    row = []

    def get_social_icon(url, name):
        u = str(url).lower()
        n = str(name).lower()
        if 'instagram' in u or 'insta' in n or 'інста' in n: return '📸'
        if 'facebook' in u or 'fb' in n or 'фейс' in n: return '📘'
        if 'telegram' in u or 't.me' in u or 'тг' in n: return '✈️'
        if 'tiktok' in u or 'тікток' in n: return '🎵'
        if 'youtube' in u or 'ютуб' in n: return '🎬'
        if 'viber' in u or 'вайбер' in n: return '💜'
        return '🌐'

    for s in socials:
        icon = get_social_icon(s['url'], s['name'])
        row.append(InlineKeyboardButton(text=f"{icon} {s['name'].upper()}", url=s['url']))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text='📞 +380503775906', callback_data='contact_phone'),
        InlineKeyboardButton(text='✉️ EMAIL', callback_data='contact_email')
    ])
    keyboard.append([
        InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_locations_info_kb():
    keyboard = []
    row = []
    locations = await location_db.get_all_locations()

    for loc in locations:
        loc_id = str(loc['_id'])
        name = loc['name'].replace('Medelin ', '')
        row.append(InlineKeyboardButton(text=f"📍 {name}", callback_data=f'locinfo_{loc_id}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text='🏠 НА ГОЛОВНУ', callback_data='back_main_menu_only')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
