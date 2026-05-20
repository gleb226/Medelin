
import base64
import hashlib
import json
import pathlib
import logging
import re
import aiohttp
from typing import Any
import asyncio
from contextlib import asynccontextmanager

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

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class RepayRequest(BaseModel):
    order_id: str
    payment_method: str

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
    async def fetch_wh(props):
        payload = {'apiKey': NP_API_KEY, 'modelName': 'Address', 'calledMethod': 'getWarehouses', 'methodProperties': props}
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.novaposhta.ua/v2.0/json/', json=payload) as resp:
                data = await resp.json()
                return data.get('data', [])

    props = {'SettlementRef': cityRef}
    if search:
        props['FindByString'] = search
    logger.info(f'Fetching warehouses for SettlementRef: {cityRef}, search: {search}')
    data = await fetch_wh(props)
    if not data:
        props_city = {'CityRef': cityRef}
        if search:
            props_city['FindByString'] = search
        data = await fetch_wh(props_city)
    if not data and cityName:
        clean_name = cityName.split(',')[0].strip()
        props_name = {'CityName': clean_name}
        if search:
            props_name['FindByString'] = search
        data = await fetch_wh(props_name)
    return data

@app.get('/api/orders/{order_id}')
async def get_order_details(order_id: str):
    oid_str = order_id.strip()
    logger.info(f"Fetching order details for ID: {oid_str}")
    try:
        order = await orders_db.get_order_by_id(oid_str)
        if not order:
            logger.warning(f"Order {oid_str} not found.")
            raise HTTPException(status_code=404, detail="Замовлення не знайдено.")
        
        total = order.get('total_amount', 0)
        cart = order.get('cart', '')
        
        if not total:
            if isinstance(cart, str):
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
        
        res = {
            "order_id": str(order['_id']),
            "total": total,
            "fullname": order.get('fullname'),
            "phone": order.get('phone'),
            "order_type": order.get('order_type'),
            "items_text": cart if isinstance(cart, str) else build_cart_text(cart)[1]
        }
        return res
    except Exception as e:
        logger.error(f"Error fetching order {oid_str}: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

async def notify_admins_about_order(order_id: str):
    order = await orders_db.get_order_by_id(order_id)
    if not order or order.get('notified_admin_ids'):
        return

    oid = str(order['_id'])
    fullname = order.get('fullname', 'Не вказано')
    phone = order.get('phone', 'Не вказано')
    tg_nick = order.get('username', '')
    loc_id = order.get('location_id', 'web')
    order_type = order.get('order_type', 'takeaway')
    total = order.get('total_amount', 0)
    items_text = order.get('cart', '')
    table_number = order.get('table_number', '')

    location_name = 'Замовлення з сайту'
    for loc in await location_db.get_all_locations():
        if str(loc.get('_id')) == loc_id:
            location_name = loc.get('name', 'Замовлення з сайту')
            break

    msg = f'✅ <b>ОПЛАЧЕНЕ ЗАМОВЛЕННЯ (#{oid})</b>\n\n'
    msg += f"👤 Клієнт: {fullname}\n"
    msg += f'📞 Телефон: <code>{phone}</code>\n'
    if tg_nick:
        msg += f"✈️ Telegram: {(tg_nick if tg_nick.startswith('@') else '@' + tg_nick)}\n"
    
    if order_type == 'nova_poshta':
        msg += f'🚚 Доставка: <b>Нова Пошта</b>\n'
    else:
        msg += f'🏛 Заклад: {location_name}\n'
        if order_type == 'in_house':
            msg += f"🪑 Тип: В закладі (Столик: {table_number or '—'})\n"
        else:
            msg += f'📦 Тип: З собою\n'

    msg += f'💰 Сума: <b>{total} грн</b>\n'
    msg += f"💳 Оплата: Онлайн (Сплачено)\n"
    
    wishes = order.get('wishes', '')
    clean_wishes = wishes.replace(f"TG: {tg_nick}", "").replace("TG: ", "").replace("МЕНЮ", "").strip()
    if clean_wishes:
        msg += f"💬 Побажання: {clean_wishes}\n"
        
    msg += f"\n🛒 Кошик:\n{items_text}"

    await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id if loc_id != 'web' else None)
    if BOSS_IDS:
        await orders_db.mark_admin_notified(oid, int(BOSS_IDS[0]))

