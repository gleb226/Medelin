
from aiogram import Router, F, Bot

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from app.common.config import PAYMENT_TOKEN

from app.databases.orders_database import orders_db

from app.databases.active_bookings_database import active_bookings_db

from app.databases.active_orders_database import active_orders_db

from app.databases.user_database import user_db

from app.databases.admin_database import admin_db

from app.databases.menu_database import menu_db, parse_gramovka_grams

from app.databases.sales_database import sales_db

from app.databases.location_database import location_db

from app.databases.mongo_client import get_db

import logging

from app.utils.logger import log_activity

from app.utils.time_utils import is_working_hours, get_closed_message

from app.utils.message_utils import safe_edit_message

import app.keyboards.admin_keyboards as akb

import app.keyboards.user_keyboards as kb

import re, time

def _parse_menu_price(row):

    if not row:

        return None

    price_str = str(row[3] or '')

    digits = re.sub('\\D', '', price_str)

    if not digits:

        return None

    val = int(digits)

    return val if val > 0 else None

order_router = Router()

class OrderStates(StatesGroup):

    choosing_order_type = State()

    choosing_location = State()

    entering_table_number = State()
    entering_pickup_time = State()
    entering_wishes = State()
    entering_phone = State()

@order_router.callback_query(F.data == 'checkout_order')

async def order_start(callback: CallbackQuery, state: FSMContext):

    if not is_working_hours():

        await callback.message.answer(get_closed_message(), parse_mode='HTML')

        return

    data = await state.get_data()

    if not data.get('cart'):

        await callback.answer('🛒 Кошик порожній.')

        return

    kb_type = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏢 В закладі', callback_data='order_type_in_house')], [InlineKeyboardButton(text='🛍 На виніс', callback_data='order_type_takeaway')], [InlineKeyboardButton(text='🔙 Скасувати', callback_data='back_main_menu_only')]])

    await safe_edit_message(callback.message, '🧾 <b>ОБЕРІТЬ ТИП ЗАМОВЛЕННЯ:</b>', reply_markup=kb_type, parse_mode='HTML')

    await state.set_state(OrderStates.choosing_order_type)

@order_router.callback_query(F.data == 'checkout_booking')

async def booking_checkout(callback: CallbackQuery, state: FSMContext, bot: Bot):

    if not is_working_hours():

        await callback.message.answer(get_closed_message(), parse_mode='HTML')

        return

    data = await state.get_data()

    if not data.get('booking_mode'):

        await callback.answer('Немає активної броні.')

        return

    if not data.get('cart'):

        await callback.answer('🛒 Спочатку додайте позиції з меню.')

        return

    await callback.answer()

    async def _send_invoice():

        await send_order_invoice(callback.from_user, callback.message.chat.id, state, bot)

    if not await _ensure_phone_and_run(callback, state, callback.from_user, _send_invoice):

        return

@order_router.callback_query(F.data.startswith('order_type_'), OrderStates.choosing_order_type)

async def order_type_chosen(callback: CallbackQuery, state: FSMContext):

    await state.update_data(order_type=callback.data.replace('order_type_', ''))

    await safe_edit_message(callback.message, '📍 <b>ОБЕРІТЬ ЗАКЛАД:</b>', reply_markup=await kb.get_locations_kb(), parse_mode='HTML')

    await state.set_state(OrderStates.choosing_location)

@order_router.callback_query(F.data.startswith('loc_'), OrderStates.choosing_location)

async def order_loc_chosen(callback: CallbackQuery, state: FSMContext, bot: Bot):

    loc_id = callback.data.split('_')[1]

    await state.update_data(location_id=loc_id)

    data = await state.get_data()

    if data.get('order_type') == 'in_house':

        loc = await location_db.get_location_by_id(loc_id)

        max_t = loc.get('max_tables', 10) if loc else 10

        await safe_edit_message(callback.message, f'🔢 <b>ВКАЖІТЬ НОМЕР ВАШОГО СТОЛИКА:</b>\n<i>(Доступно: 1 - {max_t})</i>', parse_mode='HTML')

        await state.set_state(OrderStates.entering_table_number)

    else:

        await state.update_data(pickup_time='ПО ГОТОВНОСТІ')

        await ask_wishes_order(callback, state)

