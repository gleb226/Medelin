
from datetime import datetime

from app.databases.mongo_client import get_db, projection_without_mongo_id

class SalesDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def record_sale(self, user_id, item_name, price, quantity, item_type):

        db = await get_db()

        await db.sales.insert_one({'record_type': 'sale', 'user_id': int(user_id), 'item_name': item_name, 'price': int(price), 'quantity': int(quantity), 'item_type': item_type, 'timestamp': datetime.utcnow()})

    async def record_payment(self, user_id: int, amount: int, currency: str, payload: str, telegram_id: str, provider_id: str):

        db = await get_db()

        await db.sales.insert_one({'record_type': 'payment', 'user_id': int(user_id), 'amount': int(amount), 'currency': currency, 'payload': payload, 'telegram_id': telegram_id, 'provider_id': provider_id, 'timestamp': datetime.utcnow()})

    async def get_user_sales(self, user_id: int):

        db = await get_db()

        cur = db.sales.find({'record_type': 'sale', 'user_id': int(user_id)}, projection_without_mongo_id()).sort('timestamp', -1)

        return await cur.to_list(length=None)

    async def get_all_sales(self):

        db = await get_db()

        cur = db.sales.find({'record_type': 'sale'}, projection_without_mongo_id()).sort('timestamp', -1)

        return await cur.to_list(length=None)

    async def get_all_payments(self):

        db = await get_db()

        cur = db.sales.find({'record_type': 'payment'}, projection_without_mongo_id()).sort('timestamp', -1)

        return await cur.to_list(length=None)

    async def add_sale(self, order_id, user_id, fullname, items, total, location_id):
        db = await get_db()
        await db.sales.update_one(
            {'record_type': 'sale', 'order_id': str(order_id)},
            {'$setOnInsert': {
                'record_type': 'sale',
                'order_id': str(order_id),
                'user_id': int(user_id) if user_id is not None else None,
                'fullname': fullname,
                'items': items,
                'total': int(total),
                'location_id': str(location_id),
                'timestamp': datetime.utcnow()
            }},
            upsert=True
        )

sales_db = SalesDatabase()
