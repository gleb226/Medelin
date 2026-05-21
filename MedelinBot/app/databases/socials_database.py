
from bson import ObjectId

from app.databases.mongo_client import get_db

class SocialsDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def clear_socials(self):

        db = await get_db()

        await db.socials.delete_many({})

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_socials()

    async def add_social(self, name, url):

        db = await get_db()

        await db.socials.update_one({'name': name}, {'$set': {'url': url}}, upsert=True)

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_socials()

    async def get_all_socials(self):

        db = await get_db()

        cursor = db.socials.find({})

        socials = await cursor.to_list(length=None)

        for s in socials:

            if '_id' in s:

                s['_id'] = str(s['_id'])

        return socials

    async def get_social_by_id(self, social_id):

        db = await get_db()

        try:

            return await db.socials.find_one({'_id': ObjectId(social_id)})

        except:

            return None

    async def update_social(self, social_id: str, update: dict) -> bool:

        db = await get_db()

        try:

            oid = ObjectId(social_id)

        except Exception:

            return False

        allowed_fields = {'name', 'url'}

        update = {k: v for k, v in (update or {}).items() if k in allowed_fields}

        if not update:

            return False

        res = await db.socials.update_one({'_id': oid}, {'$set': update})

        success = bool(res.matched_count)

        if success:

            from app.utils.data_cache import public_data_cache

            await public_data_cache.refresh_socials()

        return success

    async def delete_social(self, social_id):

        db = await get_db()

        try:

            res = await db.socials.delete_one({'_id': ObjectId(social_id)})

            success = bool(res.deleted_count)

            if success:

                from app.utils.data_cache import public_data_cache

                await public_data_cache.refresh_socials()

            return success

        except:

            return False

socials_db = SocialsDatabase()
