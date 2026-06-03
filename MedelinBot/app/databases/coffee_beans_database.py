
from bson import ObjectId

from typing import Any

from app.databases.mongo_client import get_db

class CoffeeBeansDatabase:

    async def connect(self):

        await get_db()

    async def add_bean(self, name, price_250=0, image_url='', processing='', descriptors='', species='', variety='', altitude='', roast='', taste='', description='', cup_score='', harvest='', acidity=0, bitterness=0, body=0, **extra):

        db = await get_db()

        res = await db.coffee_beans.insert_one({
            'name': name,
            'image_url': image_url or '',
            'processing': processing or '',
            'descriptors': descriptors or '',
            'species': species or '',
            'variety': variety or '',
            'altitude': altitude or '',
            'roast': roast or '',
            'taste': taste or '',
            'description': description or '',
            'cup_score': cup_score or '',
            'harvest': harvest or '',
            'acidity': acidity or 0,
            'bitterness': bitterness or 0,
            'body': body or 0,
            'price_250': price_250 or 0,
            'extra': extra or {}
        })

        inserted_id = str(res.inserted_id)

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_coffee()

        return inserted_id

    async def get_all_beans(self):

        db = await get_db()

        cursor = db.coffee_beans.find({})

        beans = await cursor.to_list(length=None)

        for b in beans:

            if '_id' in b:

                b['_id'] = str(b['_id'])

        return beans

    async def get_bean_by_id(self, bean_id):

        db = await get_db()

        try:

            return await db.coffee_beans.find_one({'_id': ObjectId(bean_id)})

        except:

            return None

    async def update_bean(self, bean_id: str, update: dict) -> bool:

        db = await get_db()

        try:

            oid = ObjectId(bean_id)

        except:

            return False

        res = await db.coffee_beans.update_one({'_id': oid}, {'$set': update})

        success = bool(res.matched_count)

        if success:

            from app.utils.data_cache import public_data_cache

            await public_data_cache.refresh_coffee()

        return success

    async def delete_bean(self, bean_id):

        db = await get_db()

        try:

            res = await db.coffee_beans.delete_one({'_id': ObjectId(bean_id)})

            success = bool(res.deleted_count)

            if success:

                from app.utils.data_cache import public_data_cache

                await public_data_cache.refresh_coffee()

            return success

        except:

            return False

    async def clear_beans(self):

        db = await get_db()

        await db.coffee_beans.delete_many({})

coffee_beans_db = CoffeeBeansDatabase()