@order_router.callback_query(F.data.startswith('pickup_time_'))

async def order_pickup_time_chosen(callback: CallbackQuery, state: FSMContext, bot: Bot):

    time_str = callback.data.replace('pickup_time_', '')

    await state.update_data(pickup_time=time_str)

    await ask_wishes_order(callback, state)

@order_router.message(OrderStates.entering_table_number)

async def order_table_entered(message: Message, state: FSMContext, bot: Bot):

    val = (message.text or '').strip()

    data = await state.get_data()

    loc_id = data.get('location_id')

    loc = await location_db.get_location_by_id(loc_id)

    max_t = loc.get('max_tables', 10) if loc else 10

    if not val or not val.isdigit() or (not 1 <= int(val) <= max_t):

        await message.answer(f'❌ <b>НЕВІРНИЙ НОМЕР.</b> Вкажіть число від 1 до {max_t}:', parse_mode='HTML')

        return

    await state.update_data(table_number=val)

    await ask_wishes_order(message, state)

async def ask_phone_order(target, state: FSMContext):

    text = '📞 <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН (+380...):</b>\n\nНатисніть кнопку нижче або введіть вручну:'

    if isinstance(target, CallbackQuery):

        await target.message.answer(text, parse_mode='HTML', reply_markup=kb.get_phone_kb())

    else:

        await target.answer(text, parse_mode='HTML', reply_markup=kb.get_phone_kb())

    await state.set_state(OrderStates.entering_phone)

async def ask_wishes_order(target, state: FSMContext):
    text = '💬 <b>ПОБАЖАННЯ АБО УТОЧНЕННЯ ДО ЗАМОВЛЕННЯ (або "ні"):</b>'
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, parse_mode='HTML')
    else:
        await target.answer(text, parse_mode='HTML')
    await state.set_state(OrderStates.entering_wishes)

@order_router.message(OrderStates.entering_wishes)
async def order_wishes_entered(message: Message, state: FSMContext, bot: Bot):
    wishes_raw = (message.text or '').strip()
    wishes = '' if wishes_raw.lower() in ('ні', 'нет', 'no', '-', '—') else wishes_raw
    await state.update_data(wishes=wishes)
    
    async def _next_step():
        data = await state.get_data()
        if data.get('order_type') == 'in_house':
            await process_order_final(message.from_user, message.chat.id, state, bot)
        else:
            await send_order_invoice(message.from_user, message.chat.id, state, bot)
            
    if not await _ensure_phone_and_run(message, state, message.from_user, _next_step):
        return

async def _ensure_phone_and_run(target, state: FSMContext, user, action):

    current_state = await state.get_state()

    if current_state == OrderStates.entering_phone.state:

        return False

    data = await state.get_data()
    
    # Визначаємо, чи потрібен телефон. 
    # Телефон потрібен для замовлення зерен (доставка) або бронювання.
    # Для звичайного замовлення в закладі/на виніс — ні.
    order_type = data.get('order_type', '')
    needs_phone = order_type in ('beans_delivery', 'beans_booking', 'order_with_booking') or data.get('booking_mode')

    if not needs_phone:
        await action()
        return True

    phone = data.get('phone')

    if phone:

        await action()

        return True

    phone = await user_db.get_phone(user.id)

    if phone:

        await state.update_data(phone=phone)

        await action()

        return True

    await ask_phone_order(target, state)

    return False

@order_router.message(OrderStates.entering_phone)

async def order_phone_entered(message: Message, state: FSMContext, bot: Bot):

    phone = (message.text or '').strip()

    digits = ''.join((ch for ch in phone if ch.isdigit()))

    if len(digits) < 10:

        await message.answer('Некоректний телефон. Вкажіть у форматі +380...', parse_mode='HTML')

        return

    await state.update_data(phone=phone)

    await user_db.set_phone(message.from_user.id, phone)

    data = await state.get_data()

    if data.get('order_type') == 'in_house':

        await process_order_final(message.from_user, message.chat.id, state, bot)

    else:

        await send_order_invoice(message.from_user, message.chat.id, state, bot)

