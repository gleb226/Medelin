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
from fastapi import FastAPI, HTTPException, Request, Depends, Query, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time
import shutil
import uuid

from app.databases.orders_database import orders_db
from app.databases.admin_database import admin_db
from app.databases.location_database import location_db
from app.databases.contacts_database import contacts_db
from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.sales_database import sales_db
from app.databases.mongo_client import get_db, close_client
from app.utils.data_cache import public_data_cache
from app.utils.phone_utils import format_phone
from app.common.config import WEB_APP_URL, NP_API_KEY, DEVELOPER_IDS
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
from app.utils.paths import get_site_dir, get_uploads_dir
_site_dir = get_site_dir()

@app.get('/admin-panel', response_class=HTMLResponse)
async def get_admin_panel():
    path = _site_dir / 'admin-panel.html'
    logger.info(f"Serving admin-panel.html from: {path}")
    if path.exists():
        return FileResponse(path)
    logger.error(f"admin-panel.html NOT FOUND at: {path}")
    raise HTTPException(status_code=404)

@app.get('/api/admin/verify')
async def verify_admin_login(user_id: int):
    req = await admin_db.get_auth_request(user_id)
    if req and req.get('confirmed'):
        # Create session token
        token = base64.b64encode(os.urandom(32)).decode()
        # Save session to DB
        await admin_db.create_session(user_id, token)
        admin = await admin_db.get_admin_by_id(user_id)
        
        if not admin:
            if str(user_id) in DEVELOPER_IDS:
                admin = {'display_name': 'Developer', 'role': 'developer'}
            else:
                logger.error(f"Admin record not found for user_id: {user_id}")
                return {'status': 'error', 'message': 'Запис адміністратора не знайдено'}

        # Delete auth request
        await admin_db.delete_auth_request(user_id)
        return {'status': 'ok', 'token': token, 'admin': {'name': admin['display_name'], 'role': admin['role']}}
    return {'status': 'pending'}

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
    # Group items by name
    grouped = {}
    for item in cart:
        name = item.get('name', 'Невідомий товар')
        price = parse_price(item.get('price', 0))
        total += price
        if name in grouped:
            grouped[name]['qty'] += 1
            grouped[name]['price'] += price
        else:
            grouped[name] = {'qty': 1, 'price': price}
    
    lines = []
    for name, data in grouped.items():
        if data['qty'] > 1:
            lines.append(f"- {name} x{data['qty']} ({data['price']} грн)")
        else:
            lines.append(f"- {name} ({data['price']} грн)")
            
    return (total, '\n'.join(lines))

from app.utils.nova_poshta import np_client

# ... (around line 96)
@app.get('/api/nova-poshta/cities')
async def get_np_cities(search: str = Query('')):
    if len(search) < 2: return []
    return await np_client.search_settlements(search)

@app.get('/api/nova-poshta/warehouses')
async def get_np_warehouses(cityRef: str, search: str = Query('')):
    return await np_client.get_warehouses(cityRef, search)

