
from __future__ import annotations

from datetime import datetime

from app.databases.mongo_client import get_db

from app.utils.phone_utils import normalize_phone

class GuestMessagesDatabase:

    async def add_message(self, order_id: str | None, phone: str | None, source: str, text: str) -> str:

        db = await get_db()

        doc = {'order_id': str(order_id) if order_id else None, 'phone_digits': normalize_phone(phone), 'source': source, 'text': text, 'created_at': datetime.utcnow(), 'read': False}

        res = await db.guest_messages.insert_one(doc)

        return str(res.inserted_id)

    async def get_messages(self, phone: str | None, order_id: str | None=None):

        db = await get_db()

        query = {}

        phone_digits = normalize_phone(phone)

        if order_id:

            query['order_id'] = str(order_id)

        if phone_digits:

            query['phone_digits'] = phone_digits

        if not query:

            return []

        cur = db.guest_messages.find(query).sort('created_at', 1)

        return await cur.to_list(length=None)

    async def mark_messages_read(self, phone: str | None, order_id: str | None=None) -> int:

        db = await get_db()

        query = {'read': False}

        phone_digits = normalize_phone(phone)

        if order_id:

            query['order_id'] = str(order_id)

        if phone_digits:

            query['phone_digits'] = phone_digits

        if len(query) == 1:

            return 0

        res = await db.guest_messages.update_many(query, {'$set': {'read': True}})

        return int(res.modified_count or 0)

    async def get_unique_chats(self, limit: int = 20):
        db = await get_db()
        pipeline = [
            {"$sort": {"created_at": -1}},
            {"$group": {
                "_id": {"phone": "$phone_digits", "order_id": "$order_id"},
                "last_text": {"$first": "$text"},
                "last_time": {"$first": "$created_at"},
                "unread_count": {"$sum": {"$cond": [{"$and": [{"$eq": ["$read", False]}, {"$eq": ["$source", "guest"]}]}, 1, 0]}}
            }},
            {"$sort": {"last_time": -1}},
            {"$limit": limit}
        ]
        cur = db.guest_messages.aggregate(pipeline)
        return await cur.to_list(length=limit)

    async def has_guest_chat_started(self, phone: str | None, order_id: str | None=None) -> bool:
        db = await get_db()

        phone_digits = normalize_phone(phone)
        if not phone_digits:
            return False

        query: dict = {'phone_digits': phone_digits, 'source': 'guest'}
        if order_id is not None:
            query['order_id'] = str(order_id) if order_id else None

        doc = await db.guest_messages.find_one(query, {'_id': 1})
        return bool(doc)

guest_messages_db = GuestMessagesDatabase()
