
from bson import ObjectId

from typing import Any

from app.databases.mongo_client import get_db

class LocationDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def add_location(self, name, address, schedule, google_maps_url, coordinates=None, image_url='', amenities=None, atmosphere='', description=''):
        db = await get_db()
        res = await db.locations.insert_one({'name': name, 'address': address, 'schedule': schedule, 'google_maps_url': google_maps_url, 'coordinates': coordinates or {'lat': 0.0, 'lon': 0.0}, 'image_url': image_url or '', 'amenities': amenities or [], 'atmosphere': atmosphere or '', 'description': description or ''})
        inserted_id = str(res.inserted_id)


        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_locations()

        return inserted_id

    async def get_all_locations(self):

        db = await get_db()

        cursor = db.locations.find({})

        locs = await cursor.to_list(length=None)

        for l in locs:

            if '_id' in l:

                l['_id'] = str(l['_id'])

        return locs

    async def get_locations_dict(self):

        db = await get_db()

        cursor = db.locations.find({})

        locations = await cursor.to_list(length=None)

        return {str(loc['_id']): loc for loc in locations}

    async def get_location_by_id(self, loc_id):

        db = await get_db()

        try:

            return await db.locations.find_one({'_id': ObjectId(loc_id)})

        except:

            return None

    async def update_location(self, loc_id: str, update: dict) -> bool:

        db = await get_db()

        try:

            oid = ObjectId(loc_id)

        except:

            return False

        res = await db.locations.update_one({'_id': oid}, {'$set': update})

        success = bool(res.matched_count)

        if success:

            from app.utils.data_cache import public_data_cache

            await public_data_cache.refresh_locations()

        return success

    async def delete_location(self, loc_id):

        db = await get_db()

        try:

            res = await db.locations.delete_one({'_id': ObjectId(loc_id)})

            success = bool(res.deleted_count)

            if success:

                from app.utils.data_cache import public_data_cache

                await public_data_cache.refresh_locations()

            return success

        except:

            return False

    async def clear_locations(self):

        db = await get_db()

        await db.locations.delete_many({})

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_locations()

location_db = LocationDatabase()