@app.get('/api/nova-poshta/streets')
async def get_np_streets(cityRef: str = Query(None), city_ref: str = Query(None), search: str = Query('')):
    ref = cityRef or city_ref
    if not ref or len(search) < 2: return []
    res = await np_client.search_streets(ref, search)
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
    wishes_str = comment if comment else '—'
    
    delivery_info = ""
    type_label = ""
    
    if order_type == 'nova_poshta':
        np_city = (user.get('np_city_name') or '').strip()
        np_mode = user.get('np_delivery_mode')
        if np_mode == 'courier':
            type_label = "Кур'єр"
            np_st = user.get('np_street_name', '')
            np_h = user.get('np_house', '')
            np_f = user.get('np_flat', '')
            delivery_info = f"{np_city}, вул. {np_st}, буд. {np_h}, кв. {np_f}"
        else:
            type_label = "Відділення"
            np_warehouse = (user.get('np_warehouse') or '').strip()
            delivery_info = f"{np_city}, {np_warehouse}"
    else:
        type_map = { 'takeaway': 'З собою', 'in_house': 'В закладі' }
        type_label = type_map.get(order_type, order_type)
        if order_type == 'in_house' and user.get('table_number'):
            delivery_info = f"Стіл #{user.get('table_number')}"
        else:
            delivery_info = location['name'] if location else "Web"

    user_id = None
    try:
        from app.databases.user_database import user_db
        from app.utils.phone_utils import normalize_phone
        norm_phone = normalize_phone(phone)
        existing_order = await orders_db.get_user_by_phone(phone)
        if existing_order: user_id = existing_order.get('user_id')
        if not user_id and tg_nick:
            u_info = await user_db.get_user_by_username(tg_nick)
            if u_info: user_id = u_info[0]
        if not user_id and norm_phone:
            u_info = await user_db.get_user_by_phone(norm_phone)
            if u_info: user_id = u_info[0]
        if user_id: await user_db.add_user(user_id, user.get('name', '—'), tg_nick, phone)
    except Exception as e:
        logger.error(f"User sync failed: {e}")

    oid, is_new = await orders_db.add_order(user_id=user_id, username=tg_nick, fullname=user.get('name', '—'), phone=phone, location_id=loc_id, wishes=wishes_str, cart=items_text, order_type=order_type, payment_mode=payment_mode, total_amount=total, delivery_info=delivery_info)
    order = await orders_db.get_order_by_id(oid)
    order_num = order.get('order_number', 0)

    if not is_new:
        if payment_mode == 'pay_at_checkout' or data.get('payment_method') == 'cash':
            return {'status': 'ok', 'manual': True, 'order_id': oid, 'order_number': order_num, 'duplicate': True}

    if payment_mode == 'pay_at_checkout' or data.get('payment_method') == 'cash':
        pay_label = "Накладний платіж" if order_type == 'nova_poshta' else "ПІСЛЯПЛАТА"
        
        msg = f'🆕 <b>НОВЕ ЗАМОВЛЕННЯ #{order_num}</b>\n\n👤 {user.get("name")}\n📞 <code>{phone}</code>\n🚚 Куди: <b>{type_label} {delivery_info}</b>'
        msg += f'\n💰 <b>{total} грн</b>\n💳 Оплата: <b>{pay_label}</b>\n\n🛒 {items_text}'
        msg += f'\n\n📝 ПОБАЖАННЯ: <b>{wishes_str}</b>'
        
        await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, user_id or -1), location_id=loc_id, order_id=oid)
        return {'status': 'ok', 'manual': True, 'order_id': oid, 'order_number': order_num}

    # LiqPay Integration
    from app.common.config import LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY
    if LIQPAY_PUBLIC_KEY and LIQPAY_PRIVATE_KEY:
        paytype_map = { 'card': 'card', 'applepay': 'apay', 'googlepay': 'gpay', 'privatpay': 'privat24' }
        paytypes = paytype_map.get(data.get('payment_method'), 'card')
        
        liqpay_params = {
            "public_key": LIQPAY_PUBLIC_KEY, "version": "3", "action": "pay",
            "amount": str(total), "currency": "UAH", "description": f"Замовлення #{order_num} в Medelin",
            "order_id": str(oid), "result_url": f"{WEB_APP_URL}/index.html?payment=success",
            "server_url": f"{WEB_APP_URL}/api/liqpay-callback", "paytypes": paytypes
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
                
                type_map = { 'takeaway': 'З собою', 'in_house': 'В закладі', 'nova_poshta': 'Доставка', 'beans_delivery': 'Доставка', 'beans_booking': 'Самовивіз' }
                order_type = order.get('order_type')
                
                type_label = type_map.get(order_type, order_type)
                if order_type == 'nova_poshta' or order_type == 'beans_delivery':
                    # Determine if it's courier or branch from delivery_info
                    di = order.get('delivery_info', '')
                    if 'вул.' in di: type_label = "Кур'єр"
                    else: type_label = "Відділення"
                
                delivery_info = order.get('delivery_info') or ""
                if not delivery_info and order_type == 'in_house':
                    delivery_info = f"Стіл #{order.get('table_number')}"
                
                order_num = order.get('order_number', 0)

                msg = f'💰 <b>ОПЛАЧЕНО ЗАМОВЛЕННЯ #{order_num}</b>\n\n👤 {order.get("fullname")}\n📞 <code>{order.get("phone")}</code>\n🚚 Куди: <b>{type_label} {delivery_info}</b>'
                msg += f'\n💰 <b>{order.get("total_amount")} грн</b>\n💳 Оплата: <b>ОПЛАЧЕНО</b>\n\n🛒 {order.get("cart")}'
                msg += f'\n\n📝 ПОБАЖАННЯ: <b>{order.get("wishes") or "—"}</b>'
                
                await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, order.get('user_id') or -1), location_id=order.get('location_id'), order_id=oid)
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
        
        # Escape for safe HTML
        src = html.escape(str(data.get('source') or 'Site'))
        path = html.escape(str(data.get('path') or 'N/A'))
        msg_text = html.escape(str(data.get('message') or 'Client error'))
        ctx = html.escape(str(data.get('context') or ''))
        
        msg = f"🌐 <b>SITE CLIENT ERROR</b>\n\n<b>Source:</b> {src}\n<b>Path:</b> {path}\n\n<b>Message:</b>\n{msg_text}\n\n<b>Context:</b>\n{ctx}"
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

