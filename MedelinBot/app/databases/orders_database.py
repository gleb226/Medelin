
from __future__ import annotations

from datetime import datetime, timedelta

from typing import Any

from bson import ObjectId

from app.databases.mongo_client import get_db

from app.utils.phone_utils import normalize_phone

class OrdersDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def get_next_order_number(self) -> int:
        db = await get_db()
        ret = await db.counters.find_one_and_update(
            {'_id': 'order_number'},
            {'$inc': {'seq': 1}},
            upsert=True,
            return_document=True
        )
        seq = ret.get('seq', 1)
        if seq > 1000:
            await db.counters.update_one({'_id': 'order_number'}, {'$set': {'seq': 1}})
            return 1
        return seq

    async def add_order(self, user_id, username, fullname, phone, location_id, wishes, cart, date_time=None, people_count=None, order_type='order', payment_mode='cashier', table_number='', total_amount=0, delivery_info=''):
        db = await get_db()
        digits = normalize_phone(phone)
        oid = ObjectId()
        order_num = await self.get_next_order_number()
        doc = {
            '_id': oid, 
            'order_id': str(oid), 
            'order_number': order_num,
            'user_id': int(user_id) if user_id is not None else None, 
            'username': username, 
            'fullname': fullname, 
            'phone': phone, 
            'phone_digits': digits, 
            'location_id': str(location_id), 
            'delivery_info': delivery_info,
            'date_time': date_time, 
            'people_count': people_count, 
            'wishes': wishes, 
            'cart': cart, 
            'total_amount': total_amount, 
            'status': 'new', 
            'order_type': order_type, 
            'payment_mode': payment_mode, 
            'table_number': table_number or '', 
            'payment_id': None, 
            'provider_payment_id': None, 
            'notified_admin_ids': [], 
            'refund_status': None, 
            'created_at': datetime.utcnow()
        }
        await db.orders.insert_one(doc)
        return str(oid)

    async def get_new_orders(self):

        db = await get_db()

        cur = db.orders.find({'status': {'$in': ['new', 'paid']}}).sort('created_at', -1)

        return await cur.to_list(length=None)

    async def get_new_orders_by_locations(self, location_ids):

        if not location_ids:

            return []

        db = await get_db()

        cur = db.orders.find({'status': {'$in': ['new', 'paid']}, 'location_id': {'$in': [str(x) for x in location_ids]}}).sort('created_at', -1)

        return await cur.to_list(length=None)

    async def update_status(self, order_id, status):

        db = await get_db()

        oid = ObjectId(str(order_id))

        await db.orders.update_one({'_id': oid}, {'$set': {'status': status}})

    async def get_order_by_id(self, order_id):

        try:

            oid = ObjectId(str(order_id))

        except:

            return None

        db = await get_db()

        return await db.orders.find_one({'_id': oid})

    async def set_payment_id(self, order_id: str, payment_id: str, provider_payment_id: str | None=None):

        db = await get_db()

        oid = ObjectId(str(order_id))

        await db.orders.update_one({'_id': oid}, {'$set': {'payment_id': payment_id, 'provider_payment_id': provider_payment_id}})

    async def set_refund_status(self, order_id: str, status: str):

        db = await get_db()

        oid = ObjectId(str(order_id))

        await db.orders.update_one({'_id': oid}, {'$set': {'refund_status': str(status)}})

    async def mark_admin_notified(self, order_id: str, admin_id: int):

        db = await get_db()

        oid = ObjectId(str(order_id))

        await db.orders.update_one({'_id': oid}, {'$addToSet': {'notified_admin_ids': int(admin_id)}})

    async def get_unnotified_new_orders_for_admin(self, admin_id: int, location_ids: list):

        if not location_ids:

            return []

        db = await get_db()

        cur = db.orders.find({'status': {'$in': ['new', 'paid']}, 'location_id': {'$in': [str(x) for x in location_ids]}, 'notified_admin_ids': {'$ne': int(admin_id)}}).sort('created_at', -1)

        return await cur.to_list(length=None)

    async def get_user_past_orders(self, phone: str, limit: int = 20):
        t = normalize_phone(phone)
        if not t:
            return []
        db = await get_db()
        cursor = db.orders.find({'phone_digits': t}).sort('created_at', -1).limit(limit)
        orders = await cursor.to_list(length=limit)
        for o in orders:
            if '_id' in o:
                o['_id'] = str(o['_id'])
            if 'created_at' in o:
                o['created_at'] = o['created_at'].isoformat()
        return orders

    async def get_user_by_phone(self, phone: str) -> Any:

        t = normalize_phone(phone)

        if not t:

            return None

        db = await get_db()

        return await db.orders.find_one({'phone_digits': t}, {'_id': 0, 'user_id': 1, 'fullname': 1, 'username': 1, 'phone': 1}, sort=[('created_at', -1)])

    async def cleanup_old_orders(self, months: int=6) -> int:

        db = await get_db()

        cutoff = datetime.utcnow() - timedelta(days=int(months) * 30)

        res = await db.orders.delete_many({'created_at': {'$lt': cutoff}})

        return int(res.deleted_count or 0)

    async def clear_all_orders(self) -> int:

        db = await get_db()

        res = await db.orders.delete_many({})

        return int(res.deleted_count or 0)

orders_db = OrdersDatabase()
