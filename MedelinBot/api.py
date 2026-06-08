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
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time

from app.databases.orders_database import orders_db
from app.databases.admin_database import admin_db
from app.databases.location_database import location_db
from app.databases.contacts_database import contacts_db
from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.sales_database import sales_db
from app.databases.mongo_client import get_db, close_client
from app.utils.data_cache import public_data_cache
from app.utils.phone_utils import format_phone
from app.common.config import WEB_APP_URL, NP_API_KEY
from app.utils.admin_notifications import send_admin_notification, send_developer_error
import app.keyboards.admin_keyboards as akb

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_db()
        asyncio.create_task(public_data_cache.warm_all())
    except Exception as e:
        logger.error(f"Startup error: {e}")
    yield
    await close_client()

app = FastAPI(lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"🌐 <b>SERVER ERROR</b>\n\n<b>Path:</b> {request.url.path}\n<b>Error:</b> {str(exc)}"
    logger.error(f"Global Exception: {exc}", exc_info=True)
    await send_developer_error(error_msg)
    return JSONResponse(status_code=500, content={"detail": "Внутрішня помилка сервера"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Папка з сайтом
_curr_path = pathlib.Path(__file__).parent.resolve()
_site_dir = _curr_path.parent / 'MedelinSite'
if not _site_dir.exists():
    _site_dir = None

# --- Моделі ---
class CheckoutRequest(BaseModel):
    user_details: dict
    cart_menu: list
    payment_method: str = 'card'

class RepayRequest(BaseModel):
    order_id: str
    payment_method: str

async def resolve_location(value: str | None):
    target = (value or '').strip()
    if not target: return None
    all_locs = await location_db.get_all_locations()
    
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(all_locs): return all_locs[idx]

    for loc in all_locs:
        if target == str(loc.get('_id', '')): return loc
        if target.casefold() in [str(loc.get('name', '')).casefold(), str(loc.get('address', '')).casefold()]:
            return loc
    return None

def parse_price(value):
    digits = re.sub('[^\\d]', '', str(value))
    return int(digits) if digits else 0

def build_cart_text(cart: list) -> tuple[int, str]:
    total = 0
    items = []
    for item in cart:
        price = parse_price(item.get('price', 0))
        total += price
        items.append(f"- {item['name']} ({price} грн)")
    return (total, '\n'.join(items))

async def call_np(model: str, method: str, params: dict):
    url = "https://api.novaposhta.ua/v2.0/json/"
    payload = {
        "apiKey": NP_API_KEY,
        "modelName": model,
        "calledMethod": method,
        "methodProperties": params
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if not data.get('success'):
                    logger.error(f"NP API Error: {data.get('errors')}")
                    return []
                return data.get('data', [])
    except Exception as e:
        logger.error(f"NP API Exception: {e}")
        return []

@app.get('/api/nova-poshta/cities')
async def get_np_cities(search: str = Query('')):
    if len(search) < 2: return []
    # Try searchSettlements first
    res = await call_np("Address", "searchSettlements", {"CityName": search, "Limit": "20"})
    if isinstance(res, list) and len(res) > 0 and 'Addresses' in res[0]:
        return res[0]['Addresses']
    # Fallback to getCities
    res = await call_np("Address", "getCities", {"FindByString": search, "Limit": "20"})
    return res

@app.get('/api/nova-poshta/warehouses')
async def get_np_warehouses(cityRef: str, search: str = Query('')):
    # Try with provided ref (could be CityRef or SettlementRef)
    params = {"CityRef": cityRef, "Limit": "50"}
    if search: params["FindByString"] = search
    res = await call_np("Address", "getWarehouses", params)
    if not res:
        # Try as SettlementRef
        params = {"SettlementRef": cityRef, "Limit": "50"}
        if search: params["FindByString"] = search
        res = await call_np("Address", "getWarehouses", params)
    return res

@app.get('/api/nova-poshta/streets')
async def get_np_streets(cityRef: str = Query(None), city_ref: str = Query(None), search: str = Query('')):
    ref = cityRef or city_ref
    if not ref or len(search) < 2: return []
    res = await call_np("Address", "searchSettlementStreets", {"StreetName": search, "SettlementRef": ref, "Limit": "20"})
    if isinstance(res, list) and len(res) > 0 and 'Addresses' in res[0]:
        return res[0]['Addresses']
    return []

@app.get('/api/coffee')
async def get_coffee(): 
    data = public_data_cache.get('coffee')
    if data: return data
    return await public_data_cache.refresh_coffee()

@app.get('/api/locations')
async def get_locations(): 
    data = public_data_cache.get('locations')
    if data: return data
    return await public_data_cache.refresh_locations()

@app.get('/api/socials')
async def get_socials(): 
    data = public_data_cache.get('socials')
    if data: return data
    return await public_data_cache.refresh_socials()

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
    wishes_str = f'TG: @{tg_nick}' if tg_nick else ''
    if order_type == 'nova_poshta':
        np_city = (user.get('np_city_name') or '').strip()
        np_mode = user.get('np_delivery_mode')
        if np_mode == 'courier':
            np_st = user.get('np_street_name', '')
            np_h = user.get('np_house', '')
            np_f = user.get('np_flat', '')
            wishes_str += f'\nНП (Кур\'єр): {np_city}, вул. {np_st}, буд. {np_h}, кв. {np_f}'
        else:
            np_warehouse = (user.get('np_warehouse') or '').strip()
            wishes_str += f'\nНП (Відділення): {np_city}, {np_warehouse}'
    if comment: wishes_str += f'\nКоментар: {comment}'
    
    user_id = None
    try:
        from app.databases.user_database import user_db
        from app.utils.phone_utils import normalize_phone
        norm_phone = normalize_phone(phone)
        
        # 1. Search by phone in past orders
        existing_order = await orders_db.get_user_by_phone(phone)
        if existing_order: user_id = existing_order.get('user_id')
        
        # 2. Search by nickname in users table
        if not user_id and tg_nick:
            u_info = await user_db.get_user_by_username(tg_nick)
            if u_info: user_id = u_info[0]
            
        # 3. Search by phone in users table
        if not user_id and norm_phone:
            u_info = await user_db.get_user_by_phone(norm_phone)
            if u_info: user_id = u_info[0]

        # Sync user info if we found a Telegram ID
        if user_id:
            await user_db.add_user(user_id, user.get('name', '—'), tg_nick, phone)
    except Exception as e:
        logger.error(f"User sync failed: {e}")

    oid = await orders_db.add_order(user_id=user_id, username=tg_nick, fullname=user.get('name', '—'), phone=phone, location_id=loc_id, wishes=wishes_str.strip(), cart=items_text, order_type=order_type, payment_mode=payment_mode, table_number=user.get('table_number', ''), total_amount=total)
    
    if payment_mode == 'pay_at_checkout' or data.get('payment_method') == 'cash':
        from app.databases.active_orders_database import active_orders_db
        await active_orders_db.add_active_order(oid, user_id, user.get('name', '—'), phone, loc_id, items_text, order_type, user.get('table_number', ''), total, payment_mode, wishes_str)
        msg = f'🆕 <b>НОВЕ ЗАМОВЛЕННЯ</b>\n\n👤 {user.get("name")}\n📞 {phone}\n💰 {total} грн\n💳 Оплата: <b>ПІСЛЯПЛАТА</b>\n\n🛒 {items_text}'
        await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, user_id or -1), location_id=loc_id)
        return {'status': 'ok', 'manual': True, 'order_id': oid}

    # LiqPay Integration
    from app.common.config import LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY
    if LIQPAY_PUBLIC_KEY and LIQPAY_PRIVATE_KEY:
        paytype_map = {
            'card': 'card',
            'applepay': 'apay',
            'googlepay': 'gpay',
            'privatpay': 'privat24'
        }
        paytypes = paytype_map.get(data.get('payment_method'), 'card')
        
        liqpay_params = {
            "public_key": LIQPAY_PUBLIC_KEY,
            "version": "3",
            "action": "pay",
            "amount": str(total),
            "currency": "UAH",
            "description": f"Замовлення #{str(oid)[-6:]} в Medelin",
            "order_id": str(oid),
            "result_url": f"{WEB_APP_URL}/index.html?payment=success",
            "server_url": f"{WEB_APP_URL}/api/liqpay-callback",
            "paytypes": paytypes
        }
        json_params = json.dumps(liqpay_params).encode()
        data_b64 = base64.b64encode(json_params).decode()
        sig_str = LIQPAY_PRIVATE_KEY + data_b64 + LIQPAY_PRIVATE_KEY
        signature = base64.b64encode(hashlib.sha1(sig_str.encode()).digest()).decode()
        return {'status': 'ok', 'data': data_b64, 'signature': signature, 'order_id': oid}

    return {'status': 'ok', 'order_id': oid, 'manual': False}

@app.post('/api/liqpay-callback')
async def liqpay_callback(request: Request):
    try:
        fd = await request.form()
        data_b64 = fd.get('data')
        signature = fd.get('signature')
        if not data_b64 or not signature: return {'status': 'error'}
        
        from app.common.config import LIQPAY_PRIVATE_KEY
        sig_check = base64.b64encode(hashlib.sha1((LIQPAY_PRIVATE_KEY + data_b64 + LIQPAY_PRIVATE_KEY).encode()).digest()).decode()
        if sig_check != signature: return {'status': 'error'}
        
        data = json.loads(base64.b64decode(data_b64).decode())
        if data.get('status') in ('success', 'wait_accept'):
            oid = data.get('order_id')
            order = await orders_db.get_order_by_id(oid)
            if order and order.get('status') != 'paid':
                await orders_db.update_status(oid, 'paid')
                # Add to active orders
                from app.databases.active_orders_database import active_orders_db
                await active_orders_db.add_active_order(oid, order.get('user_id'), order.get('fullname'), order.get('phone'), order.get('location_id'), order.get('cart'), order.get('order_type'), order.get('table_number'), order.get('total_amount'), 'pay_now', order.get('wishes'))
                msg = f'💰 <b>ОПЛАЧЕНО ЗАМОВЛЕННЯ</b>\n\n👤 {order.get("fullname")}\n📞 {order.get("phone")}\n💰 {order.get("total_amount")} грн\n💳 Оплата: <b>LiqPay</b>\n\n🛒 {order.get("cart")}'
                await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, order.get('user_id') or -1), location_id=order.get('location_id'))
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f"LiqPay callback error: {e}")
        return {'status': 'error'}