from app.common.bot_instance import bot

async def send_order_invoice(user, chat_id, state, bot_unused=None):

    data = await state.get_data()

    prices = []

    freq = {}

    for i in data['cart']:

        freq[i] = freq.get(i, 0) + 1

    for display_name, count in freq.items():
        # ... (rest of parsing logic) ...
        pure_name = display_name
        embedded_price = None
        if ' [' in display_name and display_name.endswith(']'):
            parts = display_name.rsplit(' [', 1)
            pure_name = parts[0]
            try:
                embedded_price = int(parts[1].replace(']', ''))
            except: pass

        base_name = pure_name.split(' (')[0]
        row = await menu_db.get_item_by_name(base_name)
        uah = _parse_menu_price(row)

        if embedded_price is not None:
            total_item_price = embedded_price * 100 * count
        elif uah:
            extra_price = 0
            if '(' in pure_name:
                opts_str = pure_name.split('(')[1].replace(')', '').lower()
                opts_list = [o.strip() for o in opts_str.split(',')]
                for opt in opts_list:
                    if opt == 'декаф': extra_price += 10
                    elif opt in ['мед', 'молоко']: extra_price += 10
            total_item_price = (uah + extra_price) * 100 * count
        else:
            continue

        prices.append(LabeledPrice(label=f'{pure_name} x{count}', amount=total_item_price))

    if not prices:

        await bot.send_message(chat_id, '❌ Не вдалося сформувати рахунок. Спробуйте ще раз або зверніться до адміністратора.')

        return

    p_type = 'bookpay' if data.get('booking_mode') else 'pay'
    pay_id = f'{p_type}_{user.id}_{int(time.time())}'
    await state.update_data(pay_id=pay_id)
    
    # Створюємо замовлення в БД перед оплатою, щоб отримати ID
    loc_id = data['location_id']
    
    # Формуємо рядок кошика з цінами
    cart_items_with_prices = []
    total_uah = 0
    for display_name in data['cart']:
        pure_name = display_name
        embedded_price = None
        if ' [' in display_name and display_name.endswith(']'):
            parts = display_name.rsplit(' [', 1)
            pure_name = parts[0]
            try:
                embedded_price = int(parts[1].replace(']', ''))
            except: pass

        if embedded_price is not None:
            total_uah += embedded_price
            cart_items_with_prices.append(f"- {pure_name} ({embedded_price} грн)")
            continue

        base_name = pure_name.split(' (')[0]
        row = await menu_db.get_item_by_name(base_name)
        uah = _parse_menu_price(row)
        if uah:
            extra = 0
            if '(' in pure_name:
                opts = pure_name.split('(')[1].replace(')', '').lower()
                for opt in [o.strip() for o in opts.split(',')]:
                    if opt in ['декаф', 'мед', 'молоко']: extra += 10
            item_total = uah + extra
            total_uah += item_total
            cart_items_with_prices.append(f"- {pure_name} ({item_total} грн)")
        else:
            cart_items_with_prices.append(f"- {pure_name}")

    cart_s = '\n'.join(cart_items_with_prices).upper()
    time_info = data.get('pickup_time', 'ЗАРАЗ')
    order_type = 'order_with_booking' if data.get('booking_mode') else data.get('order_type', 'order')
    
    rid = await orders_db.add_order(
        user.id, user.username, user.full_name, data.get('phone', '—'), 
        loc_id, time_info, data.get('people_count', '1'), 
        data.get('wishes', ''), cart_s, order_type, 
        table_number=data.get('table_number', ''),
        payment_mode='pay_now',
        total_amount=total_uah
    )

    from app.common.config import WEB_APP_URL
    payment_url = f"{WEB_APP_URL}/index.html?order_id={rid}"
    
    title = '💳 ОПЛАТА БРОНІ + ЗАМОВЛЕННЯ' if data.get('booking_mode') else '💳 ОПЛАТА ЗАМОВЛЕННЯ'
    
    kb_pay = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💳 ПЕРЕЙТИ ДО ОПЛАТИ', url=payment_url)],
        [InlineKeyboardButton(text='❌ Скасувати', callback_data='back_main_menu_only')]
    ])

    await bot.send_message(
        chat_id, 
        f"<b>{title}</b>\n\nСума до оплати: <b>{total_uah} грн</b>\n\nБудь ласка, натисніть кнопку нижче, щоб обрати спосіб оплати на нашому сайті та завершити замовлення:",
        reply_markup=kb_pay,
        parse_mode='HTML'
    )


