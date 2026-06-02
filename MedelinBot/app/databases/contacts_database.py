
from bson import ObjectId

from app.databases.mongo_client import get_db

class ContactsDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def clear_contacts(self):

        db = await get_db()

        await db.contacts.delete_many({})

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_socials()

    async def add_contact(self, name, url):

        db = await get_db()

        await db.contacts.update_one({'name': name}, {'$set': {'url': url}}, upsert=True)

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_socials()

    async def get_all_contacts(self):

        db = await get_db()

        cursor = db.contacts.find({})

        contacts = await cursor.to_list(length=None)

        for s in contacts:

            if '_id' in s:

                s['_id'] = str(s['_id'])

        return contacts

    async def get_contact_by_id(self, contact_id):

        db = await get_db()

        try:

            return await db.contacts.find_one({'_id': ObjectId(contact_id)})

        except:

            return None

    async def update_contact(self, contact_id: str, update: dict) -> bool:

        db = await get_db()

        try:

            oid = ObjectId(contact_id)

        except Exception:

            return False

        allowed_fields = {'name', 'url'}

        update = {k: v for k, v in (update or {}).items() if k in allowed_fields}

        if not update:

            return False

        res = await db.contacts.update_one({'_id': oid}, {'$set': update})

        success = bool(res.matched_count)

        if success:

            from app.utils.data_cache import public_data_cache

            await public_data_cache.refresh_socials()

        return success

    async def delete_contact(self, contact_id):

        db = await get_db()

        try:

            res = await db.contacts.delete_one({'_id': ObjectId(contact_id)})

            success = bool(res.deleted_count)

            if success:

                from app.utils.data_cache import public_data_cache

                await public_data_cache.refresh_socials()

            return success

        except:

            return False

contacts_db = ContactsDatabase()