@app.get('/api/orders/{order_id}')
async def get_order(order_id: str):
    order = await orders_db.get_order_by_id(order_id)
    if not order: raise HTTPException(status_code=404, detail='Замовлення не знайдено')
    return {'order_id': str(order['_id']), 'total': order.get('total_amount', 0), 'status': order.get('status')}

@app.get('/api/health')
async def health_check():
    try:
        db = await get_db()
        await db.command('ping')
        from app.common.bot_instance import bot
        bot_info = await bot.get_me()
        return {'status': 'ok', 'db': 'connected', 'bot': bot_info.username}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}

@app.post('/api/client-error')
async def report_error(req: Request):
    try:
        data = await req.json()
        logger.error(f"CLIENT ERROR: {data}")
        msg = f"🌐 <b>SITE CLIENT ERROR</b>\n\n<b>Source:</b> {data.get('source')}\n<b>Path:</b> {data.get('path')}\n\n<b>Message:</b>\n{data.get('message')}\n\n<b>Context:</b>\n{data.get('context')}"
        await send_developer_error(msg)
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f"Failed to report error: {e}")
        return {'status': 'error'}

# --- Admin API ---
class LoginRequest(BaseModel):
    identifier: str
    password: str

async def get_current_admin(request: Request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Неавторизовано')
    token = auth_header.split(' ')[1]
    admin = await admin_db.verify_session(token)
    if not admin:
        raise HTTPException(status_code=401, detail='Сесія недійсна')
    return admin

@app.post('/api/admin/login')
async def admin_login(req: LoginRequest):
    # If password is correct (for security, use ADMIN_PANEL_PASSWORD from config)
    from app.common.config import ADMIN_PANEL_PASSWORD
    if req.password != ADMIN_PANEL_PASSWORD:
        raise HTTPException(status_code=401, detail='Невірний пароль')
    
    admin = await admin_db.find_admin_by_identifier(req.identifier)
    if not admin:
        raise HTTPException(status_code=404, detail='Адміністратора не знайдено')
    
    # Send confirmation to bot
    from app.common.bot_instance import bot
    msg = f"🔐 <b>ЗАПИТ НА ВХІД В АДМІН-ПАНЕЛЬ</b>\n\n👤 <b>{admin['display_name']}</b> (@{admin.get('username', '—')})\n\nПідтвердіть вхід:"
    await bot.send_message(admin['user_id'], msg, reply_markup=akb.get_admin_auth_kb(admin['user_id']), parse_mode='HTML')
    
    return {'status': 'ok', 'user_id': admin['user_id']}

@app.get('/api/admin/verify')
async def admin_verify(user_id: int):
    req = await admin_db.get_auth_request(user_id)
    if req and req.get('confirmed'):
        # Create session
        token = hashlib.sha256(f"{user_id}{time.time()}".encode()).hexdigest()
        await admin_db.create_session(user_id, token)
        admin = await admin_db.get_admin_by_id(user_id)
        return {'status': 'ok', 'token': token, 'admin': admin}
    return {'status': 'pending'}

@app.get('/api/admin/new-orders')
async def get_new_orders(admin: dict = Depends(get_current_admin)):
    # Returns only orders with status 'new'
    orders = await orders_db.get_new_orders()
    for o in orders:
        o['order_id'] = str(o['_id'])
        del o['_id']
    return orders

@app.post('/api/admin/orders/{order_id}/confirm')
async def confirm_order(order_id: str, admin: dict = Depends(get_current_admin)):
    order = await orders_db.get_order_by_id(order_id)
    if not order: return {'status': 'error', 'message': 'Order not found'}
    
    await orders_db.update_status(order_id, 'confirmed')
    
    # Also add to active_orders_db if not already there
    from app.databases.active_orders_database import active_orders_db
    existing_active = await active_orders_db.get_active_order_by_id(order_id)
    if not existing_active:
        await active_orders_db.add_active_order(
            order_id=order_id,
            user_id=order.get('user_id'),
            fullname=order.get('fullname'),
            phone=order.get('phone'),
            location_id=order.get('location_id'),
            cart=order.get('cart'),
            order_type=order.get('order_type'),
            table_number=order.get('table_number', ''),
            total=order.get('total_amount', 0),
            payment_mode=order.get('payment_mode', ''),
            wishes=order.get('wishes', '')
        )
    return {'status': 'ok'}

@app.post('/api/admin/orders/{order_id}/reject')
async def reject_order(order_id: str, admin: dict = Depends(get_current_admin)):
    await orders_db.update_status(order_id, 'rejected')
    return {'status': 'ok'}

@app.get('/api/admin/active-orders')
async def get_active_orders(admin: dict = Depends(get_current_admin)):
    from app.databases.active_orders_database import active_orders_db
    locs = None
    if admin.get('role') not in ('boss', 'owner', 'developer'):
        locs = admin.get('locations')
    
    orders = await active_orders_db.get_active_orders(locs)
    for o in orders:
        o['order_id'] = str(o['_id'])
        del o['_id']
        # Add location name
        if o['location_id'] == 'NP': o['location_name'] = 'Нова Пошта'
        else:
            loc = await location_db.get_location_by_id(o['location_id'])
            o['location_name'] = loc['name'] if loc else 'Web'
    return orders

@app.post('/api/admin/orders/{order_id}/complete')
async def complete_order(order_id: str, admin: dict = Depends(get_current_admin)):
    from app.databases.active_orders_database import active_orders_db
    await active_orders_db.remove_order(order_id)
    return {'status': 'ok'}

# CRUD for Beans
@app.get('/api/admin/beans')
async def admin_get_beans(admin: dict = Depends(get_current_admin)):
    beans = await coffee_beans_db.get_all_beans()
    for b in beans: b['id'] = str(b['_id']); del b['_id']
    return beans

@app.post('/api/admin/beans')
async def admin_add_bean(data: dict, admin: dict = Depends(get_current_admin)):
    await coffee_beans_db.add_bean(**data)
    return {'status': 'ok'}

@app.post('/api/admin/beans/{bean_id}')
async def admin_update_bean(bean_id: str, data: dict, admin: dict = Depends(get_current_admin)):
    # Assuming update_bean exists or add it
    db = await get_db()
    from bson import ObjectId
    await db.coffee_beans.update_one({'_id': ObjectId(bean_id)}, {'$set': data})
    return {'status': 'ok'}

@app.delete('/api/admin/beans/{bean_id}')
async def admin_delete_bean(bean_id: str, admin: dict = Depends(get_current_admin)):
    await coffee_beans_db.delete_bean(bean_id)
    return {'status': 'ok'}

# CRUD for Locations
@app.get('/api/admin/locations')
async def admin_get_locations(admin: dict = Depends(get_current_admin)):
    locs = await location_db.get_all_locations()
    for l in locs: l['id'] = str(l['_id']); del l['_id']
    return locs

@app.post('/api/admin/locations')
async def admin_add_location(data: dict, admin: dict = Depends(get_current_admin)):
    await location_db.add_location(**data)
    return {'status': 'ok'}

@app.post('/api/admin/locations/{loc_id}')
async def admin_update_location(loc_id: str, data: dict, admin: dict = Depends(get_current_admin)):
    db = await get_db()
    from bson import ObjectId
    await db.locations.update_one({'_id': ObjectId(loc_id)}, {'$set': data})
    return {'status': 'ok'}

@app.delete('/api/admin/locations/{loc_id}')
async def admin_delete_location(loc_id: str, admin: dict = Depends(get_current_admin)):
    db = await get_db()
    from bson import ObjectId
    await db.locations.delete_one({'_id': ObjectId(loc_id)})
    return {'status': 'ok'}

# CRUD for Contacts/Socials
@app.get('/api/admin/socials')
async def admin_get_socials(admin: dict = Depends(get_current_admin)):
    socials = await contacts_db.get_all_contacts()
    for s in socials: s['id'] = str(s['_id']); del s['_id']
    return socials

@app.post('/api/admin/socials')
async def admin_add_social(data: dict, admin: dict = Depends(get_current_admin)):
    await contacts_db.add_contact(data['name'], data['url'])
    return {'status': 'ok'}

@app.delete('/api/admin/socials/{sid}')
async def admin_delete_social(sid: str, admin: dict = Depends(get_current_admin)):
    await contacts_db.remove_contact(sid)
    return {'status': 'ok'}

# CRUD for Team/Staff
@app.get('/api/admin/team')
async def admin_get_team(admin: dict = Depends(get_current_admin)):
    return await admin_db.get_admins_with_locations()

@app.post('/api/admin/team')
async def admin_add_team(data: dict, admin: dict = Depends(get_current_admin)):
    await admin_db.add_admin(user_id=data['user_id'], username=data.get('username', ''), display_name=data['display_name'], added_by=admin['user_id'], role=data.get('role', 'admin'), locations=data.get('locations', []))
    return {'status': 'ok'}

@app.delete('/api/admin/team/{uid}')
async def admin_delete_team(uid: int, admin: dict = Depends(get_current_admin)):
    await admin_db.remove_admin(uid)
    return {'status': 'ok'}

if _site_dir:
    app.mount('/', StaticFiles(directory=str(_site_dir), html=True), name='site')