async def send_beans_invoice(user, chat_id, state, bot):
    data = await state.get_data()
    base_val = data.get('base_price') or '300'
    base = int(''.join(filter(str.isdigit, str(base_val)))) or 300
    weight = int(str(data.get('weight') or '250'))
    total = int(base) if weight == 250 else int(base * (weight / 250) * (0.95 if weight == 500 else 0.9))

    pay_id = f'beans_{user.id}_{int(time.time())}'
    await state.update_data(pay_id=pay_id)
    name = str(data.get('bean_name') or '')

    # Створюємо замовлення перед оплатою на сайті
    loc_id = data.get('location_id')
    is_np = data.get('delivery_type') == 'nova_poshta'
    np_info = f"НП: {data.get('np_city_name')}, {data.get('np_warehouse')}" if is_np else "САМОВИВІЗ"
    time_info = 'НОВА ПОШТА' if is_np else 'БРОНЬ 2 ДНІ'
    order_type = 'beans_delivery' if is_np else 'beans_booking'
    
    wishes = data.get('wishes', '')
    wishes_str = f"ВАГА: {weight}г | {np_info}"
    if wishes:
        wishes_str += f"\nПОБАЖАННЯ: {wishes}"

    rid = await orders_db.add_order(
        user.id, user.username, user.full_name, data.get('phone', '—'), 
        loc_id or "NP", time_info, '0', wishes_str, 
        f"ЗЕРНА: {name}", order_type,
        payment_mode='pay_now',
        total_amount=total
    )

    from app.common.config import WEB_APP_URL
    payment_url = f"{WEB_APP_URL}/index.html?order_id={rid}"
    
    kb_pay = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💳 ПЕРЕЙТИ ДО ОПЛАТИ', url=payment_url)],
        [InlineKeyboardButton(text='❌ Скасувати', callback_data='back_main_menu_only')]
    ])

    await bot.send_message(
        chat_id, 
        f"<b>💳 ОПЛАТА КАВИ</b>\n\n<b>Сорт:</b> {name}\n<b>Вага:</b> {weight}г\n<b>Сума:</b> {total} ₴\n\nБудь ласка, натисніть кнопку нижче, щоб обрати спосіб оплати та завершити замовлення:",
        reply_markup=kb_pay,
        parse_mode='HTML'
    )

@order_router.pre_checkout_query()

async def pre_checkout(query: PreCheckoutQuery, bot: Bot):

    await bot.answer_pre_checkout_query(query.id, ok=True)

@order_router.message(F.successful_payment)

async def pay_ok(message: Message, state: FSMContext, bot: Bot):

    p = message.successful_payment

    await sales_db.record_payment(message.from_user.id, p.total_amount / 100, p.currency, p.invoice_payload, p.telegram_payment_charge_id, p.provider_payment_charge_id)

    await state.update_data(payment_charge_id=p.telegram_payment_charge_id, provider_payment_charge_id=p.provider_payment_charge_id)

    if 'beans' in p.invoice_payload:

        await process_beans_final(message.from_user, message.chat.id, state, bot)

    elif 'bookpay' in p.invoice_payload:

        await process_booking_order_final(message.from_user, message.chat.id, state, bot)

    else:

        await process_order_final(message.from_user, message.chat.id, state, bot)

