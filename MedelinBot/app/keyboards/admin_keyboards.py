
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton

ORDER_TYPE_NAMES = {
    'takeaway': 'З собою',
    'in_house': 'В залі',
    'beans_delivery': 'Зерна (Доставка)',
    'beans_booking': 'Зерна (Самовивіз)'
}

def get_admin_main_kb(role='boss'):
    """
    Main Admin Menu Keyboard.
    Roles: owner, developer, delivery_manager, boss/admin
    """
    # 1. Orders Block
    keyboard = [
        [KeyboardButton(text='🆕 НОВІ'), KeyboardButton(text='📦 АКТИВНІ')],
    ]
    
    # 2. Content Management Block (Owner & Developer)
    if role in ('owner', 'developer', 'boss'):
        keyboard.append([KeyboardButton(text='☕️ ЗЕРНА')])
        keyboard.append([KeyboardButton(text='📍 ЛОКАЦІЇ'), KeyboardButton(text='📞 КОНТАКТИ')])
    
    # 3. System Management Block (Owner & Developer)
    if role in ('owner', 'developer'):
        keyboard.append([KeyboardButton(text='👤 ПЕРСОНАЛ'), KeyboardButton(text='📊 СТАТИСТИКА')])
    
    # 4. Settings/Info Block
    # keyboard.append([KeyboardButton(text='🏠 ГОЛОВНЕ МЕНЮ')])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_main_inline_kb(role='boss'):
    """
    Inline version of Admin Menu for message editing.
    """
    keyboard = [
        [InlineKeyboardButton(text='🆕 НОВІ', callback_data='new_orders')],
        [InlineKeyboardButton(text='📦 АКТИВНІ', callback_data='active_orders')],
    ]
    if role in ('owner', 'developer', 'boss'):
        keyboard.append([InlineKeyboardButton(text='☕️ ЗЕРНА', callback_data='beans_manage')])
        keyboard.append([InlineKeyboardButton(text='📍 ЛОКАЦІЇ', callback_data='locations_manage'), InlineKeyboardButton(text='📞 КОНТАКТИ', callback_data='contacts_manage')])
    if role in ('owner', 'developer'):
        keyboard.append([InlineKeyboardButton(text='👤 ПЕРСОНАЛ', callback_data='staff_manage'), InlineKeyboardButton(text='📊 СТАТИСТИКА', callback_data='stats_show')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_beans_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Комерційна', callback_data='beans_page_commercial'), InlineKeyboardButton(text='Спешелті', callback_data='beans_page_specialty')],
        [InlineKeyboardButton(text='➕ ДОДАТИ НОВУ КАВУ', callback_data='bean_new')],
        [InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_bean_card_kb(bean_id, category='commercial'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✏️ РЕДАГУВАТИ ПАРАМЕТРИ', callback_data=f'bean_edit_fields_{bean_id}')],
        [InlineKeyboardButton(text='📝 РЕДАГУВАТИ ВСЕ', callback_data=f'bean_full_edit_{bean_id}')],
        [InlineKeyboardButton(text='🗑 ВИДАЛИТИ', callback_data=f'bean_del_confirm_{bean_id}')],
        [InlineKeyboardButton(text='⬅️ ДО СПИСКУ', callback_data=f'beans_page_{category}')]
    ])

def get_bean_edit_fields_kb(bean_id, category='commercial'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏷 Назва', callback_data=f'bean_fedit_{bean_id}_name'), InlineKeyboardButton(text='💰 Ціна', callback_data=f'bean_fedit_{bean_id}_price')],
        [InlineKeyboardButton(text='📸 Фото', callback_data=f'bean_fedit_{bean_id}_photo'), InlineKeyboardButton(text='📈 Оцінка', callback_data=f'bean_fedit_{bean_id}_score')],
        [InlineKeyboardButton(text='🌿 Склад', callback_data=f'bean_fedit_{bean_id}_species'), InlineKeyboardButton(text='🔥 Обсмаж.', callback_data=f'bean_fedit_{bean_id}_roast')],
        [InlineKeyboardButton(text='📅 Врожай', callback_data=f'bean_fedit_{bean_id}_harvest'), InlineKeyboardButton(text='⛰ Висота', callback_data=f'bean_fedit_{bean_id}_altitude')],
        [InlineKeyboardButton(text='🧪 Обробка', callback_data=f'bean_fedit_{bean_id}_processing'), InlineKeyboardButton(text='🍓 Дескрип.', callback_data=f'bean_fedit_{bean_id}_descriptors')],
        [InlineKeyboardButton(text='📖 Опис', callback_data=f'bean_fedit_{bean_id}_description')],
        [InlineKeyboardButton(text='⬅️ НАЗАД ДО КАРТКИ', callback_data=f'bean_open_{bean_id}')]
    ])


def get_locations_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📍 СПИСОК ЛОКАЦІЙ', callback_data='locations_list')],
        [InlineKeyboardButton(text='➕ ДОДАТИ ЛОКАЦІЮ', callback_data='location_new')],
        [InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_location_card_kb(loc_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✏️ РЕДАГУВАТИ ПАРАМЕТРИ', callback_data=f'loc_edit_fields_{loc_id}')],
        [InlineKeyboardButton(text='📝 РЕДАГУВАТИ ВСЕ', callback_data=f'loc_full_edit_{loc_id}')],
        [InlineKeyboardButton(text='🗑 ВИДАЛИТИ', callback_data=f'loc_del_confirm_{loc_id}')],
        [InlineKeyboardButton(text='⬅️ ДО СПИСКУ', callback_data='locations_list')]
    ])

def get_location_edit_fields_kb(loc_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏷 Назва', callback_data=f'loc_fedit_{loc_id}_name'), InlineKeyboardButton(text='🏠 Адреса', callback_data=f'loc_fedit_{loc_id}_address')],
        [InlineKeyboardButton(text='📅 Графік', callback_data=f'loc_fedit_{loc_id}_schedule'), InlineKeyboardButton(text='📞 Телефон', callback_data=f'loc_fedit_{loc_id}_phone')],
        [InlineKeyboardButton(text='📧 Email', callback_data=f'loc_fedit_{loc_id}_email'), InlineKeyboardButton(text='🗺 Google Maps', callback_data=f'loc_fedit_{loc_id}_google_maps_url')],
        [InlineKeyboardButton(text='🪑 Столики', callback_data=f'loc_fedit_{loc_id}_max_tables'), InlineKeyboardButton(text='📸 Фото', callback_data=f'loc_fedit_{loc_id}_photo')],
        [InlineKeyboardButton(text='✨ Зручності', callback_data=f'loc_fedit_{loc_id}_amenities'), InlineKeyboardButton(text='☁️ Атмосфера', callback_data=f'loc_fedit_{loc_id}_atmosphere')],
        [InlineKeyboardButton(text='⬅️ НАЗАД ДО КАРТКИ', callback_data=f'loc_open_{loc_id}')]
    ])