# --- Admin API Rate Limiting ---
login_attempts = {} # {identifier: {'count': 0, 'lockout_until': timestamp}}

@app.post('/api/admin/login')
async def admin_login(req: LoginRequest):
    now = time.time()
    ident = req.identifier.strip().lower()
    
    # Check lockout
    attempt_data = login_attempts.get(ident, {'count': 0, 'lockout_until': 0})
    if attempt_data['lockout_until'] > now:
        remaining = int(attempt_data['lockout_until'] - now)
        raise HTTPException(status_code=429, detail=f'Забагато спроб. Спробуйте через {remaining // 60 + 1} хв.')

    # If password is correct (for security, use ADMIN_PANEL_PASSWORD from config)
    from app.common.config import ADMIN_PANEL_PASSWORD
    if req.password != ADMIN_PANEL_PASSWORD:
        attempt_data['count'] += 1
        if attempt_data['count'] >= 5:
            attempt_data['lockout_until'] = now + 600 # 10 minutes
            login_attempts[ident] = attempt_data
            raise HTTPException(status_code=429, detail='Забагато спроб. Вхід заблоковано на 10 хв.')
        login_attempts[ident] = attempt_data
        raise HTTPException(status_code=401, detail=f'Невірний пароль. Залишилось спроб: {5 - attempt_data["count"]}')
    
    admin = await admin_db.find_admin_by_identifier(req.identifier)
    if not admin:
        raise HTTPException(status_code=404, detail='Адміністратора не знайдено. Впевніться, що ви зареєстровані в боті.')
    
    # Success: reset attempts
    login_attempts[ident] = {'count': 0, 'lockout_until': 0}
    
    # Send confirmation to bot
    from app.common.bot_instance import bot
    msg = f"🔐 <b>ЗАПИТ НА ВХІД В АДМІН-ПАНЕЛЬ</b>\n\n👤 <b>{admin['display_name']}</b> (@{admin.get('username', '—')})\n\nПідтвердіть вхід:"
    try:
        await bot.send_message(admin['user_id'], msg, reply_markup=akb.get_admin_auth_kb(admin['user_id']), parse_mode='HTML')
    except Exception as e:
        logger.error(f"Failed to send auth msg: {e}")
        raise HTTPException(status_code=500, detail='Не вдалося надіслати підтвердження в бот. Перевірте, чи бот не заблокований.')
    
    return {'status': 'ok', 'user_id': admin['user_id']}

@app.get('/api/admin/me')
async def get_admin_me(admin: dict = Depends(get_current_admin)):
    return {'name': admin['display_name'], 'role': admin['role'], 'user_id': admin['user_id'], 'locations': admin.get('locations', [])}

@app.get('/api/admin/new-orders')
async def get_new_orders(admin: dict = Depends(get_current_admin)):
    # Returns only orders with status 'new' or 'paid'
    locs = None
    if admin.get('role') not in ('owner', 'developer'):
        locs = list(admin.get('locations') or [])
        if not locs or 'web' not in locs: locs.append('web')
        if not locs or 'NP' not in locs: locs.append('NP')
    
    if locs:
        orders = await orders_db.get_new_orders_by_locations(locs)
    else:
        orders = await orders_db.get_new_orders()

    for o in orders:
        o['order_id'] = str(o['_id'])
        # Ensure order_number is strictly a number or fallback string for safety
        if 'order_number' not in o or not o['order_number']:
            o['order_number'] = '—'
        if 'created_at' in o and o['created_at']:
            o['created_at'] = o['created_at'].isoformat()
        del o['_id']
    return orders

