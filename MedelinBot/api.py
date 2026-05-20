
import base64

import hashlib

import json

import pathlib

from typing import Any

import asyncio

from fastapi import FastAPI, HTTPException, Response, Request, Form
from fastapi.responses import JSONResponse

from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from bson import ObjectId

from fastapi.encoders import jsonable_encoder

from app.common.config import BOSS_IDS, LIQPAY_PRIVATE_KEY, LIQPAY_PUBLIC_KEY, MONOBANK_TOKEN, WEB_APP_URL, NP_API_KEY

from app.databases.guest_messages_database import guest_messages_db

from app.databases.location_database import location_db

from app.databases.orders_database import orders_db

from app.keyboards import admin_keyboards as akb

from app.utils.admin_notifications import send_admin_notification

from app.utils.data_cache import public_data_cache

from app.utils.phone_utils import format_phone

def custom_jsonable_encoder(obj, **kwargs):

    if isinstance(obj, ObjectId):

        return str(obj)

    if isinstance(obj, list):

        return [custom_jsonable_encoder(item, **kwargs) for item in obj]

    if isinstance(obj, dict):

        return {k: custom_jsonable_encoder(v, **kwargs) for k, v in obj.items()}

    return jsonable_encoder(obj, **kwargs)

class CustomJSONResponse(JSONResponse):

    def render(self, content: Any) -> bytes:

        return json.dumps(custom_jsonable_encoder(content), ensure_ascii=False, allow_nan=False, indent=None, separators=(',', ':')).encode('utf-8')

from contextlib import asynccontextmanager

@asynccontextmanager

async def lifespan(app: FastAPI):

    async def _warm():

        await public_data_cache.warm_all(max_retries=3)

    task = asyncio.create_task(_warm())

    yield

    task.cancel()

app = FastAPI(title="Medelin Menu API", default_response_class=CustomJSONResponse, lifespan=lifespan)

_root_dir = pathlib.Path(__file__).parent.parent

_site_dir = _root_dir / "MedelinSite"

_uploads_dir = pathlib.Path("/app/uploads")

if not _uploads_dir.exists():

    _uploads_dir = _site_dir / "images" / "uploads"

_uploads_dir.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

app.mount("/cache", StaticFiles(directory=str(public_data_cache._dir)), name="cache")

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)

class CheckoutRequest(BaseModel):

    user_details: dict

    cart_menu: list

    payment_method: str = 'card'

class BookingRequest(BaseModel):

    name: str

    phone: str

    tg: str = ''

    location: str

    date: str

    time: str

    guests: str

    wishes: str = ''

class GuestReplyRequest(BaseModel):

    phone: str

    order_id: str = ''

    text: str

async def resolve_location(value: str | None):

    target = (value or '').strip()

    if not target:

        return None

    normalized = target.casefold()

    for loc in await location_db.get_all_locations():

        loc_id = str(loc.get('_id', ''))

        name = str(loc.get('name', '')).strip()

        address = str(loc.get('address', '')).strip()

        if target == loc_id:

            return loc

        if normalized in {name.casefold(), address.casefold(), f'{name} - {address}'.casefold(), f'{name} — {address}'.casefold()}:

            return loc

    return None

def parse_price(value):

    import re

    digits = re.sub('[^\\d]', '', str(value))

    return int(digits) if digits else 0

def build_cart_text(cart_menu: list) -> tuple[int, str]:

    total = 0

    items = []

    for item in cart_menu:

        price = parse_price(item.get('price', 0))

        total += price

        items.append(f"- {item['name']} ({price} грн)")

    return (total, '\n'.join(items))

@app.get('/api/nova-poshta/cities')

async def get_np_cities(search: str):

    import aiohttp

    payload = {'apiKey': NP_API_KEY, 'modelName': 'Address', 'calledMethod': 'searchSettlements', 'methodProperties': {'CityName': search, 'Limit': '50'}}

    async with aiohttp.ClientSession() as session:

        async with session.post('https://api.novaposhta.ua/v2.0/json/', json=payload) as resp:

            data = await resp.json()

            res_data = data.get('data', [])

            if res_data and isinstance(res_data, list) and (len(res_data) > 0):

                return res_data[0].get('Addresses', [])

            return []

@app.get('/api/nova-poshta/warehouses')

