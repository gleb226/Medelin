
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from app.databases.orders_database import orders_db

from app.databases.active_orders_database import active_orders_db

from app.databases.admin_database import admin_db

from app.databases.user_database import user_db

from app.databases.location_database import location_db

from app.databases.contacts_database import contacts_db

from app.databases.coffee_beans_database import coffee_beans_db

import app.keyboards.admin_keyboards as akb

from app.utils.data_cache import public_data_cache

from app.utils.message_utils import safe_edit_message

from app.common.config import DEVELOPER_IDS

from app.databases.mongo_client import get_db

import logging

import html

logger = logging.getLogger(__name__)

admin_router = Router()

class AdminStates(StatesGroup):
    adding_admin_id = State()
    adding_admin_role = State()
    choosing_admin_locations = State()
    adding_bean_name = State()
    adding_bean_price = State()
    adding_bean_desc = State()
    adding_location_name = State()
    adding_location_address = State()

async def get_user_role(user_id: int) -> str:
    if str(user_id) in DEVELOPER_IDS: return 'developer'
    db = await get_db()
    admin = await db.admins.find_one({'user_id': int(user_id)})
    return admin.get('role', 'user') if admin else 'user'

@admin_router.message(F.text == '🔐 АДМІН-ПАНЕЛЬ')
async def show_admin_panel(message: Message):
    role = await get_user_role(message.from_user.id)
    if role == 'user': return
    await message.answer(f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>\n\nВиберіть розділ керування:', reply_markup=akb.get_admin_main_kb(role), parse_mode='HTML')

@admin_router.callback_query(F.data == 'admin_panel_back')
async def back_to_admin_main(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await safe_edit_message(callback.message, f'🔐 <b>АДМІН-ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>\n\nВиберіть розділ керування:', reply_markup=akb.get_admin_main_kb(role), parse_mode='HTML')

# --- ORDERS BLOCK ---

@admin_router.message(F.text == '🆕 НОВІ ЗАМОВЛЕННЯ')
async def list_new_orders_msg(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    await show_new_orders(message)

@admin_router.callback_query(F.data == 'new_orders')
async def list_new_orders_cb(callback: CallbackQuery):
    await show_new_orders(callback.message)
    await callback.answer()

async def show_new_orders(message: Message):
    orders = await orders_db.get_new_orders()
    if not orders:
        await message.answer('🆕 <b>НОВІ ЗАМОВЛЕННЯ:</b>\nНаразі нових замовлень немає.', parse_mode='HTML')
        return
    
    text = "🆕 <b>НОВІ ЗАМОВЛЕННЯ:</b>\n\n"
    for o in orders:
        oid = str(o['_id'])
        user = o.get('fullname', 'Гість')
        total = o.get('total_amount', 0)
        created = o.get('created_at').strftime('%H:%M') if o.get('created_at') else '??'
        text += f"🕒 {created} | 📦 <b>{user}</b> - {total} ₴\nПереглянути: /view_order_{oid}\n\n"
    
    await message.answer(text, parse_mode='HTML')

@admin_router.message(F.text.startswith('/view_order_'))
async def view_order_details(message: Message, bot: Bot):
    if not await admin_db.is_admin(message.from_user.id): return
    oid = message.text.replace('/view_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await message.answer("Замовлення не знайдено.")
        return
    
    status_label = "НОВЕ" if order.get('status') == 'new' else "ОПЛАЧЕНО"
    type_map = { 'takeaway': 'З собою', 'in_house': 'В закладі', 'nova_poshta': 'НП', 'beans_delivery': 'Зерна (НП)', 'beans_booking': 'Зерна (Брон)' }
    order_type = order.get('order_type')
    type_label = type_map.get(order_type, order_type)
    
    msg = f"📦 <b>ЗАМОВЛЕННЯ #{oid[-6:]}</b> ({status_label})\n\n"
    msg += f"👤 Клієнт: <b>{order.get('fullname')}</b>\n"
    msg += f"📞 Телефон: <code>{order.get('phone')}</code>\n"
    msg += f"🚚 Куди: <b>{type_label}</b> {order.get('table_number', '')}\n"
    msg += f"💰 Сума: <b>{order.get('total_amount')} ₴</b>\n"
    msg += f"💳 Оплата: <b>{order.get('payment_mode')}</b>\n\n"
    msg += f"🛒 <b>СКЛАД:</b>\n{order.get('cart')}\n\n"
    msg += f"📝 ПОБАЖАННЯ: <b>{order.get('wishes') or '—'}</b>"
    
    await message.answer(msg, reply_markup=akb.get_booking_manage_kb(oid, order.get('user_id') or -1), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('confirm_order_'))
async def confirm_order_handler(callback: CallbackQuery, bot: Bot):
    oid = callback.data.replace('confirm_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await callback.answer('Замовлення не знайдено.')
        return
    
    await orders_db.update_status(oid, 'confirmed')
    # Add to active orders if not there
    await active_orders_db.add_active_order(
        oid, order.get('user_id'), order.get('fullname'), order.get('phone'), 
        order.get('location_id'), order.get('cart'), order.get('order_type'), 
        order.get('table_number', ''), order.get('total_amount'), 
        order.get('payment_mode'), order.get('wishes')
    )
    
    await safe_edit_message(callback.message, callback.message.text + "\n\n✅ <b>ПІДТВЕРДЖЕНО</b>", parse_mode='HTML')
    await callback.answer('Підтверджено!')
    
    await deliver_guest_message(bot, order, "✅ <b>Ваше замовлення підтверджено!</b>\nМи вже готуємо його.", "Admin confirmed")

@admin_router.callback_query(F.data.startswith('reject_order_'))
async def reject_order_handler(callback: CallbackQuery, bot: Bot):
    oid = callback.data.replace('reject_order_', '')
    order = await orders_db.get_order_by_id(oid)
    if not order:
        await callback.answer('Замовлення не знайдено.')
        return
    
    await orders_db.update_status(oid, 'rejected')
    await safe_edit_message(callback.message, callback.message.text + "\n\n❌ <b>ВІДХИЛЕНО</b>", parse_mode='HTML')
    await callback.answer('Відхилено.')
    
    await deliver_guest_message(bot, order, "❌ <b>На жаль, ваше замовлення відхилено.</b>\nДля деталей зв'яжіться з нами.", "Admin rejected")

@admin_router.callback_query(F.data.startswith('finish_order_'))
async def finish_order_handler(callback: CallbackQuery, bot: Bot):
    oid = callback.data.replace('finish_order_', '')
    await active_orders_db.remove_order(oid)
    await callback.answer('Замовлення завершено!')
    await list_active_orders_cb(callback)

# --- CONTENT MANAGEMENT BLOCK ---

@admin_router.message(F.text == '☕️ КЕРУВАННЯ ЗЕРНАМИ')
async def manage_beans_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer', 'boss'): return
    await message.answer('☕️ <b>КЕРУВАННЯ ЗЕРНАМИ:</b>\nДодавайте або редагуйте асортимент кави.', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '📍 ЛОКАЦІЇ')
async def manage_locations_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer', 'boss'): return
    await message.answer('📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ:</b>\nНалаштування кав\'ярень та точок видачі.', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '📞 КОНТАКТИ')
async def manage_contacts_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer', 'boss'): return
    await message.answer('📞 <b>КЕРУВАННЯ КОНТАКТАМИ:</b>\nРедагування посилань на соцмережі та контакти.', reply_markup=akb.get_contacts_manage_kb(), parse_mode='HTML')

# --- SYSTEM MANAGEMENT BLOCK ---

@admin_router.message(F.text == '👤 ПЕРСОНАЛ')
async def manage_staff_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer'): return
    await message.answer('👤 <b>КЕРУВАННЯ ПЕРСОНАЛОМ:</b>\nДодавання адміністраторів та менеджерів.', reply_markup=akb.get_staff_manage_kb(), parse_mode='HTML')

@admin_router.message(F.text == '📊 СТАТИСТИКА')
async def show_stats_msg(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ('owner', 'developer'): return
    await message.answer('📊 <b>СТАТИСТИКА ПРОДАЖІВ:</b>\n(Розділ знаходиться в розробці)', parse_mode='HTML')

@admin_router.callback_query(F.data == 'beans_manage')
async def manage_beans_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, '☕️ <b>КЕРУВАННЯ ЗЕРНАМИ:</b>', reply_markup=akb.get_beans_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'locations_manage')
async def manage_locations_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, '📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ:</b>', reply_markup=akb.get_locations_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'contacts_manage')
async def manage_contacts_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, '📞 <b>КЕРУВАННЯ КОНТАКТАМИ:</b>', reply_markup=akb.get_contacts_manage_kb(), parse_mode='HTML')

@admin_router.callback_query(F.data == 'beans_list')
async def list_beans_admin(callback: CallbackQuery):
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer('Сорти відсутні.')
        return
    
    text = "📜 <b>СПИСОК ЗЕРЕН:</b>\n\n"
    buttons = []
    for b in beans:
        bid = str(b['_id'])
        text += f"• <b>{b['name']}</b> ({b.get('price_250')} ₴)\n"
        buttons.append([InlineKeyboardButton(text=f"❌ Видалити {b['name'][:15]}", callback_data=f"bean_del_{bid}")])
    
    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='beans_manage')])
    await safe_edit_message(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('bean_del_'))
