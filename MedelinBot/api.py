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
from app.utils.admin_notifications import send_admin_notification
import app.keyboards.admin_keyboards as akb

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_db()
    asyncio.create_task(public_data_cache.warm_all())
    yield
    await close_client()

app = FastAPI(lifespan=lifespan)

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

@app.get('/api/coffee')
async def get_coffee(): return await public_data_cache.refresh_coffee()

@app.get('/api/locations')
async def get_locations(): return await public_data_cache.refresh_locations()

@app.get('/api/socials')
async def get_socials(): return await public_data_cache.refresh_socials()

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
        np_warehouse = (user.get('np_warehouse') or '').strip()
        wishes_str += f'\nНП: {np_city}, {np_warehouse}'
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
    return {'status': 'ok', 'order_id': oid, 'manual': False}

@app.get('/api/orders/{order_id}')
async def get_order(order_id: str):
    order = await orders_db.get_order_by_id(order_id)
    if not order: raise HTTPException(status_code=404, detail='Замовлення не знайдено')
    return {'order_id': str(order['_id']), 'total': order.get('total_amount', 0), 'status': order.get('status')}

@app.post('/api/client-error')
async def report_error(req: Request):
    try:
        data = await req.json()
        logger.error(f"CLIENT ERROR: {data}")
        msg = f"🛠 <b>DEVELOPER ALERT</b>\n\n🌐 <b>SITE CLIENT ERROR</b>\n\n<b>Source:</b> {data.get('source')}\n<b>Message:</b>\n{data.get('message')}"
        from app.common.config import DEVELOPER_IDS
        from app.common.bot_instance import bot
        for dev_id in DEVELOPER_IDS:
            try: await bot.send_message(dev_id, msg, parse_mode='HTML')
            except: pass
        return {'status': 'ok'}
    except: return {'status': 'error'}

if _site_dir:
    app.mount('/', StaticFiles(directory=str(_site_dir), html=True), name='site')