@app.post('/api/payments/liqpay-callback-raw')
async def liqpay_callback_raw(request: Request):
    try:
        form_data = await request.form()
        data_b64 = form_data.get('data')
        signature = form_data.get('signature')
        if not data_b64 or not signature:
            return {"status": "error", "message": "Missing data"}

        sign_string = LIQPAY_PRIVATE_KEY + data_b64 + LIQPAY_PRIVATE_KEY
        expected_signature = base64.b64encode(hashlib.sha1(sign_string.encode('utf-8')).digest()).decode('utf-8')
        if signature != expected_signature:
            return {"status": "error", "message": "Invalid signature"}

        data = json.loads(base64.b64decode(data_b64).decode('utf-8'))
        order_id = data.get('order_id')
        if data.get('status') in ('success', 'wait_accept'):
            await orders_db.set_payment_id(order_id, data.get('payment_id'), data.get('liqpay_order_id'))
            await notify_admins_about_order(order_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"LiqPay callback error: {e}")
        return {"status": "error", "message": str(e)}

@app.post('/api/payments/monobank-callback')
async def monobank_callback(request: Request):
    try:
        data = await request.json()
        order_id = data.get('reference')
        if data.get('status') == 'success':
            invoice_id = data.get('invoiceId')
            await orders_db.set_payment_id(order_id, invoice_id, invoice_id)
            await notify_admins_about_order(order_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Monobank callback error: {e}")
        return {"status": "error", "message": str(e)}

@app.post('/api/repay')
async def process_repay(req: RepayRequest):
    order = await orders_db.get_order_by_id(req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено.")

    oid = str(order['_id'])
    total = order.get('total_amount', 0)
    if not total:
        cart = order.get('cart', '')
        if isinstance(cart, str):
            prices = re.findall(r'\((\d+)\s*грн\)', cart, re.IGNORECASE)
            if not prices: prices = re.findall(r'(\d+)\s*грн', cart, re.IGNORECASE)
            total = sum(int(p) for p in prices)
        elif isinstance(cart, list):
            for item in cart:
                try: total += int(item.get('price', 0))
                except: pass

    if total <= 0:
        raise HTTPException(status_code=400, detail="Сума замовлення 0.")

    if req.payment_method == 'monobank' and MONOBANK_TOKEN:
        payload = {
            'amount': int(total * 100), 'ccy': 980,
            'merchantPaymInfo': {'reference': oid, 'destination': f'Замовлення #{oid}'},
            'redirectUrl': WEB_APP_URL, 'webhookUrl': f"{WEB_APP_URL}/api/payments/monobank-callback",
            'validity': 3600
        }
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.monobank.ua/api/merchant/invoice/create', json=payload, headers={'X-Token': MONOBANK_TOKEN}) as resp:
                if resp.status == 200:
                    d = await resp.json()
                    return {'status': 'ok', 'url': d['pageUrl'], 'provider': 'monobank'}

    # Мапимо методи на типи оплати LiqPay
    liqpay_paytypes = 'card,privat24' # default
    if req.payment_method == 'googlepay': liqpay_paytypes = 'gpay'
    elif req.payment_method == 'applepay': liqpay_paytypes = 'apay'
    elif req.payment_method == 'privatpay': liqpay_paytypes = 'privat24'
    elif req.payment_method == 'card': liqpay_paytypes = 'card,privat24,gpay,apay'

    liqpay_params = {
        'action': 'pay', 'amount': total, 'currency': 'UAH', 'description': f'Замовлення #{oid}',
        'order_id': oid, 'version': '3', 'public_key': LIQPAY_PUBLIC_KEY, 'result_url': WEB_APP_URL,
        'server_url': f"{WEB_APP_URL}/api/payments/liqpay-callback-raw",
        'paytypes': liqpay_paytypes
    }
    encoded = base64.b64encode(json.dumps(liqpay_params).encode()).decode()
    sig = base64.b64encode(hashlib.sha1((LIQPAY_PRIVATE_KEY + encoded + LIQPAY_PRIVATE_KEY).encode()).digest()).decode()
    return {'status': 'ok', 'data': encoded, 'signature': sig, 'provider': 'liqpay'}

@app.post('/api/checkout')
async def process_checkout(req: CheckoutRequest):
    data = req.dict()
    total, items_text = build_cart_text(data.get('cart_menu', []))
    if total <= 0: raise HTTPException(status_code=400, detail='Кошик порожній')

    user = data.get('user_details', {})
    location = await resolve_location(user.get('location'))
    loc_id = str(location['_id']) if location else 'web'
    phone = format_phone(user.get('phone', '')) or user.get('phone', '—')
    tg_nick = user.get('tg_nick') or user.get('tg') or ''
    payment_mode = user.get('payment_mode') or 'pay_now'
    order_type = user.get('delivery_type') or ('takeaway' if user.get('type') == 'takeaway' else 'in_house')

    comment = user.get('comment', '').strip()
    wishes_str = f'TG: {tg_nick}'
    if comment:
        wishes_str += f'\nКоментар: {comment}'

    oid = await orders_db.add_order(
        user_id=None, username=tg_nick, fullname=user.get('name', '—'), phone=phone,
        location_id=loc_id, date_time='Сьогодні', people_count='1', wishes=wishes_str,
        cart=items_text, order_type=order_type, payment_mode=payment_mode,
        table_number=user.get('table_number', ''), total_amount=total
    )

    if payment_mode == 'pay_at_checkout':
        msg = f'🆕 <b>НОВЕ ЗАМОВЛЕННЯ (#{oid})</b>\n\n👤 {user.get("name")}\n📞 {phone}\n💰 {total} грн\n💳 Оплата на касі'
        if comment:
            msg += f'\n💬 Коментар: {comment}'
        msg += f'\n\n🛒 {items_text}'
        await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id if loc_id != 'web' else None)
        return {'status': 'ok', 'manual': True, 'order_id': oid}

    if data.get('payment_method') == 'monobank' and MONOBANK_TOKEN:
        payload = {
            'amount': int(total * 100), 'ccy': 980,
            'merchantPaymInfo': {'reference': str(oid), 'destination': f'Замовлення #{oid}'},
            'redirectUrl': WEB_APP_URL, 'webhookUrl': f"{WEB_APP_URL}/api/payments/monobank-callback",
            'validity': 3600
        }
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.monobank.ua/api/merchant/invoice/create', json=payload, headers={'X-Token': MONOBANK_TOKEN}) as resp:
                if resp.status == 200:
                    d = await resp.json()
                    return {'status': 'ok', 'url': d['pageUrl'], 'order_id': oid, 'provider': 'monobank'}

    # Мапимо методи на типи оплати LiqPay
    liqpay_paytypes = 'card,privat24'
    method = data.get('payment_method')
    if method == 'googlepay': liqpay_paytypes = 'gpay'
    elif method == 'applepay': liqpay_paytypes = 'apay'
    elif method == 'privatpay': liqpay_paytypes = 'privat24'
    elif method == 'card': liqpay_paytypes = 'card,privat24,gpay,apay'

    liqpay_params = {
        'action': 'pay', 'amount': total, 'currency': 'UAH', 'description': f'Замовлення #{oid}',
        'order_id': str(oid), 'version': '3', 'public_key': LIQPAY_PUBLIC_KEY, 'result_url': WEB_APP_URL,
        'server_url': f"{WEB_APP_URL}/api/payments/liqpay-callback-raw",
        'paytypes': liqpay_paytypes
    }
    encoded = base64.b64encode(json.dumps(liqpay_params).encode()).decode()
    sig = base64.b64encode(hashlib.sha1((LIQPAY_PRIVATE_KEY + encoded + LIQPAY_PRIVATE_KEY).encode()).digest()).decode()
    return {'status': 'ok', 'data': encoded, 'signature': sig, 'order_id': oid, 'provider': 'liqpay'}

@app.post('/api/booking')
async def process_booking(req: BookingRequest):
    data = req.dict()
    location = await resolve_location(data.get('location'))
    loc_id = str(location['_id']) if location else 'unknown'
    phone = format_phone(data.get('phone', '')) or data.get('phone')
    oid = await orders_db.add_order(None, data.get('tg', ''), data.get('name'), phone, loc_id, f"{data.get('date')} {data.get('time')}", data.get('guests'), data.get('wishes', ''), 'Бронювання', 'booking', 'cashier')
    msg = f'🛎 <b>БРОНЮВАННЯ</b>\n\n👤 {data.get("name")}\n📞 {phone}\n📅 {data.get("date")} {data.get("time")}\n👥 {data.get("guests")}'
    await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id if loc_id != 'unknown' else None)
    return {'status': 'ok', 'order_id': oid}

@app.get('/api/menu')
async def get_menu():
    data = public_data_cache.get('menu')
    if data is None: data = await public_data_cache.refresh_menu()
    return data

@app.get('/api/coffee')
async def get_coffee():
    data = public_data_cache.get('coffee')
    if data is None: data = await public_data_cache.refresh_coffee()
    return data

@app.get('/api/locations')
async def get_locations():
    data = public_data_cache.get('locations')
    if data is None: data = await public_data_cache.refresh_locations()
    return data

@app.get('/api/socials')
async def get_socials():
    data = public_data_cache.get('socials')
    if data is None: data = await public_data_cache.refresh_socials()
    return data

app.mount('/', StaticFiles(directory=str(_site_dir), html=True), name='site')