async def delete_bean_admin(callback: CallbackQuery):
    bid = callback.data.replace('bean_del_', '')
    await coffee_beans_db.delete_bean(bid)
    await callback.answer('Сорт видалено!')
    await list_beans_admin(callback)

@admin_router.callback_query(F.data == 'locations_list')
async def list_locations_admin(callback: CallbackQuery):
    locs = await location_db.get_all_locations()
    text = "📍 <b>СПИСОК ЛОКАЦІЙ:</b>\n\n"
    buttons = []
    for l in locs:
        lid = str(l['_id'])
        text += f"• <b>{l['name']}</b>\n"
        buttons.append([InlineKeyboardButton(text=f"❌ Видалити {l['name'][:15]}", callback_data=f"loc_del_{lid}")])
    
    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='locations_manage')])
    await safe_edit_message(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('loc_del_'))
async def delete_location_admin(callback: CallbackQuery):
    lid = callback.data.replace('loc_del_', '')
    db = await get_db()
    from bson import ObjectId
    await db.locations.delete_one({'_id': ObjectId(lid)})
    await callback.answer('Локацію видалено!')
    await list_locations_admin(callback)

@admin_router.callback_query(F.data == 'contacts_list')
async def list_contacts_admin(callback: CallbackQuery):
    socials = await contacts_db.get_all_contacts()
    text = "📞 <b>СПИСОК КОНТАКТІВ:</b>\n\n"
    buttons = []
    for s in socials:
        sid = str(s['_id'])
        text += f"• <b>{s['name']}</b>: {s['url']}\n"
        buttons.append([InlineKeyboardButton(text=f"❌ Видалити {s['name']}", callback_data=f"contact_del_{sid}")])
    
    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='contacts_manage')])
    await safe_edit_message(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('contact_del_'))
