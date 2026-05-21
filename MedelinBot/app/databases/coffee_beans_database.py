
from bson import ObjectId

from typing import Any

from app.databases.mongo_client import get_db

class CoffeeBeansDatabase:

    async def connect(self):

        await get_db()

    def calculate_prices(self, price_250: float, *, price_500: float | None=None, price_1000: float | None=None) -> dict:

        p500 = price_250 * 2 * 0.97

        p1000 = price_250 * 4 * 0.92

        return {'250': round(price_250), '500': round(price_500) if price_500 is not None else round(p500), '1000': round(price_1000) if price_1000 is not None else round(p1000)}

    async def add_bean(self, name, price_250, description, sort, taste, roast, image_url='', country='', altitude='', processing='', recommendation='', variety='', cup_score='', harvest='', acidity=0, bitterness=0, body=0, *, price_500: float | None=None, price_1000: float | None=None, **extra):

        db = await get_db()

        prices = self.calculate_prices(float(price_250), price_500=price_500, price_1000=price_1000)

        res = await db.coffee_beans.insert_one({'name': name, 'price_250': prices['250'], 'price_500': prices['500'], 'price_1000': prices['1000'], 'description': description, 'sort': sort, 'taste': taste, 'roast': roast, 'image_url': image_url, 'country': country, 'altitude': altitude, 'processing': processing, 'recommendation': recommendation, 'variety': variety, 'cup_score': cup_score, 'harvest': harvest, 'acidity': acidity, 'bitterness': bitterness, 'body': body, 'extra': extra or {}})

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
