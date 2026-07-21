
from datetime import datetime

from app.databases.mongo_client import get_db, projection_without_mongo_id

from app.utils.phone_utils import format_phone, normalize_phone

class UserDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def add_user(self, user_id: int, first_name: str, username: str, phone: str=None):

        db = await get_db()

        pv = format_phone(phone) if phone else None

        digits = normalize_phone(pv) if pv else None

        set_doc = {'first_name': first_name, 'username': username, 'username_lc': (username or '').lower()}

        if pv:

            set_doc.update({'phone': pv, 'phone_digits': digits})

        await db.users.update_one({'user_id': int(user_id)}, {'$set': set_doc, '$setOnInsert': {'joined_at': datetime.utcnow()}}, upsert=True)

    async def set_phone(self, user_id: int, phone: str):

        db = await get_db()

        pv = format_phone(phone)

        await db.users.update_one({'user_id': int(user_id)}, {'$set': {'phone': pv, 'phone_digits': normalize_phone(pv)}}, upsert=True)

    async def get_phone(self, user_id: int):

        db = await get_db()

        r = await db.users.find_one({'user_id': int(user_id)}, {'_id': 0, 'phone': 1})

        return r.get('phone') if r else None

    async def get_user_by_username(self, username: str):

        if not username:

            return None

        db = await get_db()

        r = await db.users.find_one({'username_lc': username.lower()}, projection_without_mongo_id())

        if not r:

            return None

        return (r['user_id'], r.get('first_name'), r.get('username'), r.get('phone'))

    async def get_user_by_id(self, user_id: int):

        db = await get_db()

        r = await db.users.find_one({'user_id': int(user_id)}, projection_without_mongo_id())

        if not r:

            return None

        return (r['user_id'], r.get('first_name'), r.get('username'), r.get('phone'))

    async def get_user_by_phone(self, phone: str):

        t = normalize_phone(phone)

        if not t:

            return None

        db = await get_db()

        r = await db.users.find_one({'phone_digits': t}, projection_without_mongo_id())

        if not r:

            return None

        return (r['user_id'], r.get('first_name'), r.get('username'), r.get('phone'))

    async def get_all_user_ids(self):
        db = await get_db()
        cursor = db.users.find({}, {'user_id': 1, '_id': 0})
        users = await cursor.to_list(length=None)
        return [u['user_id'] for u in users if 'user_id' in u]

user_db = UserDatabase()
