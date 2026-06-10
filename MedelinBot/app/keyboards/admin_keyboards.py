
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
        [KeyboardButton(text='🆕 НОВІ ЗАМОВЛЕННЯ'), KeyboardButton(text='📦 АКТИВНІ ЗАМОВЛЕННЯ')],
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

def get_beans_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ СОРТ', callback_data='bean_add')],
        [InlineKeyboardButton(text='📜 СПИСОК / РЕДАГУВАННЯ', callback_data='beans_list')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_locations_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ ЛОКАЦІЮ', callback_data='location_add')],
        [InlineKeyboardButton(text='📍 СПИСОК / РЕДАГУВАННЯ', callback_data='locations_list')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_contacts_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ КОНТАКТ', callback_data='contact_add')],
        [InlineKeyboardButton(text='📞 СПИСОК / РЕДАГУВАННЯ', callback_data='contacts_list')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_staff_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ ПЕРСОНАЛ', callback_data='staff_add')],
        [InlineKeyboardButton(text='👤 СПИСОК ПЕРСОНАЛУ', callback_data='staff_list')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_active_types_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🆕 НОВІ (БЕЗ ОПЛАТИ / ПЕРЕВІРКА)', callback_data='new_orders')],
        [InlineKeyboardButton(text='📦 АКТИВНІ (В РОБОТІ)', callback_data='active_orders')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_active_orders_list_kb(orders):
    buttons = []
    for o in orders:
        oid = str(o['_id'])
        user = o.get('user_name', 'Гість')
        type_name = ORDER_TYPE_NAMES.get(o.get('order_type'), 'Замовлення')
        buttons.append([InlineKeyboardButton(text=f"📦 {type_name} - {user}", callback_data=f"finish_order_{oid}")])
    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')])
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