async def process_booking_order_final(user, chat_id, state, bot):

    data = await state.get_data()

    loc_id = data.get('location_id')

    is_admin = await admin_db.is_admin(user.id)

    rid = await orders_db.add_order(user.id, user.username, user.full_name, data.get('phone', '—'), loc_id, data.get('date_time'), data.get('people_count'), data.get('wishes'), ', '.join(data['cart']).upper(), 'order_with_booking')

    await orders_db.set_payment_id(rid, data.get('payment_charge_id'), data.get('provider_payment_charge_id'))

    await active_bookings_db.add_active_booking(rid, user.id, user.full_name, data.get('phone', '—'), loc_id, data.get('date_time'), data.get('people_count'), data.get('wishes'))

    loc = await location_db.get_location_by_id(loc_id)

    loc_name = loc['name'] if loc else '—'

    msg = f"🌟 <b>БРОНЮВАННЯ ТА ЗАМОВЛЕННЯ</b>\n\n👤 <b>КЛІЄНТ:</b> {user.full_name}\n📞 <b>ТЕЛЕФОН:</b> <code>{data.get('phone', '—')}</code>\n🏛 <b>ЗАКЛАД:</b> {loc_name}\n🕒 <b>ЧАС:</b> {data.get('date_time')}\n👥 <b>ГОСТЕЙ:</b> {data.get('people_count')}\n🥘 <b>МЕНЮ:</b> {', '.join(data['cart']).upper()}\n💰 <b>СТАТУС:</b> ОПЛАЧЕНО"

    targets = await admin_db.get_notification_targets(loc_id)

    for aid in targets:

        try:

            await bot.send_message(aid, msg, reply_markup=akb.get_booking_manage_kb(rid), parse_mode='HTML')

            await orders_db.mark_admin_notified(rid, aid)

        except:

            pass

    await bot.send_message(chat_id, f'✅ <b>ДЯКУЄМО! ЗАПИТ ПЕРЕДАНО АДМІНІСТРАТОРУ.</b>\n\nМи чекаємо на вас у <b>{loc_name}</b>.' if targets else '🕓 <b>ЗАПИТ ЗБЕРЕЖЕНО.</b>\n\nНаразі немає доступних адміністраторів на зміні.', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

    await state.clear()

async def process_beans_final(user, chat_id, state, bot):

    data = await state.get_data()

    is_admin = await admin_db.is_admin(user.id)

    loc_id = data.get('location_id')

    is_np = data.get('delivery_type') == 'nova_poshta'

    np_info = f"<b>📍 НП:</b> {data.get('np_city_name')}, {data.get('np_warehouse')}" if is_np else "<b>🏬 САМОВИВІЗ</b>"

    time_info = 'НОВА ПОШТА' if is_np else 'БРОНЬ 2 ДНІ'

    order_type = 'beans_delivery' if is_np else 'beans_booking'
    
    wishes = data.get('wishes', '')
    wishes_str = f"ВАГА: {data['weight']}г | {np_info}"
    if wishes:
        wishes_str += f"\nПОБАЖАННЯ: {wishes}"

    phone = data.get('phone') or '—'
    rid = await orders_db.add_order(user.id, user.username, user.full_name, phone, loc_id or "NP", time_info, '0', wishes_str, f"ЗЕРНА: {data['bean_name']}", order_type)

    await orders_db.set_payment_id(rid, data.get('payment_charge_id'), data.get('provider_payment_charge_id'))

    await active_orders_db.add_active_order(rid, user.id, user.full_name, phone, loc_id or "NP", data['bean_name'], order_type)

    loc_name = "НОВА ПОШТА"

    if loc_id and not is_np:
        loc = await location_db.get_location_by_id(loc_id)
        loc_name = loc['name'] if loc else '—'

    msg = f"☕️ <b>НОВЕ ЗАМОВЛЕННЯ ЗЕРЕН</b>\n\n"
    msg += f"👤 <b>КЛІЄНТ:</b> {user.full_name}\n"
    msg += f"📞 <b>ТЕЛЕФОН:</b> <code>{phone}</code>\n"
    
    if is_np:
        msg += f"🚚 <b>ДОСТАВКА:</b> {np_info}\n"
    else:
        msg += f"🏛 <b>ОТРИМАННЯ:</b> {loc_name}\n"

    msg += f"📦 <b>СОРТ:</b> {data['bean_name']} ({data['weight']}г)\n"
    
    if wishes:
        import html
        msg += f"💬 <b>ПОБАЖАННЯ:</b> {html.escape(wishes)}\n"
        
    msg += f"💰 <b>СТАТУС:</b> ОПЛАЧЕНО"

    targets = set()
    # ... rest remains same ...

    targets = set()

    if is_np:

        db = await get_db()

        cur = db.admins.find({'role': {'$in': ['delivery_manager', 'boss', 'owner', 'developer']}})

        rows = await cur.to_list(length=None)

        targets.update([int(r['user_id']) for r in rows])

    else:

        targets.update(await admin_db.get_notification_targets(loc_id))

    for aid in targets:

        try:

            await bot.send_message(aid, msg, reply_markup=akb.get_booking_manage_kb(rid), parse_mode='HTML')

            await orders_db.mark_admin_notified(rid, aid)

        except:

            pass

    success_text = f'✅ <b>ДЯКУЄМО!</b> Ваше замовлення прийнято. Ми відправимо каву у м. {data.get("np_city_name")} найближчим часом.' if is_np else f'✅ <b>ДЯКУЄМО!</b> Кава чекатиме на вас у <b>{loc_name}</b> протягом 2 днів.'

    await bot.send_message(chat_id, success_text, reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

    await state.clear()

async def process_order_final(user, chat_id, state, bot):

    data = await state.get_data()

    is_house = data.get('order_type') == 'in_house'

    is_admin = await admin_db.is_admin(user.id)

    loc_id = data['location_id']

    cart_s = ', '.join(data['cart']).upper()

    time_info = data.get('pickup_time', 'ЗАРАЗ')

    wishes_val = data.get('wishes')
    wishes_str = f"МЕНЮ. {wishes_val}" if wishes_val else "МЕНЮ"

    rid = await orders_db.add_order(user.id, user.username, user.full_name, data.get('phone', '—'), loc_id, time_info, '0', wishes_str, cart_s, data.get('order_type', 'order'), data.get('table_number', ''))

    if not is_house:

        await orders_db.set_payment_id(rid, data.get('payment_charge_id'), data.get('provider_payment_charge_id'))

    await active_orders_db.add_active_order(rid, user.id, user.full_name, data.get('phone', '—'), loc_id, cart_s, data['order_type'], data.get('table_number'))

    loc = await location_db.get_location_by_id(loc_id)

    loc_name = loc['name'] if loc else '—'

    p_stat = '💰 <b>ОПЛАЧЕНО</b>' if not is_house else '⏳ <b>ОПЛАТА В ЗАКЛАДІ</b>'

    t_line = f"🪑 <b>СТОЛИК:</b> {data.get('table_number')}\n" if is_house else f'🕒 <b>ЧАС:</b> {time_info}\n'

    msg = f"🔔 <b>НОВЕ ЗАМОВЛЕННЯ</b>\n\n👤 <b>КЛІЄНТ:</b> {user.full_name}\n📞 <b>ТЕЛЕФОН:</b> <code>{data.get('phone', '—')}</code>\n🏛 <b>ЗАКЛАД:</b> {loc_name}\n{t_line}🥘 <b>ПОЗИЦІЇ:</b> {cart_s}"
    if wishes_val:
        import html
        msg += f"\n💬 <b>ПОБАЖАННЯ:</b> {html.escape(wishes_val)}"
    msg += f"\n{p_stat}"

    targets = await admin_db.get_notification_targets(loc_id)

    for aid in targets:

        try:

            await bot.send_message(aid, msg, reply_markup=akb.get_booking_manage_kb(rid), parse_mode='HTML')

            await orders_db.mark_admin_notified(rid, aid)

        except:

            pass

    await bot.send_message(chat_id, '✅ <b>ЗАМОВЛЕННЯ ПЕРЕДАНО АДМІНІСТРАТОРУ.</b>', reply_markup=kb.get_main_menu(is_admin), parse_mode='HTML')

    await state.clear()