async def get_np_warehouses(cityRef: str, cityName: str = None, search: str = None):

    import aiohttp

    import logging

    async def fetch_wh(props):

        payload = {'apiKey': NP_API_KEY, 'modelName': 'Address', 'calledMethod': 'getWarehouses', 'methodProperties': props}

        async with aiohttp.ClientSession() as session:

            async with session.post('https://api.novaposhta.ua/v2.0/json/', json=payload) as resp:

                data = await resp.json()

                return data.get('data', [])

    props = {'SettlementRef': cityRef}

    if search:

        props['FindByString'] = search

    logging.warning(f'Fetching warehouses for SettlementRef: {cityRef}, search: {search}')

    data = await fetch_wh(props)

    if not data:

        logging.warning('Trying via CityRef...')

        props_city = {'CityRef': cityRef}

        if search:

            props_city['FindByString'] = search

        data = await fetch_wh(props_city)

    if not data and cityName:

        clean_name = cityName.split(',')[0].strip()

        logging.warning(f'Trying via CityName: {clean_name}, search: {search}')

        props_name = {'CityName': clean_name}

        if search:

            props_name['FindByString'] = search

        data = await fetch_wh(props_name)

    logging.warning(f'Found {len(data)} warehouses')

    return data

@app.get('/api/orders/{order_id}')
async def get_order_details(order_id: str):
    order = await orders_db.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено.")
    
    # Вираховуємо загальну суму
    # 1. Спробуємо взяти пряме поле total_amount
    total = order.get('total_amount', 0)
    
    # 2. Якщо 0 або немає, парсимо з рядка cart
    if not total:
        cart = order.get('cart', '')
        if isinstance(cart, str):
            import re
            # Використовуємо re.IGNORECASE для підтримки "грн" і "ГРН"
            prices = re.findall(r'\((\d+)\s*грн\)', cart, re.IGNORECASE)
            if not prices:
                prices = re.findall(r'(\d+)\s*грн', cart, re.IGNORECASE)
            
            total = sum(int(p) for p in prices)
        elif isinstance(cart, list):
            for item in cart:
                try:
                    p = item.get('price', 0)
                    total += int(p)
                except: pass
    
    # Якщо суму все одно не знайдено, а це замовлення з бота, 
    # можливо сума вказана в іншому полі або ми можемо спробувати отримати її з menu_db
    # Але зазвичай регулярки вище достатньо для формату бота.
    
    # Якщо суму не вдалося спарсити (наприклад, бронювання), спробуємо заглянути в саму БД або використати 0
    # Але зазвичай в боті сума вже є в описі
    
    return {
        "order_id": str(order['_id']),
        "total": total,
        "fullname": order.get('fullname'),
        "phone": order.get('phone'),
        "order_type": order.get('order_type'),
        "items_text": cart if isinstance(cart, str) else build_cart_text(cart)[1]
    }

class RepayRequest(BaseModel):
    order_id: str
    payment_method: str

async def notify_admins_about_order(order_id: str):
    order = await orders_db.get_order_by_id(order_id)
    if not order:
        return

    # Перевіряємо, чи ми вже сповіщали про це замовлення
    # Для онлайн-оплат ми вважаємо, що сповіщення треба відправити, якщо notified_admin_ids порожній
    if order.get('notified_admin_ids'):
        return

    oid = str(order['_id'])
    fullname = order.get('fullname', 'Не вказано')
    phone = order.get('phone', 'Не вказано')
    tg_nick = order.get('username', '')
    loc_id = order.get('location_id', 'web')
    order_type = order.get('order_type', 'takeaway')
    payment_mode = order.get('payment_mode', 'pay_now')
    total = order.get('total_amount', 0)
    items_text = order.get('cart', '')
    table_number = order.get('table_number', '')

    # Визначаємо назву локації
    location_name = 'Web Order'
    for loc in await location_db.get_all_locations():
        if str(loc.get('_id')) == loc_id:
            location_name = loc.get('name', 'Web Order')
            break

    msg = f'✅ <b>ОПЛАЧЕНЕ ЗАМОВЛЕННЯ (#{oid})</b>\n\n'
    msg += f"👤 Клієнт: {fullname}\n"
    msg += f'📞 Телефон: <code>{phone}</code>\n'
    if tg_nick:
        msg += f"✈️ Telegram: {(tg_nick if tg_nick.startswith('@') else '@' + tg_nick)}\n"
    
    if order_type == 'nova_poshta':
        msg += f'🚚 Доставка: <b>Нова Пошта</b>\n'
        # Тут можна було б витягнути деталі міста/відділення, якщо вони збережені в Wishes або окремо
        # Але в даному коді вони в Wishes або в cart. 
        # Для спрощення виводимо те що є.
    else:
        msg += f'🏛 Заклад: {location_name}\n'
        if order_type == 'in_house':
            msg += f"🪑 Тип: В закладі (Столик: {table_number or '—'})\n"
        else:
            msg += f'📦 Тип: З собою\n'

    msg += f'💰 Сума: <b>{total} грн</b>\n'
    msg += f"💳 Оплата: Онлайн (Сплачено)\n\n"
    msg += f'🛒 Кошик:\n{items_text}'

    await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id if loc_id != 'web' else None)
    
    # Маркуємо як сповіщене (використовуємо ID боса як заглушку, щоб список не був порожнім)
    if BOSS_IDS:
        await orders_db.mark_admin_notified(oid, int(BOSS_IDS[0]))

