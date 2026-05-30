
import base64
import hashlib
import json
import pathlib
import os
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

# Монтуємо статичні файли
def _resolve_site_dir() -> pathlib.Path | None:
    """
    Resolve MedelinSite directory across environments.

    Some deployments (e.g. Render) ship only the backend code, so the site
    directory may be absent. In that case we must not crash on startup.
    """
    env_dir = (os.getenv("SITE_DIR") or "").strip()
    if env_dir:
        p = pathlib.Path(env_dir)
        return p if p.exists() else None

    base_dir = pathlib.Path(__file__).resolve().parent
    candidates = [
        base_dir.parent / "MedelinSite",
        pathlib.Path("/usr/share/nginx/html"),
        pathlib.Path("/app/MedelinSite"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


_site_dir = _resolve_site_dir()

# Пріоритет для Render/Unified: папка /usr/share/nginx/html/images/uploads
# Потім папка /app/uploads (якщо використовується Persistent Disk)
# Інакше використовуємо локальну папку в MedelinSite
_uploads_dir = pathlib.Path("/usr/share/nginx/html/images/uploads")
if not _uploads_dir.exists():
    _uploads_dir = pathlib.Path("/app/uploads")
if not _uploads_dir.exists():
    if _site_dir:
        _uploads_dir = _site_dir / "images" / "uploads"
    else:
        _uploads_dir = pathlib.Path("./uploads")

_uploads_dir.mkdir(parents=True, exist_ok=True)

# Монтуємо /uploads для доступу через URL
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
    all_locs = await location_db.get_all_locations()
    
    # Спроба знайти за індексом (1, 2, 3...)
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(all_locs):
            return all_locs[idx]

    for loc in all_locs:
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
    logger.info(f"NP: Searching cities for '{search}'")
    if not NP_API_KEY:
        logger.error("NP_API_KEY is not set!")
        return []
    
    payload = {
        'apiKey': NP_API_KEY, 
        'modelName': 'Address', 
        'calledMethod': 'searchSettlements', 
        'methodProperties': {
            'CityName': search, 
            'Limit': '50'
        }
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post('https://api.novaposhta.ua/v2.0/json/', json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"NP API Status {resp.status}")
                    return []
                data = await resp.json()
                if not data.get('success'):
                    logger.error(f"NP Error: {data.get('errors')}")
                    return []
                res_data = data.get('data', [])
                if res_data and isinstance(res_data, list) and len(res_data) > 0:
                    # searchSettlements повертає список об'єктів, де перший містить Addresses
                    return res_data[0].get('Addresses', [])
                return []
        except Exception as e:
            logger.error(f"NP Exception (cities): {e}")
            return []

@app.get('/api/nova-poshta/warehouses')
async def get_np_warehouses(cityRef: str, cityName: str = None, search: str = None):
    if not NP_API_KEY:
        logger.error("NP_API_KEY is not set!")
        return []

    async def fetch_wh(props):
        payload = {'apiKey': NP_API_KEY, 'modelName': 'Address', 'calledMethod': 'getWarehouses', 'methodProperties': props}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post('https://api.novaposhta.ua/v2.0/json/', json=payload) as resp:
                    data = await resp.json()
                    if not data.get('success'):
                        logger.error(f"NP Error (warehouses): {data.get('errors')}")
                        return []
                    return data.get('data', [])
            except Exception as e:
                logger.error(f"NP Exception (fetch_wh): {e}")
                return []

    # Спробуємо по SettlementRef (сучасний спосіб)
    props = {'SettlementRef': cityRef}
    if search:
        props['FindByString'] = search
    logger.info(f'Fetching warehouses for SettlementRef: {cityRef}, search: {search}')
    data = await fetch_wh(props)
    
    # Якщо не вдалося, спробуємо по CityRef (старий спосіб)
    if not data:
        props_city = {'CityRef': cityRef}
        if search:
            props_city['FindByString'] = search
        data = await fetch_wh(props_city)
        
    # Якщо все ще немає, спробуємо по назві міста
    if not data and cityName:
        clean_name = cityName.split(',')[0].replace('м. ', '').replace('місто ', '').strip()
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
    user_id = order.get('user_id')
    loc_id = order.get('location_id', 'web')
    order_type = order.get('order_type', 'takeaway')
    total = order.get('total_amount', 0)
    items_text = order.get('cart', '')
    table_number = order.get('table_number', '')
    date_time = order.get('date_time', '—')
    people_count = order.get('people_count', '—')
    wishes = order.get('wishes') or ''

    location_name = 'Замовлення з сайту'
    for loc in await location_db.get_all_locations():
        if str(loc.get('_id')) == loc_id:
            location_name = loc.get('name', 'Замовлення з сайту')
            break

    msg = f'✅ <b>ОПЛАЧЕНЕ ЗАМОВЛЕННЯ</b>\n\n'
    msg += f"👤 Клієнт: {fullname}\n"
    msg += f'📞 Телефон: <code>{phone}</code>\n'
    if tg_nick:
        msg += f"✈️ Telegram: {(tg_nick if tg_nick.startswith('@') else '@' + tg_nick)}\n"
    
    if order_type == 'nova_poshta' or order_type == 'beans_delivery':
        msg += f'🚚 Доставка: <b>Нова Пошта</b>\n'
        if 'НП:' in wishes:
            msg += f"📍 Адреса: {wishes.split('НП:')[1].split('|')[0].strip()}\n"
    elif order_type == 'beans_booking':
        msg += f'🏛 Заклад: {location_name}\n'
        msg += f'📦 Тип: Самовивіз зерен\n'
    elif order_type == 'order_with_booking':
        msg += f'🏛 Заклад: {location_name}\n'
        msg += f'🕒 Час: {date_time}\n'
        msg += f'👥 Гостей: {people_count}\n'
        msg += f'📝 Тип: Бронювання + Замовлення\n'
    else:
        msg += f'🏛 Заклад: {location_name}\n'
        if order_type == 'in_house':
            msg += f"🪑 Тип: В закладі (Столик: {table_number or '—'})\n"
        else:
            msg += f'📦 Тип: З собою\n'

    msg += f'💰 Сума: <b>{total} грн</b>\n'
    msg += f"💳 Оплата: Онлайн (Сплачено)\n"
    
    clean_wishes = wishes.replace(f"TG: {tg_nick}", "").replace("TG: ", "").replace("МЕНЮ", "").strip()
    if clean_wishes:
        import html
        msg += f"💬 Побажання: {html.escape(clean_wishes)}\n"
        
    msg += f"\n🛒 Кошик:\n{items_text}"

    # Додаємо в активні якщо ще немає
    from app.databases.active_orders_database import active_orders_db
    from app.databases.active_bookings_database import active_bookings_db
    
    if order_type == 'order_with_booking':
        await active_bookings_db.add_active_booking(oid, user_id, fullname, phone, loc_id, date_time, people_count, wishes)
    else:
        await active_orders_db.add_active_order(oid, user_id, fullname, phone, loc_id, items_text, order_type, table_number)

    await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id)
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

    if order_type == 'nova_poshta':
        loc_id = 'NP'
    
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
        msg = f'🆕 <b>НОВЕ ЗАМОВЛЕННЯ</b>\n\n👤 {user.get("name")}\n📞 {phone}\n💰 {total} грн\n💳 Оплата на касі'
        
        if order_type == 'nova_poshta':
            msg += f'\n🚚 Доставка: <b>Нова Пошта</b>'
        else:
            loc_name_disp = location.get('name', 'Замовлення з сайту') if location else 'Замовлення з сайту'
            msg += f'\n🏛 Заклад: {loc_name_disp}'
            if order_type == 'in_house':
                msg += f"\n🪑 Тип: В закладі (Столик: {user.get('table_number', '—')})"
            else:
                msg += f'\n📦 Тип: З собою'

        if comment:
            import html
            msg += f'\n💬 Коментар: {html.escape(comment)}'
        msg += f'\n\n🛒 {items_text}'
        await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id)
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
    await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id)
    return {'status': 'ok', 'order_id': oid}

