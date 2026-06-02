
from app.common.config import DEVELOPER_IDS

from datetime import datetime, timedelta
import re

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

        if str(user_id) in DEVELOPER_IDS:

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': {'$in': [int(user_id), str(user_id)]}}, {'_id': 0, 'user_id': 1})

        return bool(r)

    async def is_super_admin(self, user_id: int) -> bool:

        if str(user_id) in DEVELOPER_IDS:

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': {'$in': [int(user_id), str(user_id)]}}, {'_id': 0, 'role': 1})

        return (r or {}).get('role') in ('boss', 'owner')

    async def is_boss(self, user_id: int) -> bool:

        if str(user_id) in DEVELOPER_IDS:

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': {'$in': [int(user_id), str(user_id)]}}, {'_id': 0, 'role': 1})

        return (r or {}).get('role') in ('boss', 'owner')

    async def is_developer(self, user_id: int) -> bool:

        return str(user_id) in DEVELOPER_IDS

    async def get_admin_role(self, user_id: int) -> str:

        if str(user_id) in DEVELOPER_IDS:

            return 'developer'

        db = await get_db()

        r = await db.admins.find_one({'user_id': {'$in': [int(user_id), str(user_id)]}}, {'_id': 0, 'role': 1})

        return (r or {}).get('role') or 'user'

    async def get_developers(self) -> list[int]:

        ids = set()

        for bid in DEVELOPER_IDS:

            if bid.strip():

                ids.add(int(bid))

        return list(ids)

    async def add_admin(self, user_id: int, username: str, display_name: str, added_by: int, role: str='boss', receive_notifications: int=1, locations: list=None):

        db = await get_db()
        
        # Заборона додавати роль developer через БД
        if role == 'developer':
            role = 'boss'

        locs = list(locations or [])

        await db.admins.update_one(
            {'user_id': int(user_id)},
            {
                '$set': {
                    'username': username,
                    'display_name': display_name,
                    'role': role,
                    'added_by': int(added_by),
                    'receive_notifications': bool(int(receive_notifications)),
                    'locations': locs,
                },
                '$setOnInsert': {'created_at': datetime.utcnow()},
            },
            upsert=True,
        )

    async def remove_admin(self, user_id: int):

        if str(user_id) in DEVELOPER_IDS:

            return

        db = await get_db()

        await db.admins.delete_one({'user_id': int(user_id)})

    async def has_location_access(self, user_id: int, location_id: str) -> bool:

        if await self.is_super_admin(user_id):

            return True

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id), 'locations': str(location_id)}, {'_id': 0, 'user_id': 1})

        return bool(r)

    async def get_notification_targets(self, location_id: str | None) -> list:
        db = await get_db()
        loc_id_str = str(location_id) if location_id else ''

        targets = set()

        if not location_id or location_id in ('web', 'unknown', 'None', ''):
            # Web/unknown order → send to ALL admins with receive_notifications=True except super
            rows = await db.admins.find({'receive_notifications': True, 'role': {'$ne': 'super'}}, {'_id': 0, 'user_id': 1}).to_list(length=None)
            for r in rows:
                targets.add(int(r['user_id']))

        elif loc_id_str == 'NP':
            # Nova Poshta → delivery_managers first, fallback to all
            rows = await db.admins.find({'receive_notifications': True, 'role': 'delivery_manager'}, {'_id': 0, 'user_id': 1}).to_list(length=None)
            for r in rows:
                targets.add(int(r['user_id']))
            if not targets:
                # Fallback: send to all admins if no delivery_manager found except super
                rows = await db.admins.find({'receive_notifications': True, 'role': {'$ne': 'super'}}, {'_id': 0, 'user_id': 1}).to_list(length=None)
                for r in rows:
                    targets.add(int(r['user_id']))

        else:
            # Real location → admins currently on shift for this location
            rows = await db.admins.find({'receive_notifications': True, 'is_on_shift': loc_id_str}, {'_id': 0, 'user_id': 1}).to_list(length=None)
            for r in rows:
                targets.add(int(r['user_id']))

            if not targets:
                # Nobody on shift → fallback: admins assigned to this location (or assigned to all = empty list) except super
                all_rows = await db.admins.find({'receive_notifications': True, 'role': {'$ne': 'super'}}, {'_id': 0, 'user_id': 1, 'locations': 1}).to_list(length=None)
                for r in all_rows:
                    locs = r.get('locations') or []
                    # Empty list means "all locations"
                    if not locs or loc_id_str in [str(x) for x in locs]:
                        targets.add(int(r['user_id']))

        return list(targets)

    async def get_admins_basic(self) -> list:

        db = await get_db()

        rows = await db.admins.find({}, projection_without_mongo_id()).to_list(length=None)

        if not rows:

            return []

        role_rank = {'developer': 5, 'owner': 4, 'boss': 4, 'admin': 3}

        rows.sort(key=lambda r: (-role_rank.get(r.get('role') or 'admin', 1), int(r.get('user_id') or 0)))

        return [(r['user_id'], r.get('username'), r.get('display_name'), r.get('role') or 'admin') for r in rows]

    async def get_admins_with_locations(self) -> list:

        db = await get_db()

        rows = await db.admins.find({}, projection_without_mongo_id()).to_list(length=None)

        if not rows:

            return []

        role_rank = {'developer': 5, 'owner': 4, 'boss': 4, 'admin': 3}

        rows.sort(key=lambda r: (-role_rank.get(r.get('role') or 'admin', 1), int(r.get('user_id') or 0)))

        result = []

        for r in rows:

            result.append((int(r['user_id']), r.get('username'), r.get('display_name'), r.get('role') or 'admin', int(bool(r.get('is_on_shift'))), int(bool(r.get('receive_notifications'))), list(r.get('locations') or [])))

        return result

    async def get_admin_by_id(self, user_id: int):
        db = await get_db()
        return await db.admins.find_one({'user_id': int(user_id)}, projection_without_mongo_id())

    async def find_admin_by_identifier(self, identifier: str):
        db = await get_db()
        clean_id = str(identifier).strip().replace('@', '').lower()
        
        # 1. Спробуємо знайти в колекції admins (по username, phone або user_id)
        # По username
        res = await db.admins.find_one({'username': {'$regex': f'^{re.escape(clean_id)}$', '$options': 'i'}}, projection_without_mongo_id())
        if res: return res
        
        # По phone (нормалізованому)
        from app.utils.phone_utils import normalize_phone
        norm = normalize_phone(identifier)
        if norm and len(norm) >= 10:
            res = await db.admins.find_one({'$or': [{'phone_digits': norm}, {'phone': {'$regex': re.escape(norm)}}]}, projection_without_mongo_id())
            if res: return res
            
        # По user_id
        if identifier.isdigit():
            res = await db.admins.find_one({'user_id': int(identifier)}, projection_without_mongo_id())
            if res: return res
            
        # 2. Якщо не знайдено в admins, перевіримо чи це розробник (DEVELOPER_IDS)
        from app.databases.user_database import user_db
        user_info = None
        
        if identifier.isdigit():
            target_id = int(identifier)
            if str(target_id) in DEVELOPER_IDS:
                user_info = await user_db.get_user_by_id(target_id)
                if user_info:
                    uid, name, uname, uphone = user_info
                    return {'user_id': uid, 'display_name': name or 'Developer', 'role': 'developer', 'username': uname}
                return {'user_id': target_id, 'display_name': 'Developer', 'role': 'developer'}
        
        # Спробуємо знайти в users по телефону, а потім звірити з DEVELOPER_IDS
        if norm and len(norm) >= 10:
            user_info = await user_db.get_user_by_phone(norm)
            
        # Потім по username
        if not user_info:
            user_info = await user_db.get_user_by_username(clean_id)
            
        if user_info:
            uid, name, uname, uphone = user_info
            if str(uid) in DEVELOPER_IDS:
                return {'user_id': uid, 'display_name': name or 'Developer', 'role': 'developer', 'username': uname}

        return None

    async def create_auth_request(self, user_id: int, code: str):
        db = await get_db()
        await db.admin_auth_requests.update_one(
            {'user_id': int(user_id)},
            {'$set': {'code': code, 'confirmed': False, 'created_at': datetime.utcnow()}},
            upsert=True
        )

    async def confirm_auth_request(self, user_id: int):
        db = await get_db()
        await db.admin_auth_requests.update_one(
            {'user_id': int(user_id)},
            {'$set': {'confirmed': True}}
        )

    async def get_auth_request(self, user_id: int):
        db = await get_db()
        return await db.admin_auth_requests.find_one({'user_id': int(user_id)})

    async def create_session(self, user_id: int, token: str):
        db = await get_db()
        await db.admin_sessions.insert_one({
            'user_id': int(user_id),
            'token': token,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(days=7)
        })

    async def verify_session(self, token: str):
        db = await get_db()
        sess = await db.admin_sessions.find_one({
            'token': token,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        if not sess: return None
        
        user_id = sess['user_id']
        admin = await self.get_admin_by_id(user_id)
        
        if not admin and str(user_id) in DEVELOPER_IDS:
            return {'user_id': int(user_id), 'display_name': 'Developer', 'role': 'developer'}
            
        return admin

    async def get_locations_for_admin(self, user_id: int) -> list:

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'locations': 1})

        return list((r or {}).get('locations') or [])

admin_db = AdminDatabase()