@app.post('/api/admin/orders/{order_id}/confirm')
async def confirm_order(order_id: str, admin: dict = Depends(get_current_admin)):
    if admin.get('role') not in ('owner', 'developer'):
        raise HTTPException(status_code=403, detail='Недостатньо прав')
        
    order = await orders_db.get_order_by_id(order_id)
    if not order: return {'status': 'error', 'message': 'Order not found'}
    
    await orders_db.update_status(order_id, 'confirmed')
    
    # Bot Sync: Update messages for all admins
    from app.utils.admin_notifications import update_order_notifications
    await update_order_notifications(order_id, 'confirmed')
    
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
            total=order.get('total_amount', 0),
            payment_mode=order.get('payment_mode', ''),
            wishes=order.get('wishes', '')
        )
    return {'status': 'ok'}

@app.post('/api/admin/orders/{order_id}/reject')
async def reject_order(order_id: str, admin: dict = Depends(get_current_admin)):
    if admin.get('role') not in ('owner', 'developer'):
        raise HTTPException(status_code=403, detail='Недостатньо прав')
        
    await orders_db.update_status(order_id, 'rejected')
    
    # Bot Sync
    from app.utils.admin_notifications import update_order_notifications
    await update_order_notifications(order_id, 'rejected')
    
    return {'status': 'ok'}

@app.get('/api/admin/active-orders')
async def get_active_orders(admin: dict = Depends(get_current_admin)):
    from app.databases.active_orders_database import active_orders_db
    locs = None
    if admin.get('role') == 'admin':
        locs = list(admin.get('locations') or [])
        if not locs or 'web' not in locs: locs.append('web')
        if not locs or 'NP' not in locs: locs.append('NP')
    
    orders = await active_orders_db.get_active_orders(locs)
    for o in orders:
        o['order_id'] = str(o['_id'])
        if 'created_at' in o and o['created_at']:
            o['created_at'] = o['created_at'].isoformat()
        
        # Get order_number from orders_db if missing in active_orders
        if 'order_number' not in o or not o['order_number'] or o['order_number'] == '—':
            orig_order = await orders_db.get_order_by_id(o.get('order_id'))
            if orig_order:
                o['order_number'] = orig_order.get('order_number')
        
        if 'order_number' not in o or not o['order_number']:
            o['order_number'] = '—'

        del o['_id']
        # Add location name
        if o['location_id'] == 'NP': o['location_name'] = 'Нова Пошта'
        elif o['location_id'] == 'web': o['location_name'] = 'Сайт'
        else:
            loc = await location_db.get_location_by_id(o['location_id'])
            o['location_name'] = loc['name'] if loc else 'Web'
    return orders

@app.post('/api/admin/orders/{order_id}/complete')
async def complete_order(order_id: str, admin: dict = Depends(get_current_admin)):
    if admin.get('role') not in ('owner', 'developer'):
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    from app.databases.active_orders_database import active_orders_db

    # On the web panel, order_id passed is actually the MongoDB _id string
    order = await active_orders_db.get_active_order_by_mongo_id(order_id)
    if not order:
        # Fallback to order_id field just in case
        order = await active_orders_db.get_active_order_by_id(order_id)

    if order:
        await sales_db.add_sale(
            order_id=order.get('order_id', order_id),
            user_id=order.get('user_id'),
            fullname=order.get('fullname'),
            items=order.get('cart'),
            total=order.get('total', 0),
            location_id=order.get('location_id')
        )
        
        # Bot Sync: update message if mapping exists
        from app.utils.admin_notifications import update_order_notifications
        await update_order_notifications(order.get('order_id', order_id), 'completed')
    
    await active_orders_db.remove_order(order_id)
    return {'status': 'ok'}