from fastapi.responses import HTMLResponse, FileResponse
from fastapi import Request
from app.common.config import ADMIN_PANEL_PASSWORD

@app.get('/admin-panel')
async def get_admin_panel(request: Request):
    auth = request.query_params.get('auth')
    if auth == ADMIN_PANEL_PASSWORD:
        admin_path = _site_dir / "admin-panel.html"
        if admin_path.exists():
            return FileResponse(admin_path)
    
    # If not authorized, show the "stealth" login page which looks like a 404
    login_path = _site_dir / "admin-login.html"
    if login_path.exists():
        return FileResponse(login_path)
    
    raise HTTPException(status_code=404, detail="Not Found")

# Admin API endpoints
def check_admin_auth(request: Request):
    # Simple check for now based on query param or header
    auth = request.query_params.get('auth') or request.headers.get('Authorization')
    if auth != ADMIN_PANEL_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get('/api/admin/active-orders')
async def get_admin_active_orders(request: Request):
    check_admin_auth(request)
    from app.databases.active_orders_database import active_orders_db
    return await active_orders_db.get_all_active_orders()

@app.get('/api/admin/active-bookings')
async def get_admin_active_bookings(request: Request):
    check_admin_auth(request)
    from app.databases.active_bookings_database import active_bookings_db
    return await active_bookings_db.get_all_active_bookings()

