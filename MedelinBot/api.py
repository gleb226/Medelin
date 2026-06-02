import base64
import hashlib
import json
import pathlib
import os
import logging
import re
import html
import aiohttp
from typing import Any
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
import secrets
import fastapi

from app.common.config import DEVELOPER_IDS, LIQPAY_PRIVATE_KEY, LIQPAY_PUBLIC_KEY, MONOBANK_TOKEN, WEB_APP_URL, NP_API_KEY, ADMIN_PANEL_PASSWORD
from app.databases.guest_messages_database import guest_messages_db
from app.databases.location_database import location_db
from app.databases.orders_database import orders_db
from app.databases.admin_database import admin_db
from app.keyboards import admin_keyboards as akb
from app.utils.admin_notifications import send_admin_notification, send_developer_error
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin API Auth
async def get_current_admin(request: Request):
    auth_header = request.headers.get('Authorization')
    token = None
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    else:
        token = request.query_params.get('token')
        
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    admin = await admin_db.verify_session(token)
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid session")
    return admin

@app.post('/api/admin/login')
async def admin_login(data: dict):
    identifier = str(data.get('identifier', '')).strip()
    password = str(data.get('password', '')).strip()
    
    # Check fixed password 0707 or the one from ENV
    if password != '0707' and password != ADMIN_PANEL_PASSWORD:
        raise HTTPException(status_code=401, detail="Невірний пароль")
        
    admin = await admin_db.find_admin_by_identifier(identifier)
        
    if not admin or not admin.get('user_id'):
        raise HTTPException(status_code=404, detail="Адміністратора не знайдено")
        
    # Generate 2FA request
    code = secrets.token_hex(3).upper() 
    await admin_db.create_auth_request(admin['user_id'], code)
    
    # Send confirmation to bot
    msg = f"🔐 <b>СПРОБА ВХОДУ В АДМІН-ПАНЕЛЬ</b>\n\n"
    msg += f"Ви намагаєтесь увійти в адмін-панель Medelin.\n"
    msg += f"Якщо це не ви, проігноруйте або заблокуйте доступ."
    
    from app.common.bot_instance import bot
    try:
        await bot.send_message(
            admin['user_id'], 
            msg, 
            parse_mode='HTML',
            reply_markup=akb.get_admin_login_confirm_kb(admin['user_id'])
        )
    except Exception as e:
        logger.error(f"Failed to send 2FA message to {admin['user_id']}: {e}")
        if admin.get('role') == 'developer':
             raise HTTPException(status_code=500, detail="Ви розробник, але бот не може надіслати вам повідомлення. Будь ласка, напишіть боту /start або будь-яке повідомлення.")
        raise HTTPException(status_code=500, detail="Не вдалося надіслати повідомлення в Telegram. Переконайтеся, що ви почали діалог з ботом.")
        
    return {"status": "ok", "user_id": admin['user_id']}

