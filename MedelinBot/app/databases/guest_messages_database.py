
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

guest_messages_db = GuestMessagesDatabase()