# CRUD for Beans
@app.post('/api/admin/upload')
async def admin_upload_image(file: UploadFile = File(...), admin: dict = Depends(get_current_admin)):
    if admin.get('role') not in ('owner', 'developer'):
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    from app.utils.paths import get_uploads_dir
    import uuid
    import shutil
    
    ext = file.filename.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'webp', 'heic', 'heif']:
        raise HTTPException(status_code=400, detail="Непідтримуваний формат файлу")
        
    filename = f"{uuid.uuid4()}.{ext}"
    uploads_dir = get_uploads_dir()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = uploads_dir / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"status": "ok", "url": f"/uploads/{filename}"}

@app.get('/api/admin/beans')
async def admin_get_beans(admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    beans = await coffee_beans_db.get_all_beans()
    for b in beans: b['id'] = str(b['_id']); del b['_id']
    return beans

@app.post('/api/admin/beans')
async def admin_add_bean(data: dict, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    if 'price_250' in data: data['price_250'] = int(data['price_250'])
    if 'stock_packs' in data and data['stock_packs']: data['stock_packs'] = int(data['stock_packs'])
    await coffee_beans_db.add_bean(**data)
    return {'status': 'ok'}

@app.post('/api/admin/beans/{bean_id}')
async def admin_update_bean(bean_id: str, data: dict, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    if 'price_250' in data: data['price_250'] = int(data['price_250'])
    if 'stock_packs' in data and data['stock_packs']: data['stock_packs'] = int(data['stock_packs'])
    for f in ['acidity', 'body', 'sweetness']:
        if f in data and data[f]: data[f] = int(data[f])
    await coffee_beans_db.update_bean(bean_id, data)
    return {'status': 'ok'}

@app.delete('/api/admin/beans/{bean_id}')
async def admin_delete_bean(bean_id: str, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    await coffee_beans_db.delete_bean(bean_id)
    return {'status': 'ok'}

# CRUD for Locations
@app.get('/api/admin/locations')
async def admin_get_locations(admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    locs = await location_db.get_all_locations()
    for l in locs: l['id'] = str(l['_id']); del l['_id']
    return locs

@app.post('/api/admin/locations')
async def admin_add_location(data: dict, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    await location_db.add_location(**data)
    return {'status': 'ok'}

@app.post('/api/admin/locations/{loc_id}')
async def admin_update_location(loc_id: str, data: dict, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    await location_db.update_location(loc_id, data)
    return {'status': 'ok'}

@app.delete('/api/admin/locations/{loc_id}')
async def admin_delete_location(loc_id: str, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    await location_db.delete_location(loc_id)
    return {'status': 'ok'}

# CRUD for Contacts/Socials
@app.get('/api/admin/socials')
async def admin_get_socials(admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    socials = await contacts_db.get_all_contacts()
    for s in socials: s['id'] = str(s['_id']); del s['_id']
    return socials

@app.post('/api/admin/socials')
async def admin_add_social(data: dict, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    await contacts_db.add_contact(data['name'], data['url'])
    return {'status': 'ok'}

@app.post('/api/admin/socials/{sid}')
async def admin_update_social(sid: str, data: dict, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    await contacts_db.update_contact(sid, data)
    return {'status': 'ok'}

@app.delete('/api/admin/socials/{sid}')
async def admin_delete_social(sid: str, admin: dict = Depends(get_current_admin)):
    if admin.get('role') == 'admin':
        raise HTTPException(status_code=403, detail='Недостатньо прав')
    await contacts_db.delete_contact(sid)
    return {'status': 'ok'}

# CRUD for Team/Staff
@app.get('/api/admin/team')
async def admin_get_team(admin: dict = Depends(get_current_admin)):
    try:
        if admin.get('role') not in ('owner', 'developer'):
            raise HTTPException(status_code=403, detail='Недостатньо прав')
        
        # Get admins from DB
        admins_data = await admin_db.get_admins_with_locations()
        # result.append((str(r['user_id']), r.get('username'), r.get('display_name'), r.get('role') or 'admin', ...))
        
        # We need to enrich this with phone numbers from user_db
        from app.databases.user_database import user_db
        enriched = []
        for a in admins_data:
            uid = int(a[0])
            u_info = await user_db.get_user_by_id(uid)
            phone = u_info[3] if u_info else '—'
            enriched.append({
                'user_id': a[0],
                'username': a[1],
                'display_name': a[2],
                'role': a[3],
                'phone': phone
            })
        return enriched
    except Exception as e:
        logger.error(f"Error in get_team: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/admin/team')
async def admin_add_team(data: dict, admin: dict = Depends(get_current_admin)):
    try:
        logger.info(f"Adding team member. Data: {data}. Admin: {admin['user_id']}")
        if admin.get('role') not in ('owner', 'developer'):
            raise HTTPException(status_code=403, detail='Недостатньо прав')
        
        user_id_val = data.get('user_id', '').strip()
        username = data.get('username', '').strip().replace('@', '')
        
        # Try to find user via the same logic as the bot
        from app.databases.user_database import user_db
        target = None
        
        if user_id_val.isdigit():
            u_info = await user_db.get_user_by_id(int(user_id_val))
            if u_info:
                target = {'user_id': int(u_info[0]), 'display_name': u_info[1], 'username': u_info[2]}
        elif user_id_val.startswith('@') or username:
            un = username or user_id_val.replace('@', '')
            u_info = await user_db.get_user_by_username(un)
            if u_info:
                target = {'user_id': int(u_info[0]), 'display_name': u_info[1], 'username': u_info[2]}

        if not target:
            raise HTTPException(status_code=404, detail='Користувача не знайдено в базі бота. Він має натиснути /start.')

        user_id = int(target['user_id'])
        final_username = target.get('username') or username
        final_display_name = target.get('display_name') or data.get('display_name') or target.get('username') or str(user_id)
        
        me_role = admin.get('role')
        target_role = data.get('role', 'admin')
        
        if me_role == 'owner' and target_role == 'owner':
            raise HTTPException(status_code=403, detail='Власник не може створювати інших власників')

        # Location access is removed as per user request
        await admin_db.add_admin(user_id=user_id, username=final_username, display_name=final_display_name, added_by=admin['user_id'], role=target_role, locations=[])
        return {'status': 'ok'}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Error in add_team: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/admin/team/{uid}')
async def admin_delete_team(uid: str, admin: dict = Depends(get_current_admin)):
    try:
        logger.info(f"Deleting team member {uid}. Admin: {admin['user_id']}")
        if admin.get('role') not in ('owner', 'developer'):
            raise HTTPException(status_code=403, detail='Недостатньо прав')
            
        try:
            target_uid = int(uid)
        except:
            # Try to find by username if uid is not numeric
            target = await admin_db.find_admin_by_identifier(uid)
            if target: target_uid = int(target['user_id'])
            else: raise HTTPException(status_code=400, detail='Невірний ID користувача')

        await admin_db.remove_admin(target_uid)
        return {'status': 'ok'}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Error in delete_team: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Stats and Broadcast
@app.get('/api/admin/stats')
async def get_admin_stats(admin: dict = Depends(get_current_admin)):
    if admin.get('role') != 'developer':
        raise HTTPException(status_code=403, detail='Тільки Розробник має доступ до статистики')
    
    sales = await sales_db.get_all_sales()
    # Calculate revenue handling both total and price*quantity fields
    total_revenue = sum(
        s.get('total', 0) or (s.get('price', 0) * s.get('quantity', 1))
        for s in sales if s.get('record_type') == 'sale'
    )
    total_sales = len([s for s in sales if s.get('record_type') == 'sale'])
    avg_check = int(total_revenue / total_sales) if total_sales > 0 else 0
    
    return {
        'total_revenue': int(total_revenue),
        'total_sales': total_sales,
        'avg_check': avg_check,
        'recent_sales': sales[:20]
    }

@app.post('/api/admin/stats/reset')
async def reset_admin_stats(admin: dict = Depends(get_current_admin)):
    if admin.get('role') != 'developer':
        raise HTTPException(status_code=403, detail='Тільки Розробник може скидати статистику')
    
    db = await get_db()
    await db.sales.delete_many({})
    if 'bookings' in await db.list_collection_names():
        await db.bookings.delete_many({})
    
    return {'status': 'ok'}

if _site_dir:
    app.mount('/uploads', StaticFiles(directory=str(get_uploads_dir())), name='uploads')
    app.mount('/', StaticFiles(directory=str(_site_dir), html=True), name='site')