def get_contacts_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ КОНТАКТ', callback_data='contact_add')],
        [InlineKeyboardButton(text='📞 СПИСОК / РЕДАГУВАННЯ', callback_data='contacts_list')],
        [InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_staff_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ ПЕРСОНАЛ', callback_data='staff_add')],
        [InlineKeyboardButton(text='👤 СПИСОК ПЕРСОНАЛУ', callback_data='staff_list')],
        [InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_active_types_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🆕 НОВІ', callback_data='new_orders')],
        [InlineKeyboardButton(text='📦 АКТИВНІ', callback_data='active_orders')],
        [InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_active_orders_list_kb(orders):
    buttons = []
    for o in orders:
        oid = str(o['_id'])
        user = o.get('user_name', 'Гість')
        type_name = ORDER_TYPE_NAMES.get(o.get('order_type'), 'Замовлення')
        buttons.append([InlineKeyboardButton(text=f"📦 {type_name} - {user}", callback_data=f"finish_order_{oid}")])
    buttons.append([InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_booking_manage_kb(order_id, user_id=-1):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ ПІДТВЕРДИТИ', callback_data=f'confirm_order_{order_id}')],
        [InlineKeyboardButton(text='❌ ВІДХИЛИТИ', callback_data=f'reject_order_{order_id}')]
    ])

def get_admin_auth_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ ПІДТВЕРДИТИ ВХІД', callback_data=f'admin_auth_confirm_{user_id}')],
        [InlineKeyboardButton(text='❌ ВІДХИЛИТИ', callback_data=f'admin_auth_reject_{user_id}')]
    ])