@app.post('/api/payments/liqpay-callback')
async def liqpay_callback(response: Response):
    from fastapi import Request
    # LiqPay надсилає data та signature у form-data
    from fastapi import Form
    import base64
    import json

    try:
        # Отримуємо сирі дані з тіла запиту, бо FastAPI може не розпарсити LiqPay POST
        # Але спробуємо через Form спочатку
        pass
    except: pass

@app.post('/api/payments/liqpay-callback-raw')
async def liqpay_callback_raw(request: Request):
    form_data = await request.form()
    data_b64 = form_data.get('data')
    signature = form_data.get('signature')

    if not data_b64 or not signature:
        return {"status": "error", "message": "Missing data or signature"}

    # Перевірка підпису
    sign_string = LIQPAY_PRIVATE_KEY + data_b64 + LIQPAY_PRIVATE_KEY
    expected_signature = base64.b64encode(hashlib.sha1(sign_string.encode('utf-8')).digest()).decode('utf-8')
    
    if signature != expected_signature:
        return {"status": "error", "message": "Invalid signature"}

    data = json.loads(base64.b64decode(data_b64).decode('utf-8'))
    order_id = data.get('order_id')
    status = data.get('status')

    if status in ('success', 'wait_accept'):
        await orders_db.set_payment_id(order_id, data.get('payment_id'), data.get('liqpay_order_id'))
        await notify_admins_about_order(order_id)
    
    return {"status": "ok"}

@app.post('/api/payments/monobank-callback')
async def monobank_callback(request: Request):
    data = await request.json()
    # Monobank надсилає JSON з полем reference (наш order_id) та status
    order_id = data.get('reference')
    status = data.get('status')

    if status == 'success':
        invoice_id = data.get('invoiceId')
        await orders_db.set_payment_id(order_id, invoice_id, invoice_id)
        await notify_admins_about_order(order_id)

    return {"status": "ok"}