async def delete_contact_admin(callback: CallbackQuery):
    sid = callback.data.replace('contact_del_', '')
    await contacts_db.remove_contact(sid)
    await callback.answer('Контакт видалено!')
    await list_contacts_admin(callback)

@admin_router.callback_query(F.data == 'staff_list')
async def list_staff_admin(callback: CallbackQuery):
    staff = await admin_db.get_admins_with_locations()
    text = "👤 <b>СПИСОК ПЕРСОНАЛУ:</b>\n\n"
    buttons = []
    for s in staff:
        uid, uname, dname, role, shift, notify, locs = s
        text += f"• <b>{dname}</b> (@{uname or '—'}) — {role}\n"
        if str(uid) not in DEVELOPER_IDS:
            buttons.append([InlineKeyboardButton(text=f"❌ Видалити {dname[:15]}", callback_data=f"staff_del_{uid}")])
    
    buttons.append([InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='staff_manage')])
    await safe_edit_message(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('staff_del_'))
async def delete_staff_admin(callback: CallbackQuery):
    uid = int(callback.data.replace('staff_del_', ''))
    await admin_db.remove_admin(uid)
    await callback.answer('Учасника видалено!')
    await list_staff_admin(callback)

@admin_router.callback_query(F.data == 'bean_add')
async def add_bean_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer('Вкажіть назву нового сорту:')
    await state.set_state(AdminStates.adding_bean_name)

@admin_router.message(AdminStates.adding_bean_name)
async def add_bean_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Вкажіть ціну за 250г:')
    await state.set_state(AdminStates.adding_bean_price)

@admin_router.message(AdminStates.adding_bean_price)
async def add_bean_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price_250=price)
        await coffee_beans_db.add_bean(name=(await state.get_data())['name'], price_250=price)
        await message.answer('✅ Сорт додано!', reply_markup=akb.get_beans_manage_kb())
        await state.clear()
    except:
        await message.answer('Помилка. Вкажіть число ціною:')

@admin_router.callback_query(F.data.startswith('admin_auth_confirm_'))
async def confirm_admin_login(callback: CallbackQuery, bot: Bot):
    uid = int(callback.data.replace('admin_auth_confirm_', ''))
    code = f"LOGIN_{uid}_{int(time.time())}"
    await admin_db.create_auth_request(uid, code)
    try:
        await bot.send_message(uid, f"✅ <b>ВХІД ПІДТВЕРДЖЕНО!</b>\n\nВаш код для сайту: <code>{code}</code>", parse_mode='HTML')
        await callback.answer('Підтверджено!')
        await callback.message.delete()
    except:
        await callback.answer('Помилка відправки повідомлення.', show_alert=True)

@admin_router.callback_query(F.data.startswith('admin_auth_reject_'))
async def reject_admin_login(callback: CallbackQuery, bot: Bot):
    uid = int(callback.data.replace('admin_auth_reject_', ''))
    try:
        await bot.send_message(uid, "❌ <b>ВХІД ВІДХИЛЕНО.</b>", parse_mode='HTML')
        await callback.answer('Відхилено.')
        await callback.message.delete()
    except:
        await callback.answer('Помилка.')

async def deliver_guest_message(bot: Bot, order: dict, user_text: str, admin_text: str):
    uid = order.get('user_id')
    if uid:
        try: await bot.send_message(uid, user_text, parse_mode='HTML')
        except: pass
    else:
        logger.info(f"No user_id for order {order.get('_id')}, skipping user notification")
