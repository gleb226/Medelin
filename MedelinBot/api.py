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
from app.databases.location_database import location_db
from app.databases.orders_database import orders_db
from app.databases.admin_database import admin_db
from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.contacts_database import contacts_db
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
        raise HTTPException(status_code=500, detail="Не вдалося надіслати повідомлення in Telegram. Переконайтеся, що ви почали діалог з ботом.")
        
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

_uploads_dir = pathlib.Path("/usr/share/nginx/html/assets/images/uploads")
if not _uploads_dir.exists():
    if _site_dir:
        _uploads_dir = _site_dir / "assets" / "images" / "uploads"
    else:
        _uploads_dir = pathlib.Path("/app/MedelinSite/assets/images/uploads")

if not _uploads_dir.exists():
    _uploads_dir = pathlib.Path("/app/uploads")

_uploads_dir.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")
app.mount("/cache", StaticFiles(directory=str(public_data_cache._dir)), name="cache")

class CheckoutRequest(BaseModel):
    user_details: dict
    cart_menu: list
    payment_method: str = 'card'

class RepayRequest(BaseModel):
    order_id: str
    payment_method: str

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

@app.get('/api/nova-poshta/cities')
async def get_np_cities(search: str):
    if not NP_API_KEY:
        return []
    payload = {'apiKey': NP_API_KEY, 'modelName': 'Address', 'calledMethod': 'searchSettlements', 'methodProperties': {'CityName': search, 'Limit': '50'}}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post('https://api.novaposhta.ua/v2.0/json/', json=payload) as resp:
                if resp.status != 200: return []
                data = await resp.json()
                if not data.get('success'): return []
                res_data = data.get('data', [])
                if res_data and isinstance(res_data, list) and len(res_data) > 0:
                    return res_data[0].get('Addresses', [])
                return []
        except: return []

@app.get('/api/nova-poshta/warehouses')
async def get_np_warehouses(cityRef: str, cityName: str = None, search: str = None):
    if not NP_API_KEY: return []
    async def fetch_wh(props):
        payload = {'apiKey': NP_API_KEY, 'modelName': 'Address', 'calledMethod': 'getWarehouses', 'methodProperties': props}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post('https://api.novaposhta.ua/v2.0/json/', json=payload) as resp:
                    data = await resp.json()
                    if not data.get('success'): return []
                    return data.get('data', [])
            except: return []
    props = {'SettlementRef': cityRef}
    if search: props['FindByString'] = search
    data = await fetch_wh(props)
    if not data:
        props_city = {'CityRef': cityRef}
        if search: props_city['FindByString'] = search
        data = await fetch_wh(props_city)
    return data

@app.post('/api/checkout')
async def process_checkout(req: CheckoutRequest):
    data = req.dict()
    total, items_text = build_cart_text(data.get('cart_menu', []))
    if total <= 0: raise HTTPException(status_code=400, detail='Кошик порожній')
    user = data.get('user_details', {})
    location = await resolve_location(user.get('location'))
    loc_id = str(location['_id']) if location else 'web'
    phone = format_phone(user.get('phone', '')) or user.get('phone', '—')
    tg_nick = (user.get('tg_nick') or user.get('tg') or '').strip().replace('@', '')
    payment_mode = user.get('payment_mode') or 'pay_now'
    order_type = user.get('delivery_type') or ('takeaway' if user.get('type') == 'takeaway' else 'in_house')
    if order_type == 'nova_poshta': loc_id = 'NP'
    comment = user.get('comment', '').strip()
    wishes_str = f'TG: {tg_nick}'
    if order_type == 'nova_poshta':
        np_city = (user.get('np_city_name') or '').strip(); np_warehouse = (user.get('np_warehouse') or '').strip()
        if np_city or np_warehouse: wishes_str += f'\nНП: {np_city}, {np_warehouse}'.strip()
    if comment: wishes_str += f'\nКоментар: {comment}'
    
    # Спроба знайти user_id і додати користувача
    user_id = None
    try:
        from app.databases.user_database import user_db
        existing_order = await orders_db.get_user_by_phone(phone)
        if existing_order:
            user_id = existing_order.get('user_id')
        
        if not user_id and tg_nick:
            u_info = await user_db.get_user_by_username(tg_nick)
            if u_info:
                user_id = u_info[0]
        
        if user_id:
            await user_db.add_user(user_id, user.get('name', '—'), tg_nick, phone)
    except Exception as e:
        logger.error(f"Failed to update user in checkout: {e}")

    oid = await orders_db.add_order(user_id=user_id, username=tg_nick, fullname=user.get('name', '—'), phone=phone, location_id=loc_id, date_time=None, people_count=None, wishes=wishes_str, cart=items_text, order_type=order_type, payment_mode=payment_mode, table_number=user.get('table_number', ''), total_amount=total)
    if payment_mode == 'pay_at_checkout' or data.get('payment_method') == 'cash':
        from app.databases.active_orders_database import active_orders_db
        await active_orders_db.add_active_order(oid, user_id, user.get('name', '—'), phone, loc_id, items_text, order_type, user.get('table_number', ''), total, payment_mode, wishes_str)
        msg = f'🆕 <b>НОВЕ ЗАМОВЛЕННЯ</b>\n\n👤 {user.get("name")}\n📞 {phone}\n💰 {total} грн\n💳 Оплата: <b>ПІСЛЯПЛАТА</b>\n\n🛒 {items_text}'
        await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, user_id or -1), location_id=loc_id)
        return {'status': 'ok', 'manual': True, 'order_id': oid}
    return {'status': 'ok', 'order_id': oid, 'manual': False}
    return {'status': 'ok', 'order_id': oid, 'manual': False}