@app.get('/api/admin/verify')
async def admin_verify(user_id: int):
    req = await admin_db.get_auth_request(user_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if not req.get('confirmed'):
        return {"status": "pending"}
        
    # Validated! Create session
    token = secrets.token_urlsafe(32)
    await admin_db.create_session(user_id, token)
    
    admin = await admin_db.get_admin_by_id(user_id)
    # If it was a temporary dev admin not in DB, create basic info
    if not admin:
        if str(user_id) in DEVELOPER_IDS:
             admin = {'display_name': 'Developer', 'role': 'developer'}
        else:
             # Should not happen if verified
             admin = {'display_name': f'Admin {user_id}', 'role': 'admin'}

    return {
        "status": "ok", 
        "token": token,
        "admin": {
            "name": admin.get('display_name') or admin.get('name') or 'Admin',
            "role": admin.get('role') or 'admin'
        }
    }

# Монтуємо статичні файли
def _resolve_site_dir() -> pathlib.Path | None:
    """
    Resolve MedelinSite directory across environments.
    """
    env_dir = (os.getenv("SITE_DIR") or "").strip()
    if env_dir:
        p = pathlib.Path(env_dir)
        return p if p.exists() else None

    base_dir = pathlib.Path(__file__).resolve().parent
    candidates = [
        base_dir.parent / "MedelinSite",
        pathlib.Path("/app/MedelinSite"),
        pathlib.Path("/usr/share/nginx/html"),
    ]
    for p in candidates:
        if p.exists() and (p / "index.html").exists():
            return p
    return None

_site_dir = _resolve_site_dir()

# Пріоритет для Render/Unified: папка /usr/share/nginx/html/assets/images/uploads
_uploads_dir = pathlib.Path("/usr/share/nginx/html/assets/images/uploads")
if not _uploads_dir.exists():
    if _site_dir:
        _uploads_dir = _site_dir / "assets" / "images" / "uploads"
    else:
        _uploads_dir = pathlib.Path("/app/MedelinSite/assets/images/uploads")

if not _uploads_dir.exists():
    _uploads_dir = pathlib.Path("/app/uploads")

_uploads_dir.mkdir(parents=True, exist_ok=True)

# Монтуємо /uploads для доступу через URL
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")
app.mount("/cache", StaticFiles(directory=str(public_data_cache._dir)), name="cache")

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

def _clean_text(value, default=''):
    return str(value if value is not None else default).strip()

def _to_int(value, default=0):
    try:
        if value in (None, ''):
            return default
        return int(float(str(value).replace(',', '.')))
    except Exception:
        return default

def _to_float(value, default=0):
    try:
        if value in (None, ''):
            return default
        return float(str(value).replace(',', '.'))
    except Exception:
        return default

def _parse_locations(value):
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return [x.strip() for x in str(value or '').split(',') if x.strip()]

def _has_field(data: dict, key: str) -> bool:
    return key in data and data.get(key) is not None

def _flatten_public_menu(menu_data: Any) -> list[dict[str, Any]]:
    if not isinstance(menu_data, list):
        return []
    rows: list[dict[str, Any]] = []
    for section in menu_data:
        if not isinstance(section, dict):
            continue
        category = section.get('category', '')
        for item in section.get('items') or []:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row['category'] = category
            row['id'] = str(row.get('id') or row.get('_id') or '')
            rows.append(row)
    return rows

def _load_site_data_json(name: str) -> Any | None:
    if not _site_dir:
        return None
    path = _site_dir / "assets" / "data" / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to read site data %s: %s", path, e)
        return None

def _safe_alert_text(value: Any, limit: int = 900) -> str:
    text = html.escape(str(value or '').strip())
    return text[:limit] + ('...' if len(text) > limit else '')

def build_cart_text(cart_menu: list) -> tuple[int, str]:
    total = 0
    items = []
    for item in cart_menu:
        price = parse_price(item.get('price', 0))
        total += price
        items.append(f"- {item['name']} ({price} грн)")
    return (total, '\n'.join(items))

async def create_monobank_invoice(order_id: str, total: int | float) -> str:
    if not MONOBANK_TOKEN:
        raise HTTPException(status_code=503, detail="MonoPay token is not configured")

    payload = {
        'amount': int(total * 100), 'ccy': 980,
        'merchantPaymInfo': {'reference': str(order_id), 'destination': f'Order #{order_id}'},
        'redirectUrl': WEB_APP_URL, 'webhookUrl': f"{WEB_APP_URL}/api/payments/monobank-callback",
        'validity': 3600
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.monobank.ua/api/merchant/invoice/create', json=payload, headers={'X-Token': MONOBANK_TOKEN}) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = {'raw': await resp.text()}
            if resp.status == 200 and data.get('pageUrl'):
                return data['pageUrl']
            
            error_hint = ""
            if resp.status == 403:
                error_hint = "\n\n💡 <i>Ймовірно, використовується особистий токен замість Merchant токена або еквайринг не активовано.</i>"
            
            await send_developer_error(
                f"💳 <b>MONOPAY INVOICE FAILED</b>\n\n"
                f"<b>Order:</b> <code>{html.escape(str(order_id))}</code>\n"
                f"<b>Status:</b> <code>{resp.status}</code>\n"
                f"<b>Response:</b>\n<pre>{_safe_alert_text(data, 900)}</pre>{error_hint}"
            )
            raise HTTPException(status_code=502, detail="MonoPay invoice was not created")

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

    # 1. Спробуємо через SettlementRef (найбільш точно для малих населених пунктів)
    props = {'SettlementRef': cityRef}
    if search: props['FindByString'] = search
    data = await fetch_wh(props)
    
    # 2. Спробуємо через CityRef (для великих міст)
    if not data:
        props_city = {'CityRef': cityRef}
        if search: props_city['FindByString'] = search
        data = await fetch_wh(props_city)
        
    # 3. Спробуємо через CityName (як крайній захід)
    if not data and cityName:
        clean_name = cityName.split(',')[0].replace('м. ', '').replace('місто ', '').strip()
        props_name = {'CityName': clean_name}
        if search: props_name['FindByString'] = search
        data = await fetch_wh(props_name)
        
    # 4. Якщо все ще немає, але є cityRef, який схожий на назву міста (не UUID)
    if not data and cityRef and len(cityRef) > 2 and '-' not in cityRef:
         props_name = {'CityName': cityRef.split(',')[0].replace('м. ', '').replace('місто ', '').strip()}
         if search: props_name['FindByString'] = search
         data = await fetch_wh(props_name)
         
    return data

@app.get('/api/orders/{order_id}')
async def get_order_details(order_id: str):
    oid_str = order_id.strip()
    try:
        order = await orders_db.get_order_by_id(oid_str)
        if not order:
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
        
        return {
            "order_id": str(order['_id']),
            "total": total,
            "fullname": order.get('fullname'),
            "phone": order.get('phone'),
            "order_type": order.get('order_type'),
            "items_text": cart if isinstance(cart, str) else build_cart_text(cart)[1]
        }
    except Exception as e:
        logger.error(f"Error fetching order {oid_str}: {str(e)}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/client-error')
async def report_client_error(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    source = _safe_alert_text(data.get('source') or 'site', 120)
    message = _safe_alert_text(data.get('message') or 'Client error')
    context = _safe_alert_text(data.get('context') or '', 700)
    path = _safe_alert_text(data.get('path') or str(request.url), 300)
    user_agent = _safe_alert_text(request.headers.get('user-agent', ''), 300)
    await send_developer_error(
        f"🌐 <b>SITE CLIENT ERROR</b>\n\n"
        f"<b>Source:</b> <code>{source}</code>\n"
        f"<b>Message:</b>\n<pre>{message}</pre>\n"
        f"<b>Path:</b>\n<pre>{path}</pre>\n"
        f"<b>Context:</b>\n<pre>{context or '—'}</pre>\n"
        f"<b>User-Agent:</b>\n<pre>{user_agent or '—'}</pre>"
    )
    return {"status": "ok"}

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
        loc_actual_id = str(loc.get('_id'))
        if loc_actual_id == loc_id:
            location_name = loc.get('name', 'Замовлення з сайту')
            break

    msg = f'✅ <b>ОПЛАЧЕНЕ ЗАМОВЛЕННЯ</b>\n\n'
    msg += f"👤 Клієнт: {fullname}\n"
    if phone and phone != '—':
        msg += f'📞 Телефон: <code>{phone}</code>\n'
    if tg_nick:
        msg += f"✈️ Telegram: {(tg_nick if tg_nick.startswith('@') else '@' + tg_nick)}\n"
    
    if order_type == 'nova_poshta' or order_type == 'beans_delivery':
        addr = '—'
        if wishes and 'НП:' in wishes:
            addr = wishes.split('НП:')[1].split('|')[0].strip()
        elif wishes and 'ВАГА:' in wishes and 'НП:' in wishes:
             addr = wishes.split('НП:')[1].strip()
        
        msg += f'🚚 Доставка: <b>Нова Пошта — {addr}</b>\n'
    elif order_type == 'beans_booking':
        msg += f'🏛 Заклад: {location_name}\n'
        msg += f'📦 Тип: Самовивіз зерен\n'
    elif order_type == 'order_with_booking':
        msg += f'🏛 Заклад: {location_name}\n'
        if date_time and str(date_time).lower() not in ('none', '—', ''):
            msg += f'🕒 Час: {date_time}\n'
        if people_count and str(people_count).lower() not in ('none', '—', '', '0'):
            msg += f'👥 Гостей: {people_count}\n'
        msg += f'📝 Тип: Бронювання + Замовлення\n'
    else:
        if location_name and location_name not in ('Замовлення з сайту', '—'):
            msg += f'🏛 Заклад: {location_name}\n'
        
        if order_type == 'in_house':
            msg += f"🪑 Тип: В закладі (Столик: {table_number or '—'})\n"
        else:
            msg += f'📦 Тип: З собою\n'
        
        if date_time and str(date_time).lower() not in ('none', '—', 'сьогодні', '', 'зараз', 'по готовності'):
            msg += f'🕒 Час: {date_time}\n'

    msg += f'💰 Сума: <b>{total} грн</b>\n'
    
    payment_status = "Онлайн (Сплачено)"
    if order.get('payment_mode') == 'pay_at_checkout' or order.get('payment_method') == 'cash':
        payment_status = "Післяплата (Наложений платіж)"
    
    msg += f"💳 Оплата: <b>{payment_status}</b>\n"
    
    clean_wishes = wishes.replace(f"TG: {tg_nick}", "").replace("TG: ", "").replace("МЕНЮ", "").strip()
    if clean_wishes:
        import html
        msg += f"💬 Побажання: {html.escape(clean_wishes)}\n"
        
    msg += f"\n🛒 Кошик:\n{items_text}"

    # Додаємо в активні якщо ще немає
    from app.databases.active_orders_database import active_orders_db
    from app.databases.active_bookings_database import active_bookings_db
    
    if order_type == 'order_with_booking':
        await active_orders_db.add_active_order(oid, user_id, fullname, phone, loc_id, items_text, order_type, table_number, total, order.get('payment_mode', ''), wishes)
    else:
        await active_orders_db.add_active_order(oid, user_id, fullname, phone, loc_id, items_text, order_type, table_number, total, order.get('payment_mode', ''), wishes)

    await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id)
    if DEVELOPER_IDS:
        await orders_db.mark_admin_notified(oid, int(DEVELOPER_IDS[0]))

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

    # Prioritize MonoPay if token is configured
    if MONOBANK_TOKEN and req.payment_method in ['monobank', 'applepay', 'googlepay', 'card']:
        try:
            url = await create_monobank_invoice(oid, total)
            return {'status': 'ok', 'url': url, 'provider': 'monobank'}
        except Exception as e:
            logger.error(f"MonoPay failed, falling back to LiqPay: {e}")
            # Continue to LiqPay fallback below

    if req.payment_method == '_disabled_monobank_legacy':
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

    liqpay_paytypes = 'card'
    if req.payment_method == 'googlepay': liqpay_paytypes = 'gpay'
    elif req.payment_method == 'applepay': liqpay_paytypes = 'apay'
    elif req.payment_method == 'privatpay': liqpay_paytypes = 'privat24'
    elif req.payment_method == 'card': liqpay_paytypes = 'card'

    result_url = WEB_APP_URL
    if '?' in result_url:
        result_url += f"&payment=success&order_id={oid}"
    else:
        result_url += f"?payment=success&order_id={oid}"

    liqpay_params = {
        'action': 'pay', 'amount': total, 'currency': 'UAH', 'description': f'Замовлення #{oid}',
        'order_id': oid, 'version': '3', 'public_key': LIQPAY_PUBLIC_KEY, 'result_url': result_url,
        'server_url': f"{WEB_APP_URL}/api/payments/liqpay-callback-raw",
        'paytypes': liqpay_paytypes
    }
    encoded = base64.b64encode(json.dumps(liqpay_params).encode()).decode()
    sig = base64.b64encode(hashlib.sha1((LIQPAY_PRIVATE_KEY + encoded + LIQPAY_PRIVATE_KEY).encode()).digest()).decode()
    return {'status': 'ok', 'data': encoded, 'signature': sig, 'provider': 'liqpay'}

@app.post("/api/guest-message")
async def guest_message(data: dict):
    from app.utils.admin_notifications import send_admin_notification
    name = data.get('name', 'Гість')
    contact = data.get('contact', 'Не вказано')
    msg = data.get('message', '')
    
    text = f"💬 <b>НОВЕ ПОВІДОМЛЕННЯ З САЙТУ</b>\n\n"
    text += f"👤 Від: <b>{name}</b>\n"
    text += f"📞 Контакт: <code>{contact}</code>\n\n"
    text += f"📝 Повідомлення:\n{msg}"
    
    await send_admin_notification(text)
    return {"status": "ok"}

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
    if order_type == 'nova_poshta':
        np_city = (user.get('np_city_name') or '').strip()
        np_warehouse = (user.get('np_warehouse') or '').strip()
        if np_city or np_warehouse:
            wishes_str += f'\nНП: {np_city}, {np_warehouse}'.strip()
    if comment:
        wishes_str += f'\nКоментар: {comment}'

    oid = await orders_db.add_order(
        user_id=None, username=tg_nick, fullname=user.get('name', '—'), phone=phone,
        location_id=loc_id, date_time=None, people_count=None, wishes=wishes_str,
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
        from app.databases.active_orders_database import active_orders_db
        await active_orders_db.add_active_order(
            oid, None, user.get('name', '—'), phone, loc_id, items_text,
            order_type, user.get('table_number', ''), total, payment_mode, wishes_str
        )
        await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id)
        return {'status': 'ok', 'manual': True, 'order_id': oid}

    # Prioritize MonoPay if token is configured
    method = data.get('payment_method')
    if MONOBANK_TOKEN and method in ['monobank', 'applepay', 'googlepay', 'card']:
        try:
            url = await create_monobank_invoice(str(oid), total)
            return {'status': 'ok', 'url': url, 'order_id': oid, 'provider': 'monobank'}
        except Exception as e:
            logger.error(f"MonoPay failed in checkout, falling back to LiqPay: {e}")
            # Continue to LiqPay fallback below

    if data.get('payment_method') == '_disabled_monobank_legacy':
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

    liqpay_paytypes = 'card'
    if method == 'googlepay': liqpay_paytypes = 'gpay'
    elif method == 'applepay': liqpay_paytypes = 'apay'
    elif method == 'privatpay': liqpay_paytypes = 'privat24'
    elif method == 'card': liqpay_paytypes = 'card'

    result_url = WEB_APP_URL
    if '?' in result_url:
        result_url += f"&payment=success&order_id={oid}"
    else:
        result_url += f"?payment=success&order_id={oid}"

    liqpay_params = {
        'action': 'pay', 'amount': total, 'currency': 'UAH', 'description': f'Замовлення #{oid}',
        'order_id': str(oid), 'version': '3', 'public_key': LIQPAY_PUBLIC_KEY, 'result_url': result_url,
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

@app.get('/admin-panel')
async def get_admin_panel(request: Request):
    auth = request.query_params.get('auth')
    
    # Тільки валідний токен сесії дозволяє перегляд. 
    # Статичний пароль ADMIN_PANEL_PASSWORD більше не пускає в адмінку напряму,
    # а лише дозволяє відкрити форму входу (якщо потрібно) або ми просто редиректимо на 404.
    
    if auth:
        admin = await admin_db.verify_session(auth)
        if admin:
            admin_path = _site_dir / "admin-panel.html"
            if admin_path.exists():
                return FileResponse(admin_path)
    
    # Якщо токен невірний або його немає — показуємо 404 (де прихована форма входу)
    login_path = _site_dir / "404.html"
    if login_path.exists():
        return FileResponse(login_path)
    
    raise HTTPException(status_code=404, detail="Not Found")

# Admin API endpoints
async def _admin_visible_location_ids(admin: dict):
    role = admin.get('role') or 'admin'
    if role in ('super', 'boss', 'owner', 'developer'):
        return None
    if role == 'delivery_manager':
        return ['NP']
    user_id = admin.get('user_id')
    shift_loc = await admin_db.is_on_shift(user_id) if user_id else False
    if isinstance(shift_loc, str) and shift_loc not in ("True", "1", "False", "0"):
        return [shift_loc]
    locs = await admin_db.get_locations_for_admin(user_id) if user_id else []
    return locs or None

async def _decorate_active_order(order: dict):
    loc_id = str(order.get('location_id') or '')
    order_type = order.get('order_type')
    location_name = 'Сайт'
    if loc_id == 'NP' or order_type in ('nova_poshta', 'beans_delivery'):
        location_name = 'Нова Пошта'
        wishes = order.get('wishes') or ''
        if 'НП:' in wishes:
            location_name = f"Нова Пошта — {wishes.split('НП:', 1)[1].split('|', 1)[0].strip()}"
    elif loc_id and loc_id not in ('web', 'unknown', 'None'):
        loc = await location_db.get_location_by_id(loc_id)
        if loc:
            location_name = loc.get('name') or loc.get('address') or location_name

    full_order = await orders_db.get_order_by_id(str(order.get('order_id')))
    if full_order:
        if not order.get('total'):
            order['total'] = full_order.get('total_amount', 0)
        if not order.get('payment_mode'):
            order['payment_mode'] = full_order.get('payment_mode', '')
        order['is_paid'] = bool(full_order.get('payment_id') or full_order.get('provider_payment_id'))
    else:
        order['is_paid'] = False
    order['location_name'] = location_name
    return order

@app.get('/api/admin/me')
async def admin_me(admin: dict = fastapi.Depends(get_current_admin)):
    user_id = admin.get('user_id')
    shift = await admin_db.is_on_shift(user_id) if user_id else False
    locations = await admin_db.get_locations_for_admin(user_id) if user_id else []
    return {
        "user_id": user_id,
        "name": admin.get('display_name') or admin.get('name') or 'Admin',
        "role": admin.get('role') or 'admin',
        "is_on_shift": shift,
        "locations": locations,
    }

@app.post('/api/admin/uploads')
async def admin_upload_image(file: UploadFile = File(...), admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    content_type = (file.content_type or '').lower()
    if not content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only images are allowed")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image is too large")

    stem = secrets.token_hex(5)
    try:
        from PIL import Image, ImageOps
        import io
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        img = img.convert('RGBA') if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info) else img.convert('RGB')
        filename = f'{stem}.webp'
        img.save(str(_uploads_dir / filename), 'WEBP', quality=85, method=6)
    except Exception:
        ext = pathlib.Path(file.filename or '').suffix.lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            ext = '.jpg'
        filename = f'{stem}{ext}'
        (_uploads_dir / filename).write_bytes(raw)
    return {"url": f"/uploads/{filename}"}

@app.post('/api/admin/shift/start')
async def admin_start_shift(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if (admin.get('role') or 'admin') != 'admin':
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    loc_id = _clean_text(data.get('location_id'))
    allowed = await admin_db.get_locations_for_admin(admin.get('user_id'))
    if allowed and loc_id not in [str(x) for x in allowed]:
        raise HTTPException(status_code=403, detail="No location access")
    if not loc_id:
        raise HTTPException(status_code=400, detail="Location is required")
    await admin_db.set_shift_status(admin.get('user_id'), loc_id)
    return {"status": "ok"}

@app.post('/api/admin/shift/end')
async def admin_end_shift(admin: dict = fastapi.Depends(get_current_admin)):
    if (admin.get('role') or 'admin') != 'admin':
        raise HTTPException(status_code=403, detail="Forbidden")
    await admin_db.set_shift_status(admin.get('user_id'), False)
    return {"status": "ok"}

@app.get('/api/admin/active-orders')
async def get_admin_active_orders(admin: dict = fastapi.Depends(get_current_admin)):
    from app.databases.active_orders_database import active_orders_db
    locs = await _admin_visible_location_ids(admin)
    orders = await active_orders_db.get_active_orders(locs)
    return [await _decorate_active_order(o) for o in orders]

@app.get('/api/admin/active-bookings')
async def get_admin_active_bookings(admin: dict = fastapi.Depends(get_current_admin)):
    return await get_admin_active_orders(admin)

@app.post('/api/admin/orders/{order_id}/complete')
async def complete_order(order_id: str, admin: dict = fastapi.Depends(get_current_admin)):
    from app.databases.active_orders_database import active_orders_db
    from app.databases.sales_database import sales_db
    
    order = await active_orders_db.get_active_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    full_order = await orders_db.get_order_by_id(order_id)
    
    await sales_db.add_sale(
        order_id=order_id,
        user_id=order.get('user_id'),
        fullname=order.get('fullname'),
        items=order.get('cart') or order.get('items'),
        total=order.get('total') or (full_order or {}).get('total_amount', 0),
        location_id=order.get('location_id')
    )
    await active_orders_db.delete_active_order(order_id)
    return {"status": "ok"}

@app.post('/api/admin/orders/{order_id}/cancel')
async def cancel_order(order_id: str, admin: dict = fastapi.Depends(get_current_admin), reason: str = Form("Скасовано адміном")):
    from app.databases.active_orders_database import active_orders_db
    await active_orders_db.delete_active_order(order_id)
    return {"status": "ok"}

@app.delete('/api/admin/bookings/{booking_id}')
async def delete_booking(booking_id: str, admin: dict = fastapi.Depends(get_current_admin)):
    from app.databases.active_bookings_database import active_bookings_db
    await active_bookings_db.remove_booking(booking_id)
    return {"status": "ok"}

@app.get('/api/admin/menu')
async def admin_get_menu(admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.menu_database import menu_db
    try:
        items = await menu_db.get_all_items_detailed()
        if items:
            return items
    except Exception as e:
        await send_developer_error(f"Admin menu load failed:\n<code>{_safe_alert_text(e)}</code>")
    cached = public_data_cache.get('menu')
    flattened = _flatten_public_menu(cached)
    if flattened:
        return flattened
    flattened = _flatten_public_menu(_load_site_data_json('menu'))
    if flattened:
        return flattened
    raise HTTPException(status_code=503, detail="Дані тимчасово недоступні")

@app.post('/api/admin/menu')
async def admin_save_menu_item(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    item = await request.json()
    from app.databases.menu_database import menu_db

    converters = {
        'category': _clean_text,
        'name': _clean_text,
        'price': lambda v: _to_float(v, 0),
        'description': _clean_text,
        'volume': _clean_text,
        'calories': _clean_text,
        'image_url': _clean_text,
        'composition': _clean_text,
    }
    payload = {key: convert(item.get(key)) for key, convert in converters.items() if _has_field(item, key)}
    if not payload.get('category') or not payload.get('name'):
        raise HTTPException(status_code=400, detail="Category and name are required")

    item_id = item.get('id') or item.get('_id')
    if item_id:
        if not await menu_db.update_item(item_id, payload):
            raise HTTPException(status_code=404, detail="Menu item not found in database")
    else:
        await menu_db.add_item(
            category=payload.get('category', ''),
            name=payload.get('name', ''),
            price=payload.get('price', 0),
            description=payload.get('description', ''),
            volume=payload.get('volume', ''),
            calories=payload.get('calories', ''),
            image_url=payload.get('image_url', ''),
            composition=payload.get('composition', ''),
        )
    
    await public_data_cache.refresh_menu()
    return {"status": "ok"}

@app.delete('/api/admin/menu/{item_id}')
async def admin_delete_menu_item(item_id: str, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.menu_database import menu_db
    await menu_db.delete_item(item_id)
    await public_data_cache.refresh_menu()
    return {"status": "ok"}

@app.get('/api/admin/menu/categories')
async def admin_get_menu_categories(admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.menu_database import menu_db
    try:
        categories = await menu_db.get_categories()
        if categories:
            return categories
    except Exception as e:
        await send_developer_error(f"Admin menu categories load failed:\n<code>{_safe_alert_text(e)}</code>")
    cached = public_data_cache.get('menu') or _load_site_data_json('menu') or []
    return [section.get('category') for section in cached if isinstance(section, dict) and section.get('category')]

@app.post('/api/admin/menu/categories')
async def admin_save_menu_category(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    from app.databases.menu_database import menu_db
    old_name = (data.get('old_name') or '').strip()
    name = (data.get('name') or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail="Назва категорії обовʼязкова")
    if old_name and old_name != name:
        await menu_db.update_category(old_name, name)
    else:
        await menu_db.add_category(name)
    await public_data_cache.refresh_menu()
    return {"status": "ok"}

@app.delete('/api/admin/menu/categories/{name}')
async def admin_delete_menu_category(name: str, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.menu_database import menu_db
    await menu_db.delete_category(name)
    await public_data_cache.refresh_menu()
    return {"status": "ok"}

@app.get('/api/admin/beans')
async def admin_get_beans(admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.coffee_beans_database import coffee_beans_db
    return await coffee_beans_db.get_all_beans()

@app.post('/api/admin/beans')
async def admin_save_bean(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    bean = await request.json()
    from app.databases.coffee_beans_database import coffee_beans_db

    converters = {
        'name': _clean_text,
        'price_250': lambda v: _to_float(v, 0),
        'description': _clean_text,
        'sort': _clean_text,
        'taste': _clean_text,
        'roast': _clean_text,
        'image_url': _clean_text,
        'acidity': lambda v: _to_int(v, 0),
        'bitterness': lambda v: _to_int(v, 0),
        'body': lambda v: _to_int(v, 0),
    }
    payload = {key: convert(bean.get(key)) for key, convert in converters.items() if _has_field(bean, key)}
    if 'price_250' in payload:
        prices = coffee_beans_db.calculate_prices(payload['price_250'])
        payload['price_250'] = prices['250']
        payload['price_500'] = prices['500']
        payload['price_1000'] = prices['1000']
    if not payload.get('name'):
        raise HTTPException(status_code=400, detail="Name is required")

    bean_id = bean.get('_id')
    if bean_id:
        await coffee_beans_db.update_bean(bean_id, payload)
    else:
        await coffee_beans_db.add_bean(
            name=payload.get('name', ''),
            price_250=payload.get('price_250', 0),
            description=payload.get('description', ''),
            sort=payload.get('sort', ''),
            taste=payload.get('taste', ''),
            roast=payload.get('roast', ''),
            image_url=payload.get('image_url', ''),
            acidity=payload.get('acidity', 0),
            bitterness=payload.get('bitterness', 0),
            body=payload.get('body', 0),
        )
    
    await public_data_cache.refresh_coffee()
    return {"status": "ok"}

@app.delete('/api/admin/beans/{bean_id}')
async def admin_delete_bean(bean_id: str, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.coffee_beans_database import coffee_beans_db
    await coffee_beans_db.delete_bean(bean_id)
    await public_data_cache.refresh_coffee()
    return {"status": "ok"}

@app.get('/api/admin/locations')
async def admin_get_locations(admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('admin', 'super', 'boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    locations = await location_db.get_all_locations()
    if admin.get('role') == 'admin':
        allowed = await admin_db.get_locations_for_admin(admin.get('user_id'))
        if allowed:
            allowed_set = {str(x) for x in allowed}
            locations = [loc for loc in locations if str(loc.get('_id')) in allowed_set]
    return locations

@app.post('/api/admin/locations')
async def admin_save_location(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    loc_id = data.get('_id') or data.get('id')
    payload = {}
    for key in ('name', 'address', 'schedule', 'phone', 'google_maps_url', 'image_url', 'atmosphere'):
        if _has_field(data, key):
            payload[key] = _clean_text(data.get(key))
    if _has_field(data, 'amenities'):
        payload['amenities'] = data.get('amenities') if isinstance(data.get('amenities'), list) else [x.strip() for x in str(data.get('amenities', '')).split(',') if x.strip()]
    if not loc_id:
        payload.setdefault('max_tables', 10)
    if loc_id:
        await location_db.update_location(loc_id, payload)
    else:
        await location_db.add_location(
            name=payload.get('name', ''),
            address=payload.get('address', ''),
            schedule=payload.get('schedule', ''),
            phone=payload.get('phone', ''),
            email='',
            google_maps_url=payload.get('google_maps_url', ''),
            max_tables=payload.get('max_tables', 10),
            image_url=payload.get('image_url', ''),
            amenities=payload.get('amenities', []),
            atmosphere=payload.get('atmosphere', ''),
        )
    await public_data_cache.refresh_locations()
    return {"status": "ok"}

@app.delete('/api/admin/locations/{loc_id}')
async def admin_delete_location(loc_id: str, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    await location_db.delete_location(loc_id)
    await public_data_cache.refresh_locations()
    return {"status": "ok"}

@app.get('/api/admin/socials')
async def admin_get_socials(admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.socials_database import socials_db
    return await socials_db.get_all_socials()

@app.post('/api/admin/socials')
async def admin_save_social(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    from app.databases.socials_database import socials_db
    social_id = data.get('_id') or data.get('id')
    payload = {'name': data.get('name', ''), 'url': data.get('url', '')}
    if social_id:
        await socials_db.update_social(social_id, payload)
    else:
        await socials_db.add_social(payload['name'], payload['url'])
    await public_data_cache.refresh_socials()
    return {"status": "ok"}

@app.delete('/api/admin/socials/{social_id}')
async def admin_delete_social(social_id: str, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.socials_database import socials_db
    await socials_db.delete_social(social_id)
    await public_data_cache.refresh_socials()
    return {"status": "ok"}

def _can_manage_admin(caller_role: str, target_role: str) -> bool:
    levels = {'developer': 5, 'owner': 4, 'boss': 4, 'super': 3, 'admin': 2, 'delivery_manager': 2}
    caller_role = (caller_role or '').lower()
    target_role = (target_role or '').lower()
    if caller_role == 'developer':
        return True
    if target_role == 'developer':
        return False
    if caller_role in ('owner', 'boss'):
        return target_role != 'developer'
    if caller_role == 'super':
        return target_role in ('admin', 'delivery_manager')
    return levels.get(caller_role, 0) > levels.get(target_role, 0)

@app.get('/api/admin/team')
async def admin_get_team(admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('super', 'boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.mongo_client import get_db, projection_without_mongo_id
    db = await get_db()
    rows = await db.admins.find({}, projection_without_mongo_id()).sort('role', 1).to_list(length=None)
    return rows

@app.post('/api/admin/team')
async def admin_save_team_member(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    caller_role = admin.get('role') or 'admin'
    if caller_role not in ('super', 'boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    user_id = int(data.get('user_id') or 0)
    role = (data.get('role') or 'admin').strip()
    if not user_id or not _can_manage_admin(caller_role, role):
        raise HTTPException(status_code=403, detail="Недостатньо прав")
    receive_notifications = bool(data.get('receive_notifications', True))
    locations = [str(x) for x in (data.get('locations') or [])]
    from app.databases.mongo_client import get_db
    db = await get_db()
    old = await db.admins.find_one({'user_id': user_id}, {'_id': 0, 'role': 1})
    if old and not _can_manage_admin(caller_role, old.get('role') or 'admin'):
        raise HTTPException(status_code=403, detail="Недостатньо прав")
    await db.admins.update_one(
        {'user_id': user_id},
        {'$set': {
            'user_id': user_id,
            'username': (data.get('username') or '').replace('@', ''),
            'display_name': data.get('display_name') or data.get('username') or str(user_id),
            'role': role,
            'receive_notifications': receive_notifications,
            'locations': locations,
        }, '$setOnInsert': {'created_at': datetime.utcnow(), 'added_by': int(admin.get('user_id') or 0)}},
        upsert=True
    )
    return {"status": "ok"}

@app.delete('/api/admin/team/{user_id}')
async def admin_delete_team_member(user_id: int, admin: dict = fastapi.Depends(get_current_admin)):
    caller_role = admin.get('role') or 'admin'
    if caller_role not in ('super', 'boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.mongo_client import get_db
    db = await get_db()
    target = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'role': 1})
    if not target:
        raise HTTPException(status_code=404, detail="Адміністратора не знайдено")
    if not _can_manage_admin(caller_role, target.get('role') or 'admin'):
        raise HTTPException(status_code=403, detail="Недостатньо прав для видалення цього користувача")
    await db.admins.delete_one({'user_id': int(user_id)})
    return {"status": "ok"}

@app.get('/api/admin/support/chats')
async def admin_get_chats(admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('super', 'boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.guest_messages_database import guest_messages_db
    try:
        return await guest_messages_db.get_unique_chats()
    except Exception as e:
        await send_developer_error(f"Admin support chats load failed:\n<code>{_safe_alert_text(e)}</code>")
        raise HTTPException(status_code=503, detail="Чати тимчасово недоступні")

@app.get('/api/admin/support/messages')
async def admin_get_messages(request: Request, phone: str = None, order_id: str = None, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('super', 'boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.guest_messages_database import guest_messages_db
    try:
        return await guest_messages_db.get_messages(phone, order_id if order_id not in ('', 'none', 'null', 'undefined') else None)
    except Exception as e:
        await send_developer_error(f"Admin support messages load failed:\nphone={_safe_alert_text(phone, 120)}\norder_id={_safe_alert_text(order_id, 120)}\n<code>{_safe_alert_text(e)}</code>")
        raise HTTPException(status_code=503, detail="Повідомлення тимчасово недоступні")

@app.post('/api/admin/support/reply')
async def admin_reply_support(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('super', 'boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    phone = data.get('phone')
    order_id = data.get('order_id')
    text = data.get('text')
    
    from app.databases.guest_messages_database import guest_messages_db
    try:
        await guest_messages_db.add_message(order_id, phone, 'admin', text)
    except Exception as e:
        await send_developer_error(f"Admin support reply failed:\nphone={_safe_alert_text(phone, 120)}\norder_id={_safe_alert_text(order_id, 120)}\n<code>{_safe_alert_text(e)}</code>")
        raise HTTPException(status_code=503, detail="Відповідь тимчасово не відправилась")
    return {"status": "ok"}

@app.delete('/api/admin/support/messages')
async def admin_clear_support_chat(phone: str, order_id: str = None, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('super', 'boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.databases.mongo_client import get_db
    from app.utils.phone_utils import normalize_phone
    db = await get_db()
    query = {'phone_digits': normalize_phone(phone)}
    if order_id and order_id != 'none':
        query['order_id'] = order_id
    else:
        query['order_id'] = {'$in': [None, 'none', '']}
    await db.guest_messages.delete_many(query)
    return {"status": "ok"}

@app.get('/api/past-orders')
async def get_past_orders(phone: str):
    if not phone: return []
    orders = await orders_db.get_user_past_orders(phone)
    formatted = []
    for o in orders:
        formatted.append({
            'order_id': o.get('order_id'),
            'items_text': o.get('cart', ''),
            'total': o.get('total_amount', 0),
            'timestamp': o.get('created_at'),
            'type': o.get('order_type', 'menu')
        })
    return formatted

@app.get('/api/menu')
async def get_menu():
    return await public_data_cache.refresh_menu()

@app.get('/api/coffee')
async def get_coffee():
    return await public_data_cache.refresh_coffee()

@app.get('/api/locations')
async def get_locations():
    return await public_data_cache.refresh_locations()

@app.get('/api/socials')
async def get_socials():
    return await public_data_cache.refresh_socials()

if _site_dir:
    app.mount('/', StaticFiles(directory=str(_site_dir), html=True), name='site')
else:
    logger.warning("MedelinSite directory not found; skipping static site mount.")
