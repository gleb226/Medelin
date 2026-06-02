
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton

ORDER_TYPE_NAMES = {
    'takeaway': 'З собою',
    'in_house': 'В залі',
    'beans_delivery': 'Зерна (Доставка)',
    'beans_booking': 'Зерна (Самовивіз)'
}

def get_admin_main_kb(role='boss'):
    kb = [
        [InlineKeyboardButton(text='🛍 АКТИВНІ ЗАМОВЛЕННЯ', callback_data='active_panel')],
        [InlineKeyboardButton(text='☕️ КЕРУВАННЯ ЗЕРНАМИ', callback_data='beans_manage')]
    ]
    if role in ('boss', 'owner', 'developer'):
        kb.append([InlineKeyboardButton(text='📊 СТАТИСТИКА', callback_data='admin_stats')])
        kb.append([InlineKeyboardButton(text='👤 АДМІНІСТРАТОРИ', callback_data='admins_manage')])
        kb.append([InlineKeyboardButton(text='📍 ЛОКАЦІЇ', callback_data='locations_manage')])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_active_types_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛍 АКТИВНІ ЗАМОВЛЕННЯ', callback_data='active_orders')],
        [InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='admin_panel_back')]
    ])

def get_active_orders_list_kb(orders):
    buttons = []
    for o in orders:
        o_type = ORDER_TYPE_NAMES.get(o['order_type'], o['order_type'])
        buttons.append([InlineKeyboardButton(text=f"✅ {o['fullname']} ({o_type})", callback_data=f"finish_order_{o['_id']}")])
    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='active_panel')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_beans_manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ДОДАТИ СОРТ', callback_data='bean_add')],
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
