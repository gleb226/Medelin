
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton

ORDER_TYPE_NAMES = {
    'takeaway': 'З собою',
    'in_house': 'В залі',
    'beans_delivery': 'Зерна (Доставка)',
    'beans_booking': 'Зерна (Самовивіз)'
}

def get_admin_main_kb(role='admin'):
    """
    Main Admin Menu Keyboard.
    Roles: owner, developer, admin
    """
    # 1. Orders Block (All roles see this)
    keyboard = [
        [KeyboardButton(text='🆕 НОВІ'), KeyboardButton(text='📦 АКТИВНІ')],
    ]
    
    # 2. Content & Staff Management (Owner & Developer only)
    if role in ('owner', 'developer'):
        keyboard.append([KeyboardButton(text='☕️ ЗЕРНА')])
        keyboard.append([KeyboardButton(text='📍 ЛОКАЦІЇ'), KeyboardButton(text='📞 КОНТАКТИ')])
        keyboard.append([KeyboardButton(text='👤 ПЕРСОНАЛ')])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_main_inline_kb(role='admin'):
    """
    Inline version of Admin Menu for message editing.
    """
    keyboard = [
        [InlineKeyboardButton(text='🆕 НОВІ', callback_data='new_orders')],
        [InlineKeyboardButton(text='📦 АКТИВНІ', callback_data='active_orders')],
    ]
    if role in ('owner', 'developer'):
        keyboard.append([InlineKeyboardButton(text='☕️ ЗЕРНА', callback_data='beans_manage')])
        keyboard.append([InlineKeyboardButton(text='📍 ЛОКАЦІЇ', callback_data='locations_manage'), InlineKeyboardButton(text='📞 КОНТАКТИ', callback_data='contacts_manage')])
        keyboard.append([InlineKeyboardButton(text='👤 ПЕРСОНАЛ', callback_data='staff_manage')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_beans_manage_kb(role='owner'):
    kb = [
        [InlineKeyboardButton(text='Комерційна', callback_data='beans_page_commercial'), InlineKeyboardButton(text='Спешелті', callback_data='beans_page_specialty')],
    ]
    if role != 'developer':
        kb.append([InlineKeyboardButton(text='➕ ДОДАТИ НОВУ КАВУ', callback_data='bean_new')])
    kb.append([InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_bean_card_kb(bean_id, category='commercial', is_specialty=False, role='owner'):
    buttons = []
    if role != 'developer':
        buttons.append([InlineKeyboardButton(text='✏️ РЕДАГУВАТИ', callback_data=f'bean_edit_fields_{bean_id}')])
        if is_specialty:
            buttons.append([InlineKeyboardButton(text='📦 ПОПОВНИТИ ЗАПАС', callback_data=f'bean_restock_{bean_id}')])
        buttons.append([InlineKeyboardButton(text='🗑 ВИДАЛИТИ', callback_data=f'bean_del_confirm_{bean_id}')])
    
    buttons.append([InlineKeyboardButton(text='⬅️ ДО СПИСКУ', callback_data=f'beans_page_{category}')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_bean_edit_fields_kb(bean_id, category='commercial'):
    rows = [
        [InlineKeyboardButton(text='🏷 Назва', callback_data=f'bean_fedit_{bean_id}_name'), InlineKeyboardButton(text='💰 Ціна', callback_data=f'bean_fedit_{bean_id}_price')],
        [InlineKeyboardButton(text='📸 Фото', callback_data=f'bean_fedit_{bean_id}_photo')]
    ]
    
    # Hide quality score for commercial coffee
    if category == 'specialty':
        rows[1].append(InlineKeyboardButton(text='📈 Оцінка', callback_data=f'bean_fedit_{bean_id}_score'))
    
    rows.extend([
        [InlineKeyboardButton(text='🌿 Склад', callback_data=f'bean_fedit_{bean_id}_species'), InlineKeyboardButton(text='🔥 Обсмаж.', callback_data=f'bean_fedit_{bean_id}_roast')],
        [InlineKeyboardButton(text='📅 Врожай', callback_data=f'bean_fedit_{bean_id}_harvest'), InlineKeyboardButton(text='⛰ Висота', callback_data=f'bean_fedit_{bean_id}_altitude')],
        [InlineKeyboardButton(text='🧪 Обробка', callback_data=f'bean_fedit_{bean_id}_processing'), InlineKeyboardButton(text='🍓 Дескрип.', callback_data=f'bean_fedit_{bean_id}_descriptors')],
        [InlineKeyboardButton(text='📖 Опис', callback_data=f'bean_fedit_{bean_id}_description')],
        [InlineKeyboardButton(text='⬅️ НАЗАД ДО КАРТКИ', callback_data=f'bean_open_{bean_id}')]
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_locations_manage_kb(role='owner'):
    kb = [[InlineKeyboardButton(text='📍 СПИСОК ЛОКАЦІЙ', callback_data='locations_list')]]
    if role != 'developer':
        kb.append([InlineKeyboardButton(text='➕ ДОДАТИ ЛОКАЦІЮ', callback_data='location_new')])
    kb.append([InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_location_card_kb(loc_id, role='owner'):
    buttons = []
    if role != 'developer':
        buttons.append([InlineKeyboardButton(text='✏️ РЕДАГУВАТИ', callback_data=f'loc_edit_fields_{loc_id}')])
        buttons.append([InlineKeyboardButton(text='🗑 ВИДАЛИТИ', callback_data=f'loc_del_confirm_{loc_id}')])
    buttons.append([InlineKeyboardButton(text='⬅️ ДО СПИСКУ', callback_data='locations_list')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_location_edit_fields_kb(loc_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏷 Назва', callback_data=f'loc_fedit_{loc_id}_name'), InlineKeyboardButton(text='🏠 Адреса', callback_data=f'loc_fedit_{loc_id}_address')],
        [InlineKeyboardButton(text='📅 Графік', callback_data=f'loc_fedit_{loc_id}_schedule')],
        [InlineKeyboardButton(text='🗺 Google Maps', callback_data=f'loc_fedit_{loc_id}_google_maps_url'), InlineKeyboardButton(text='📸 Фото', callback_data=f'loc_fedit_{loc_id}_photo')],
        [InlineKeyboardButton(text='✨ Зручності', callback_data=f'loc_fedit_{loc_id}_amenities'), InlineKeyboardButton(text='📝 Опис', callback_data=f'loc_fedit_{loc_id}_atmosphere')],
        [InlineKeyboardButton(text='⬅️ НАЗАД ДО КАРТКИ', callback_data=f'loc_open_{loc_id}')]
    ])

def get_contacts_manage_kb(role='owner'):
    kb = [[InlineKeyboardButton(text='📞 СПИСОК КОНТАКТІВ', callback_data='contacts_list')]]
    if role != 'developer':
        kb.append([InlineKeyboardButton(text='➕ ДОДАТИ КОНТАКТ', callback_data='contact_new')])
    kb.append([InlineKeyboardButton(text='⬅️ ПОВЕРНУТИСЯ НАЗАД', callback_data='admin_panel_back')])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_contact_card_kb(contact_id, role='owner'):
    buttons = []
    if role != 'developer':
        buttons.append([InlineKeyboardButton(text='✏️ РЕДАГУВАТИ', callback_data=f'con_edit_fields_{contact_id}')])
        buttons.append([InlineKeyboardButton(text='🗑 ВИДАЛИТИ', callback_data=f'con_del_confirm_{contact_id}')])
    buttons.append([InlineKeyboardButton(text='⬅️ ДО СПИСКУ', callback_data='contacts_list')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_contact_edit_fields_kb(contact_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏷 Назва', callback_data=f'con_fedit_{contact_id}_name'), InlineKeyboardButton(text='🔗 URL / Дані', callback_data=f'con_fedit_{contact_id}_url')],
        [InlineKeyboardButton(text='⬅️ НАЗАД ДО КАРТКИ', callback_data=f'con_open_{contact_id}')]
    ])

def get_staff_manage_kb(role='owner'):
    # Developer and Owner can add staff (Developer adds Owners, Owner adds Admins)
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

def get_booking_manage_kb(order_id, user_id=-1, role='admin'):
    if role == 'developer':
        return None # Developer sees no action buttons
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ ПІДТВЕРДИТИ', callback_data=f'confirm_order_{order_id}')],
        [InlineKeyboardButton(text='❌ ВІДХИЛИТИ', callback_data=f'reject_order_{order_id}')]
    ])

def get_active_finish_kb(order_id, role='admin'):
    if role == 'developer':
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ ЗАВЕРШИТИ', callback_data=f'finish_order_{order_id}')]
    ])

def get_admin_auth_kb(user_id, code=None):
    suffix = f'{user_id}_{code}' if code else str(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ ПІДТВЕРДИТИ ВХІД', callback_data=f'admin_auth_confirm_{suffix}')],
        [InlineKeyboardButton(text='❌ ВІДХИЛИТИ', callback_data=f'admin_auth_reject_{suffix}')]
    ])