@app.post('/api/repay')
async def process_repay(req: RepayRequest):
    order = await orders_db.get_order_by_id(req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено.")

    oid = str(order['_id'])

    # Вираховуємо суму (надійна логіка)
    total = order.get('total_amount', 0)
    if not total:
        cart = order.get('cart', '')
        if isinstance(cart, str):
            import re
            prices = re.findall(r'\((\d+)\s*грн\)', cart, re.IGNORECASE)
            if not prices:
                prices = re.findall(r'(\d+)\s*грн', cart, re.IGNORECASE)
            total = sum(int(p) for p in prices)
        elif isinstance(cart, list):
            for item in cart:
                try:
                    p = item.get('price', 0)
                    total += int(p)
                except: pass

    if total <= 0:
        raise HTTPException(status_code=400, detail="Сума замовлення не може бути 0.")

    payment_method = req.payment_method

    # Повторюємо логіку вибору провайдера
    use_monobank = payment_method == 'monobank'
    if use_monobank and MONOBANK_TOKEN:
        import aiohttp
        mono_url = 'https://api.monobank.ua/api/merchant/invoice/create'
        headers = {'X-Token': MONOBANK_TOKEN, 'Content-Type': 'application/json'}
        payload = {
            'amount': int(total * 100),
            'ccy': 980,
            'merchantPaymInfo': {'reference': oid, 'destination': f'Замовлення #{oid} (Medelin)'},
            'redirectUrl': WEB_APP_URL,
            'webhookUrl': f"{WEB_APP_URL}/api/payments/monobank-callback",
            'validity': 3600
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(mono_url, json=payload, headers=headers, timeout=15) as resp:
                    resp_data = await resp.json()
                    if resp.status == 200:
                        return {'status': 'ok', 'url': resp_data['pageUrl'], 'provider': 'monobank'}
        except: pass

    # LiqPay fallback
    liqpay_paytypes = 'card'
    if payment_method == 'applepay': liqpay_paytypes = 'apay'
    elif payment_method == 'googlepay': liqpay_paytypes = 'gpay'
    elif payment_method == 'privatpay': liqpay_paytypes = 'privat24'

    liqpay_params = {
        'action': 'pay', 'amount': total, 'currency': 'UAH',
        'description': f'Замовлення #{oid} (Medelin)', 'order_id': oid,
        'version': '3', 'public_key': LIQPAY_PUBLIC_KEY, 'result_url': WEB_APP_URL,
        'server_url': f"{WEB_APP_URL}/api/payments/liqpay-callback-raw",
        'paytypes': liqpay_paytypes
    }
    json_data = json.dumps(liqpay_params).encode('utf-8')
    encoded_data = base64.b64encode(json_data).decode('utf-8')
    sign_string = LIQPAY_PRIVATE_KEY + encoded_data + LIQPAY_PRIVATE_KEY
    signature = base64.b64encode(hashlib.sha1(sign_string.encode('utf-8')).digest()).decode('utf-8')

    return {'status': 'ok', 'data': encoded_data, 'signature': signature, 'provider': 'liqpay'}

@app.post('/api/checkout')
async def process_checkout(req: CheckoutRequest):
    data = req.dict()
    cart_menu = data.get('cart_menu', [])
    user = data.get('user_details', {})
    payment_method = data.get('payment_method', 'card')

    total, items_text = build_cart_text(cart_menu)
    if total <= 0:
        raise HTTPException(status_code=400, detail='Сума замовлення не може бути нульовою.')

    location = await resolve_location(user.get('location'))
    loc_id = str(location['_id']) if location else 'web'
    location_name = location['name'] if location else 'Web Order'
    phone = format_phone(user.get('phone', '')) or user.get('phone', 'Не вказано')
    tg_nick = user.get('tg_nick') or user.get('tg') or ''
    delivery_type = user.get('delivery_type')
    payment_mode = user.get('payment_mode') or 'pay_now'
    order_type = 'takeaway' if user.get('type') == 'takeaway' else 'in_house'
    if delivery_type:
        order_type = delivery_type

    oid = await orders_db.add_order(user_id=None, username=tg_nick, fullname=user.get('name', 'Не вказано'), phone=phone, location_id=loc_id, date_time='Сьогодні', people_count='1', wishes=f'TG: {tg_nick}', cart=items_text, order_type=order_type, payment_mode=payment_mode, table_number=user.get('table_number', ''), total_amount=total)

    msg = f'🆕 <b>НОВЕ ЗАМОВЛЕННЯ (#{oid})</b>\n\n'
    msg += f"👤 Клієнт: {user.get('name')}\n"
    msg += f'📞 Телефон: <code>{phone}</code>\n'
    if tg_nick:
        msg += f"✈️ Telegram: {(tg_nick if tg_nick.startswith('@') else '@' + tg_nick)}\n"

    if delivery_type == 'nova_poshta':
        msg += f'🚚 Доставка: <b>Нова Пошта</b>\n'
        msg += f"📍 Місто: {user.get('np_city_name')}\n"
        msg += f"🏢 Відділення: {user.get('np_warehouse')}\n"
    else:
        msg += f'🏛 Заклад: {location_name}\n'
        if order_type == 'in_house':
            msg += f"🪑 Тип: В закладі (Столик: {user.get('table_number') or '—'})\n"
        else:
            msg += f'📦 Тип: З собою\n'

    msg += f'💰 Сума: <b>{total} грн</b>\n'
    msg += f"💳 Оплата: {('Зараз (онлайн)' if payment_mode == 'pay_now' else 'На касі')}\n\n"
    msg += f'🛒 Кошик:\n{items_text}'

    # Надсилаємо сповіщення адміну ТІЛЬКИ якщо це оплата на касі
    if payment_mode == 'pay_at_checkout':
        await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id if loc_id != 'web' else None)
        return {'status': 'ok', 'manual': True, 'order_id': oid}

    # Для онлайн-оплати
    use_monobank = payment_method == 'monobank'
    if use_monobank and MONOBANK_TOKEN:
        import aiohttp
        mono_url = 'https://api.monobank.ua/api/merchant/invoice/create'
        headers = {'X-Token': MONOBANK_TOKEN, 'Content-Type': 'application/json'}
        payload = {
            'amount': int(total * 100),
            'ccy': 980,
            'merchantPaymInfo': {'reference': str(oid), 'destination': f'Замовлення #{oid} (Medelin)'},
            'redirectUrl': WEB_APP_URL,
            'webhookUrl': f"{WEB_APP_URL}/api/payments/monobank-callback",
            'validity': 3600
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(mono_url, json=payload, headers=headers, timeout=15) as resp:
                    resp_data = await resp.json()
                    if resp.status == 200:
                        return {'status': 'ok', 'url': resp_data['pageUrl'], 'order_id': oid, 'provider': 'monobank'}
        except Exception: pass

    # LiqPay
    liqpay_paytypes = 'card'
    if payment_method == 'applepay': liqpay_paytypes = 'apay'
    elif payment_method == 'googlepay': liqpay_paytypes = 'gpay'
    elif payment_method == 'privatpay': liqpay_paytypes = 'privat24'

    liqpay_params = {
        'action': 'pay', 'amount': total, 'currency': 'UAH',
        'description': f'Замовлення #{oid} (Medelin)', 'order_id': str(oid),
        'version': '3', 'public_key': LIQPAY_PUBLIC_KEY, 'result_url': WEB_APP_URL,
        'server_url': f"{WEB_APP_URL}/api/payments/liqpay-callback-raw",
        'paytypes': liqpay_paytypes
    }
    json_data = json.dumps(liqpay_params).encode('utf-8')
    encoded_data = base64.b64encode(json_data).decode('utf-8')
    sign_string = LIQPAY_PRIVATE_KEY + encoded_data + LIQPAY_PRIVATE_KEY
    signature = base64.b64encode(hashlib.sha1(sign_string.encode('utf-8')).digest()).decode('utf-8')

    return {'status': 'ok', 'data': encoded_data, 'signature': signature, 'order_id': oid, 'provider': 'liqpay'}


@app.post('/api/booking')

async def process_booking(req: BookingRequest):

    data = req.dict()

    location = await resolve_location(data.get('location'))

    loc_id = str(location['_id']) if location else 'unknown'

    location_name = location['name'] if location else data.get('location') or 'Невідомо'

    phone = format_phone(data.get('phone', '')) or data.get('phone')

    booking_time = (data.get('time') or '').strip()

    oid = await orders_db.add_order(user_id=None, username=data.get('tg', ''), fullname=data.get('name'), phone=phone, location_id=loc_id, date_time=f"{data.get('date')} {booking_time}", people_count=data.get('guests'), wishes=data.get('wishes', ''), cart='Бронювання столика', order_type='booking', payment_mode='cashier')

    msg = '🛎 <b>НОВЕ БРОНЮВАННЯ З САЙТУ</b> 🛎\n\n'

    msg += f"👤 Гість: {data.get('name')}\n"

    msg += f'📞 Телефон: <code>{phone}</code>\n'

    tg = data.get('tg', '')

    if tg:

        msg += f"✈️ Telegram: {(tg if tg.startswith('@') else '@' + tg)}\n"

    msg += f'📍 Заклад: {location_name}\n'

    msg += f"📅 Дата: {data.get('date')} о {booking_time}\n"

    msg += f"👥 Осіб: {data.get('guests')}\n"

    if data.get('wishes'):

        msg += f"📝 Побажання: {data.get('wishes')}\n"

    await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id if loc_id != 'unknown' else None)

    return {'status': 'ok', 'order_id': oid}

@app.get('/api/menu')

async def get_menu():

    cached = public_data_cache.get('menu')

    if cached is not None:

        return cached

    try:

        data = await public_data_cache.refresh_menu()

        return data

    except Exception as e:

        disk = public_data_cache._load_from_disk("menu")

        if disk:

            return disk

        raise HTTPException(status_code=503, detail="Menu data temporarily unavailable.")

@app.get('/api/coffee')

async def get_coffee():

    cached = public_data_cache.get('coffee')

    if cached is not None:

        return cached

    try:

        data = await public_data_cache.refresh_coffee()

        return data

    except Exception as e:

        disk = public_data_cache._load_from_disk("coffee")

        if disk:

            return disk

        raise HTTPException(status_code=503, detail="Coffee data temporarily unavailable.")

@app.get('/api/locations')

async def get_locations():

    cached = public_data_cache.get('locations')

    if cached is not None:

        return cached

    try:

        data = await public_data_cache.refresh_locations()

        return data

    except Exception as e:

        disk = public_data_cache._load_from_disk("locations")

        if disk:

            return disk

        raise HTTPException(status_code=503, detail="Locations data temporarily unavailable.")

@app.get('/api/socials')

async def get_socials():

    cached = public_data_cache.get('socials')

    if cached is not None:

        return cached

    try:

        data = await public_data_cache.refresh_socials()

        return data

    except Exception as e:

        disk = public_data_cache._load_from_disk("socials")

        if disk:

            return disk

        return []

app.mount('/', StaticFiles(directory=str(_site_dir), html=True), name='site')