@app.get('/api/admin/beans')
async def admin_get_beans(admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    return await coffee_beans_db.get_all_beans()

@app.post('/api/admin/coffee-beans')
async def admin_save_bean(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    bean_id = data.get('_id') or data.get('id')
    payload = {}
    fields = ('name', 'country', 'station', 'processing', 'descriptors', 'species', 'variety', 'region', 'altitude', 'roast', 'image_url')
    for key in fields:
        if _has_field(data, key): payload[key] = _clean_text(data.get(key))
    if _has_field(data, 'price_250'):
        try: payload['price_250'] = float(str(data.get('price_250')).replace(',', '.'))
        except: pass
    if bean_id: await coffee_beans_db.update_bean(bean_id, payload)
    else: await coffee_beans_db.add_bean(**payload)
    await public_data_cache.refresh_coffee()
    return {"status": "ok"}

@app.delete('/api/admin/beans/{bean_id}')
async def admin_delete_bean(bean_id: str, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    await coffee_beans_db.delete_bean(bean_id)
    await public_data_cache.refresh_coffee()
    return {"status": "ok"}

@app.get('/api/admin/locations')
async def admin_get_locations(admin: dict = fastapi.Depends(get_current_admin)):
    return await location_db.get_all_locations()

@app.post('/api/admin/locations')
async def admin_save_location(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    loc_id = data.get('_id') or data.get('id')
    payload = {k: _clean_text(data.get(k)) for k in ('name', 'address', 'schedule', 'phone', 'google_maps_url', 'image_url', 'atmosphere') if _has_field(data, k)}
    if loc_id: await location_db.update_location(loc_id, payload)
    else: await location_db.add_location(name=payload.get('name',''), address=payload.get('address',''), schedule=payload.get('schedule',''), phone=payload.get('phone',''), email='', google_maps_url=payload.get('google_maps_url',''), max_tables=10, image_url=payload.get('image_url',''), amenities=[], atmosphere=payload.get('atmosphere',''))
    await public_data_cache.refresh_locations()
    return {"status": "ok"}

@app.get('/api/admin/socials')
async def admin_get_socials(admin: dict = fastapi.Depends(get_current_admin)):
    return await contacts_db.get_all_contacts()

@app.post('/api/admin/socials')
async def admin_save_social(request: Request, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'): raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json(); social_id = data.get('_id') or data.get('id')
    payload = {'name': data.get('name', ''), 'url': data.get('url', '')}
    if social_id: await contacts_db.update_contact(social_id, payload)
    else: await contacts_db.add_contact(payload['name'], payload['url'])
    await public_data_cache.refresh_socials()
    return {"status": "ok"}

@app.delete('/api/admin/socials/{social_id}')
async def admin_delete_social(social_id: str, admin: dict = fastapi.Depends(get_current_admin)):
    if admin.get('role') not in ('boss', 'owner', 'developer'): raise HTTPException(status_code=403, detail="Forbidden")
    await contacts_db.delete_contact(social_id)
    await public_data_cache.refresh_socials()
    return {"status": "ok"}

@app.get('/api/admin/active-orders')
async def get_admin_active_orders(admin: dict = fastapi.Depends(get_current_admin)):
    from app.databases.active_orders_database import active_orders_db
    locs = await _admin_visible_location_ids(admin)
    orders = await active_orders_db.get_active_orders(locs)
    return [await _decorate_active_order(o) for o in orders]

async def _admin_visible_location_ids(admin: dict):
    role = admin.get('role') or 'admin'
    if role in ('super', 'boss', 'owner', 'developer'): return None
    if role == 'delivery_manager': return ['NP']
    user_id = admin.get('user_id')
    shift_loc = await admin_db.is_on_shift(user_id) if user_id else False
    if isinstance(shift_loc, str) and shift_loc not in ("True", "1", "False", "0"): return [shift_loc]
    return []

async def _decorate_active_order(order: dict):
    loc_id = str(order.get('location_id') or '')
    location_name = 'Сайт'
    if loc_id == 'NP': location_name = 'Нова Пошта'
    elif loc_id and loc_id not in ('web', 'unknown'):
        loc = await location_db.get_location_by_id(loc_id)
        if loc: location_name = loc.get('name') or location_name
    order['location_name'] = location_name
    return order

@app.get('/api/coffee')
async def get_coffee(): return await public_data_cache.refresh_coffee()

@app.get('/api/locations')
async def get_locations(): return await public_data_cache.refresh_locations()

@app.get('/api/socials')
async def get_socials(): return await public_data_cache.refresh_socials()

if _site_dir:
    app.mount('/', StaticFiles(directory=str(_site_dir), html=True), name='site')
