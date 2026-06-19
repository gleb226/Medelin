
from __future__ import annotations

from datetime import datetime, timedelta

from bson import ObjectId

from app.databases.mongo_client import get_db

class ActiveOrdersDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def add_order(self, order_id, fullname, location_id, order_type, cart):
        db = await get_db()
        await db.active_orders.update_one(
            {'order_id': str(order_id)},
            {'$set': {
                'fullname': fullname,
                'location_id': str(location_id),
                'cart': cart,
                'order_type': order_type,
                'created_at': datetime.utcnow()
            }},
            upsert=True
        )

    async def add_active_order(self, order_id, user_id, fullname, phone, location_id, cart, order_type, total=0, payment_mode='', wishes=''):
        db = await get_db()
        await db.active_orders.update_one(
            {'order_id': str(order_id)},
            {'$set': {
                'user_id': int(user_id) if user_id is not None else None,
                'fullname': fullname,
                'phone': phone,
                'location_id': str(location_id),
                'cart': cart,
                'order_type': order_type,
                'total': int(total or 0),
                'payment_mode': payment_mode or '',
                'wishes': wishes or '',
                'created_at': datetime.utcnow()
            }},
            upsert=True
        )

    async def get_active_orders(self, location_ids=None):

        db = await get_db()

        query = {}

        if location_ids:

            query['location_id'] = {'$in': [str(x) for x in location_ids]}

        cutoff = datetime.utcnow() - timedelta(minutes=20)

        await db.active_orders.delete_many({'created_at': {'$lt': cutoff}})

        cur = db.active_orders.find(query).sort('created_at', 1)

        return await cur.to_list(length=None)

    async def remove_order(self, active_id):

        db = await get_db()

        key = str(active_id)
        query = {'order_id': key}

        try:
            query = {'$or': [{'_id': ObjectId(key)}, {'order_id': key}]}
        except Exception:
            pass

        result = await db.active_orders.delete_many(query)
        return int(result.deleted_count or 0)

    async def delete_active_order(self, order_id):
        db = await get_db()
        await db.active_orders.delete_one({'order_id': str(order_id)})

    async def get_all_active_orders(self):
        db = await get_db()
        cur = db.active_orders.find({}).sort('created_at', 1)
        return await cur.to_list(length=None)

    async def get_active_order_by_mongo_id(self, mongo_id):
        db = await get_db()
        try:
            return await db.active_orders.find_one({'_id': ObjectId(str(mongo_id))})
        except:
            return None

    async def get_active_order_by_id(self, order_id):
        db = await get_db()
        return await db.active_orders.find_one({'order_id': str(order_id)})

active_orders_db = ActiveOrdersDatabase()