@app.post('/api/admin/orders/{order_id}/complete')
async def complete_order(order_id: str, request: Request):
    check_admin_auth(request)
    from app.databases.active_orders_database import active_orders_db
    from app.databases.sales_database import sales_db
    
    order = await active_orders_db.get_active_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Move to sales
    await sales_db.add_sale(
        order_id=order_id,
        user_id=order.get('user_id'),
        fullname=order.get('fullname'),
        items=order.get('items'),
        total=order.get('total', 0),
        location_id=order.get('location_id')
    )
    await active_orders_db.delete_active_order(order_id)
    return {"status": "ok"}

@app.post('/api/admin/orders/{order_id}/cancel')
async def cancel_order(order_id: str, request: Request, reason: str = Form("Скасовано адміном")):
    check_admin_auth(request)
    from app.databases.active_orders_database import active_orders_db
    await active_orders_db.delete_active_order(order_id)
    return {"status": "ok"}

@app.delete('/api/admin/bookings/{booking_id}')
async def delete_booking(booking_id: str, request: Request):
    check_admin_auth(request)
    from app.databases.active_bookings_database import active_bookings_db
    await active_bookings_db.remove_booking(booking_id)
    return {"status": "ok"}

@app.get('/api/admin/menu')
async def admin_get_menu(request: Request):
    check_admin_auth(request)
    from app.databases.menu_database import menu_db
    return await menu_db.get_all_items_detailed()

@app.post('/api/admin/menu')
async def admin_save_menu_item(request: Request):
    check_admin_auth(request)
    item = await request.json()
    from app.databases.menu_database import menu_db
    
    item_id = item.get('id')
    if item_id:
        await menu_db.update_item(item_id, item)
    else:
        await menu_db.add_item(item)
    
    await public_data_cache.refresh_menu()
    return {"status": "ok"}

@app.delete('/api/admin/menu/{item_id}')
async def admin_delete_menu_item(item_id: str, request: Request):
    check_admin_auth(request)
    from app.databases.menu_database import menu_db
    await menu_db.delete_item(item_id)
    await public_data_cache.refresh_menu()
    return {"status": "ok"}

@app.get('/api/admin/beans')
async def admin_get_beans(request: Request):
    check_admin_auth(request)
    from app.databases.coffee_beans_database import coffee_beans_db
    return await coffee_beans_db.get_all_beans()

@app.post('/api/admin/beans')
async def admin_save_bean(request: Request):
    check_admin_auth(request)
    bean = await request.json()
    from app.databases.coffee_beans_database import coffee_beans_db
    
    bean_id = bean.get('_id')
    if bean_id:
        await coffee_beans_db.update_bean(bean_id, bean)
    else:
        await coffee_beans_db.add_bean(bean)
    
    await public_data_cache.refresh_coffee()
    return {"status": "ok"}

@app.delete('/api/admin/beans/{bean_id}')
async def admin_delete_bean(bean_id: str, request: Request):
    check_admin_auth(request)
    from app.databases.coffee_beans_database import coffee_beans_db
    await coffee_beans_db.delete_bean(bean_id)
    await public_data_cache.refresh_coffee()
    return {"status": "ok"}

@app.get('/api/admin/support/chats')
async def admin_get_chats(request: Request):
    check_admin_auth(request)
    from app.databases.guest_messages_database import guest_messages_db
    return await guest_messages_db.get_unique_chats()

@app.get('/api/admin/support/messages')
async def admin_get_messages(request: Request, phone: str = None, order_id: str = None):
    check_admin_auth(request)
    from app.databases.guest_messages_database import guest_messages_db
    return await guest_messages_db.get_messages(phone, order_id)

@app.post('/api/admin/support/reply')
async def admin_reply_support(request: Request):
    check_admin_auth(request)
    data = await request.json()
    phone = data.get('phone')
    order_id = data.get('order_id')
    text = data.get('text')
    
    from app.databases.guest_messages_database import guest_messages_db
    await guest_messages_db.add_message(order_id, phone, 'admin', text)
    
    # Also try to send to Telegram if user is a TG user
    # This part requires finding the user's telegram ID, which might be linked to the phone
    # For now, we at least record it in the DB.
    
    return {"status": "ok"}

@app.get('/api/menu')
async def get_menu():
    data = await public_data_cache.refresh_menu()
    return data

@app.get('/api/coffee')
async def get_coffee():
    data = await public_data_cache.refresh_coffee()
    return data

@app.get('/api/locations')
async def get_locations():
    data = await public_data_cache.refresh_locations()
    return data

@app.get('/api/socials')
async def get_socials():
    data = await public_data_cache.refresh_socials()
    return data

if _site_dir:
    app.mount('/', StaticFiles(directory=str(_site_dir), html=True), name='site')
else:
    logger.warning("MedelinSite directory not found; skipping static site mount. Set SITE_DIR to enable it.")
