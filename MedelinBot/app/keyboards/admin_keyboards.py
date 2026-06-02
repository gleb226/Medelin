
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton

ORDER_TYPE_NAMES = {
    'takeaway': 'З собою',
    'in_house': 'В залі',
    'beans_delivery': 'Зерна (Доставка)',
    'beans_booking': 'Зерна (Самовивіз)'
}

def get_admin_main_kb(role='boss'):
    keyboard = [
        [KeyboardButton(text='🛍 АКТИВНІ ЗАМОВЛЕННЯ')],
        [KeyboardButton(text='☕️ КЕРУВАННЯ ЗЕРНАМИ'), KeyboardButton(text='📍 ЛОКАЦІЇ')],
        [KeyboardButton(text='📞 КОНТАКТИ'), KeyboardButton(text='👤 ПЕРСОНАЛ')]
    ]
    if role in ('boss', 'owner', 'developer'):
        keyboard.append([KeyboardButton(text='📊 СТАТИСТИКА')])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_beans_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ СОРТ', callback_data='bean_add')],
        [InlineKeyboardButton(text='📜 СПИСОК ЗЕРЕН', callback_data='beans_list')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_locations_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ ЛОКАЦІЮ', callback_data='location_add')],
        [InlineKeyboardButton(text='📍 СПИСОК ЛОКАЦІЙ', callback_data='locations_list')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_contacts_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ КОНТАКТ', callback_data='contact_add')],
        [InlineKeyboardButton(text='📞 СПИСОК КОНТАКТІВ', callback_data='contacts_list')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_staff_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ ПЕРСОНАЛ', callback_data='staff_add')],
        [InlineKeyboardButton(text='👤 СПИСОК ПЕРСОНАЛУ', callback_data='staff_list')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

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
