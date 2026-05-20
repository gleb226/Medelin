
from app.common.config import BOSS_IDS

from datetime import datetime

from app.databases.mongo_client import get_db, projection_without_mongo_id

class AdminDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def set_shift_status(self, user_id: int, status):

        db = await get_db()

        await db.admins.update_one({'user_id': int(user_id)}, {'$set': {'is_on_shift': status}})

    async def is_on_shift(self, user_id: int):

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'is_on_shift': 1})

        return (r or {}).get('is_on_shift') or False

    async def is_admin(self, user_id: int) -> bool:

        if str(user_id) in BOSS_IDS:

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'user_id': 1})

        return bool(r)

    async def is_super_admin(self, user_id: int) -> bool:

        if str(user_id) in BOSS_IDS:

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'role': 1})

        return (r or {}).get('role') in ('super', 'boss', 'owner', 'developer')

    async def is_boss(self, user_id: int) -> bool:

        if str(user_id) in BOSS_IDS:

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'role': 1})

        return (r or {}).get('role') in ('boss', 'owner')

    async def is_developer(self, user_id: int) -> bool:

        if str(user_id) in BOSS_IDS:

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'role': 1})

        return (r or {}).get('role') == 'developer'

    async def get_admin_role(self, user_id: int) -> str:

        if str(user_id) in BOSS_IDS:

            return 'developer'

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'role': 1})

        return (r or {}).get('role') or 'user'

    async def get_developers(self) -> list[int]:

        db = await get_db()

        cur = db.admins.find({'role': 'developer'}, {'_id': 0, 'user_id': 1})

        rows = await cur.to_list(length=None)

        ids = {int(r['user_id']) for r in rows or []}

        for bid in BOSS_IDS:

            if bid.strip():

                ids.add(int(bid))

        return list(ids)

    async def add_admin(self, user_id: int, username: str, display_name: str, added_by: int, role: str='admin', receive_notifications: int=1, locations: list=None):

        db = await get_db()

        locs = list(locations or [])

        await db.admins.update_one({'user_id': int(user_id)}, {'$set': {'username': username, 'display_name': display_name, 'role': role, 'added_by': int(added_by), 'receive_notifications': bool(int(receive_notifications)), 'locations': locs}, '$setOnInsert': {'created_at': datetime.utcnow()}}, upsert=True)

    async def remove_admin(self, user_id: int):

        if str(user_id) in BOSS_IDS:

            return

        db = await get_db()

        await db.admins.delete_one({'user_id': int(user_id)})

    async def has_location_access(self, user_id: int, location_id: str) -> bool:

        if await self.is_super_admin(user_id):

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id), 'locations': str(location_id)}, {'_id': 0, 'user_id': 1})

        return bool(r)

    async def get_notification_targets(self, location_id: str) -> list:
        db = await get_db()
        loc_id_str = str(location_id)
        
        # Строга фільтрація:
        # - Якщо це Нова Пошта (location_id == 'NP'), то відправляємо лише 'delivery_manager'
        # - Якщо це звичайний заклад, то відправляємо ТІЛЬКИ тим адмінам, які зараз на зміні в цьому закладі.
        
        if loc_id_str == "NP":
            query = {
                'receive_notifications': True,
                'role': 'delivery_manager'
            }
        else:
            query = {
                'receive_notifications': True,
                'role': 'admin',
                'is_on_shift': loc_id_str
            }
            
        cur = db.admins.find(query, {'_id': 0, 'user_id': 1})
        rows = await cur.to_list(length=None)
        
        targets = set()
        for r in rows:
            targets.add(int(r['user_id']))
            
        return list(targets)

    async def get_admins_basic(self) -> list:

        db = await get_db()

        rows = await db.admins.find({}, projection_without_mongo_id()).to_list(length=None)

        if not rows:

            return []

        role_rank = {'developer': 5, 'owner': 4, 'boss': 4, 'super': 3, 'admin': 2}

        rows.sort(key=lambda r: (-role_rank.get(r.get('role') or 'admin', 1), int(r.get('user_id') or 0)))

        return [(r['user_id'], r.get('username'), r.get('display_name'), r.get('role') or 'admin') for r in rows]

    async def get_admins_with_locations(self) -> list:

        db = await get_db()

        rows = await db.admins.find({}, projection_without_mongo_id()).to_list(length=None)

        if not rows:

            return []

        role_rank = {'developer': 5, 'owner': 4, 'boss': 4, 'super': 3, 'admin': 2}

        rows.sort(key=lambda r: (-role_rank.get(r.get('role') or 'admin', 1), int(r.get('user_id') or 0)))

        result = []

        for r in rows:

            result.append((int(r['user_id']), r.get('username'), r.get('display_name'), r.get('role') or 'admin', int(bool(r.get('is_on_shift'))), int(bool(r.get('receive_notifications'))), list(r.get('locations') or [])))

        return result

    async def get_admin_by_id(self, user_id: int):

        db = await get_db()

        return await db.admins.find_one({'user_id': int(user_id)}, projection_without_mongo_id())

    async def get_locations_for_admin(self, user_id: int) -> list:

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'locations': 1})

        return list((r or {}).get('locations') or [])

admin_db = AdminDatabase()
