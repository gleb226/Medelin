
import base64

import hashlib

import json

import pathlib

from typing import Any

import asyncio

from fastapi import FastAPI, HTTPException, Response

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

    oid = await orders_db.add_order(user_id=None, username=tg_nick, fullname=user.get('name', 'Не вказано'), phone=phone, location_id=loc_id, date_time='Сьогодні', people_count='1', wishes=f'TG: {tg_nick}', cart=items_text, order_type=order_type, payment_mode=payment_mode, table_number=user.get('table_number', ''))

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

    await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id if loc_id != 'web' else None)

    if payment_mode == 'pay_at_checkout':
        return {'status': 'ok', 'manual': True, 'order_id': oid}

    # Визначаємо провайдера: Картка, Apple Pay, Google Pay та MonoPay йдуть через Монобанк
    use_monobank = payment_method in ('monobank', 'card', 'applepay', 'googlepay')

    if use_monobank and MONOBANK_TOKEN:
        import aiohttp
        mono_url = 'https://api.monobank.ua/api/merchant/invoice/create'
        headers = {'X-Token': MONOBANK_TOKEN, 'Content-Type': 'application/json'}
        
        # Відображаємо тільки той метод, який вибрав користувач
        methods_map = {
            'card': ['pan'],
            'applepay': ['applepay'],
            'googlepay': ['googlepay'],
            'monobank': ['monobank']
        }
        
        payload = {
            'amount': int(total * 100),
            'ccy': 980,
            'merchantPaymInfo': {
                'reference': str(oid),
                'destination': f'Замовлення #{oid} (Medelin)'
            },
            'redirectUrl': WEB_APP_URL,
            'validity': 3600,
            'paymentMethods': methods_map.get(payment_method, [])
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(mono_url, json=payload, headers=headers, timeout=15) as resp:
                    resp_data = await resp.json()
                    if resp.status == 200:
                        return {'status': 'ok', 'url': resp_data['pageUrl'], 'order_id': oid, 'provider': 'monobank'}
                    else:
                        # Якщо Монобанк повернув помилку, спробуємо LiqPay як запасний варіант
                        pass
        except Exception:
            # Якщо Монобанк недоступний, йдемо далі до LiqPay
            pass

    # LiqPay використовується для PrivatPay або як запасний варіант
    liqpay_paytypes = 'card'
    if payment_method == 'applepay':
        liqpay_paytypes = 'apay'
    elif payment_method == 'googlepay':
        liqpay_paytypes = 'gpay'
    elif payment_method == 'privatpay':
        liqpay_paytypes = 'privat24'

    liqpay_params = {
        'action': 'pay',
        'amount': total,
        'currency': 'UAH',
        'description': f'Замовлення #{oid} (Medelin)',
        'order_id': str(oid),
        'version': '3',
        'public_key': LIQPAY_PUBLIC_KEY,
        'result_url': WEB_APP_URL,
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
