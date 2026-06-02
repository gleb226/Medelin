
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton

EMOJI_MAP = {'Кава': '☕', 'До кави': '➕', 'Декаф': '🍃', 'Мілк': '🥛', 'Десерти': '🍰', 'Напої': '🍹', 'Масала': '🌶️', 'Фреш': '🍊', 'Чай': '🍵', 'Матча': '🍵', 'Какао': '🍫', 'Кава в зернах': '☕'}

def get_cat_with_emoji(cat):

    cat_s = cat.strip()

    for emoji in EMOJI_MAP.values():

        cat_s = cat_s.replace(emoji, '').strip()

    emoji = EMOJI_MAP.get(cat_s, '🍽️')

    return f'{emoji} {cat_s}'

ROLE_NAMES = {
    'developer': 'Розробник',
    'owner': 'Власник',
    'boss': 'Власник',
    'delivery_manager': 'Менеджер доставки',
    'courier': 'Курʼєр'
}

ORDER_TYPE_NAMES = {
    'in_house': 'В закладі',
    'takeaway': 'На виніс',
    'booking': 'Бронювання',
    'order_with_booking': 'Бронь + замовлення',
    'beans_booking': 'Зерно (самовивіз)',
    'beans_delivery': 'Нова Пошта'
}

def get_main_admin_menu(is_on_shift: bool=False, role: str='delivery_manager'):

    keyboard = []

    role = role.lower()

    # Почати зміну тільки для менеджерів доставки
    if role == 'delivery_manager':

        shift_text = '🔴 ЗАВЕРШИТИ ЗМІНУ' if is_on_shift else '🟢 ПОЧАТИ ЗМІНУ'

        keyboard.append([KeyboardButton(text=shift_text)])

    if role in ('boss', 'owner', 'developer', 'delivery_manager'):
        keyboard.append([KeyboardButton(text='🆕 НОВІ ЗАПИТИ'), KeyboardButton(text='⚡️ АКТИВНІ')])


    if role in ('boss', 'owner', 'developer'):
        # Тільки КОМАНДА (ПІДТРИМКУ прибрали)
        keyboard.append([KeyboardButton(text='👥 КОМАНДА')])

    if role in ('boss', 'owner', 'developer'):

        keyboard.append([KeyboardButton(text='☕ ЗЕРНО')])

        keyboard.append([KeyboardButton(text='📍 ЛОКАЦІЇ'), KeyboardButton(text='📱 СОЦМЕРЕЖІ')])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_active_types_kb():

    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🛍 АКТИВНІ ЗАМОВЛЕННЯ', callback_data='active_orders')], [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]])

def get_active_bookings_list_kb(bookings):

    buttons = []

    for b in bookings:

        buttons.append([InlineKeyboardButton(text=f"✅ {b['fullname']} ({b['date_time_str']})", callback_data=f"finish_book_{b['_id']}")])

    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='active_panel')])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_active_orders_list_kb(orders):

    buttons = []

    for o in orders:
        o_type = ORDER_TYPE_NAMES.get(o['order_type'], o['order_type'])
        buttons.append([InlineKeyboardButton(text=f"✅ {o['fullname']} ({o_type})", callback_data=f"finish_order_{o['_id']}")])

    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='active_panel')])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_management_kb(is_privileged: bool=False):

    buttons = []

    buttons.append([InlineKeyboardButton(text='➕ ДОДАТИ ПЕРСОНАЛ', callback_data='adm_add_new')])

    buttons.append([InlineKeyboardButton(text='🗑 ВИДАЛИТИ ДОСТУП', callback_data='adm_remove')])

    buttons.append([InlineKeyboardButton(text='📋 СПИСОК КОМАНДИ', callback_data='adm_list')])

    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_roles_kb(caller_role: str):

    roles = []

    if caller_role == 'developer':

        roles = [('Власник', 'boss'), ('Менеджер доставки', 'delivery_manager')]

    elif caller_role in ('owner', 'boss'):

        roles = [('Менеджер доставки', 'delivery_manager')]

    buttons = []

    for label, r in roles:

        buttons.append([InlineKeyboardButton(text=label, callback_data=f"set_role_{r}")])

    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='adm_add_new')])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admins_to_remove_kb(admins):

    buttons = []

    for uid, user, name, role in admins:

        buttons.append([InlineKeyboardButton(text=f"🗑 {name} (@{user or '—'})", callback_data=f"adm_del_yes_{uid}")])

    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='adm_remove')])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_booking_manage_kb(order_id, user_id=None):

    buttons = []

    buttons.append([InlineKeyboardButton(text='✅ ПРИЙНЯТИ', callback_data=f'adm2_confirm_{order_id}'), InlineKeyboardButton(text='❌ ВІДХИЛИТИ', callback_data=f'adm2_cancel_{order_id}')])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_beans_manage_kb():

    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='➕ ДОДАТИ СОРТ', callback_data='bean_add')], [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]])

def get_locations_manage_kb():

    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='➕ ДОДАТИ ЛОКАЦІЮ', callback_data='loc_add')], [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]])

def get_socials_manage_kb():

    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='➕ ДОДАТИ СОЦМЕРЕЖУ', callback_data='soc_add')], [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]])

def get_admin_login_confirm_kb(user_id: int):

    return InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text='✅ ПІДТВЕРДИТИ ВХІД', callback_data=f'admin_auth_confirm_{user_id}')],

        [InlineKeyboardButton(text='❌ ВІДХИЛИТИ', callback_data=f'admin_auth_reject_{user_id}')]

    ])
