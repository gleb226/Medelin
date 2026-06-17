
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
        r = await db.admins.find_one({'user_id': {'$in': [int(user_id), str(user_id)]}}, {'_id': 0, 'role': 1})
        return bool(r)

    async def is_owner(self, user_id: int) -> bool:
        if str(user_id) in DEVELOPER_IDS:
            return True
        db = await get_db()
        r = await db.admins.find_one({'user_id': {'$in': [int(user_id), str(user_id)]}}, {'_id': 0, 'role': 1})
        return (r or {}).get('role') == 'owner'

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
                try: ids.add(int(bid))
                except: pass
        return list(ids)

    async def add_admin(self, user_id: int, username: str, display_name: str, added_by: int, role: str='admin', locations: list=None):
        db = await get_db()
        
        # Mapping old role names if any
        if role in ('boss', 'super'):
            role = 'owner'
        
        if role not in ('owner', 'admin'):
            role = 'admin'

        await db.admins.update_one(
            {'user_id': int(user_id)},
            {
                '$set': {
                    'username': username,
                    'display_name': display_name,
                    'role': role,
                    'added_by': int(added_by),
                    'receive_notifications': True,
                    'locations': locations or [],
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

    async def get_notification_targets(self, location_id: str | None, notification_type: str = 'new_order') -> list:
        db = await get_db()
        targets = set()

        if notification_type == 'stock_alert':
            # Stock alerts go to Owners (and Developers via send_admin_notification wrapper)
            rows = await db.admins.find({'role': 'owner', 'receive_notifications': True}, {'_id': 0, 'user_id': 1}).to_list(length=None)
            for r in rows:
                targets.add(int(r['user_id']))
            return list(targets)

        # Default: new_order notifications go to Admins
        # Filter by shift/location if possible, but as per new rules, Admins see all New/Active
        rows = await db.admins.find({'role': 'admin', 'receive_notifications': True}, {'_id': 0, 'user_id': 1}).to_list(length=None)
        for r in rows:
            targets.add(int(r['user_id']))

        return list(targets)

    async def get_admins_basic(self) -> list:
        db = await get_db()
        rows = await db.admins.find({}, projection_without_mongo_id()).to_list(length=None)
        if not rows: return []
        role_rank = {'developer': 5, 'owner': 4, 'admin': 2}
        rows.sort(key=lambda r: (-role_rank.get(r.get('role') or 'admin', 1), int(r.get('user_id') or 0)))
        return [(r['user_id'], r.get('username'), r.get('display_name'), r.get('role') or 'admin') for r in rows]

    async def get_admins_with_locations(self) -> list:

        db = await get_db()

        rows = await db.admins.find({}, projection_without_mongo_id()).to_list(length=None)

        if not rows:

            return []

        role_rank = {'developer': 5, 'owner': 4, 'boss': 4, 'delivery_manager': 3, 'admin': 2}

        rows.sort(key=lambda r: (-role_rank.get(r.get('role') or 'admin', 1), int(r.get('user_id') or 0)))

        result = []

        for r in rows:

            result.append((str(r['user_id']), r.get('username'), r.get('display_name'), r.get('role') or 'admin', int(bool(r.get('is_on_shift'))), int(bool(r.get('receive_notifications'))), list(r.get('locations') or [])))

        return result

    async def get_admin_by_id(self, user_id: int):
        db = await get_db()
        return await db.admins.find_one({'user_id': int(user_id)}, projection_without_mongo_id())

    async def find_admin_by_identifier(self, identifier: str):
        db = await get_db()
        clean_id = str(identifier).strip().replace('@', '')
        
        # 1. Search in admins collection
        if identifier.isdigit():
            res = await db.admins.find_one({'user_id': int(identifier)}, projection_without_mongo_id())
            if res: return res
            
        res = await db.admins.find_one({'username': {'$regex': f'^{re.escape(clean_id)}$', '$options': 'i'}}, projection_without_mongo_id())
        if res: return res
        
        from app.utils.phone_utils import normalize_phone
        norm = normalize_phone(identifier)
        if norm and len(norm) >= 10:
            res = await db.admins.find_one({'$or': [{'phone_digits': norm}, {'phone': {'$regex': re.escape(norm)}}]}, projection_without_mongo_id())
            if res: return res

        # 2. Search in users collection
        from app.databases.user_database import user_db
        user_info = None
        
        if identifier.isdigit():
            user_info = await user_db.get_user_by_id(int(identifier))
        if not user_info and norm and len(norm) >= 10:
            user_info = await user_db.get_user_by_phone(norm)
        if not user_info:
            user_info = await user_db.get_user_by_username(clean_id)
            
        if user_info:
            uid, name, uname, uphone = user_info
            role = 'developer' if str(uid) in DEVELOPER_IDS else 'user'
            return {'user_id': uid, 'display_name': name or uname or 'Користувач', 'username': uname, 'role': role}

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

    async def delete_auth_request(self, user_id: int):
        db = await get_db()
        await db.admin_auth_requests.delete_one({'user_id': int(user_id)})

    async def create_session(self, user_id: int, token: str):
        db = await get_db()
        await db.admin_sessions.insert_one({
            'user_id': int(user_id),
            'token': token,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=2)
        })

    async def verify_session(self, token: str):
        db = await get_db()
        now = datetime.utcnow()
        sess = await db.admin_sessions.find_one({
            'token': token,
            'expires_at': {'$gt': now}
        })
        if not sess: return None
        
        # Refresh session for another 2 hours on each request (inactivity timeout)
        await db.admin_sessions.update_one(
            {'_id': sess['_id']},
            {'$set': {'expires_at': now + timedelta(hours=2)}}
        )
        
        user_id = sess['user_id']
        admin = await self.get_admin_by_id(user_id)
        
        if not admin and str(user_id) in DEVELOPER_IDS:
            return {'user_id': int(user_id), 'display_name': 'Developer', 'role': 'developer'}
            
        return admin

    async def get_all_admins(self) -> list:
        db = await get_db()
        return await db.admins.find({}, projection_without_mongo_id()).to_list(length=None)

    async def get_locations_for_admin(self, user_id: int) -> list:

        db = await get_db()

        r = await db.admins.find_one({'user_id': int(user_id)}, {'_id': 0, 'locations': 1})

        return list((r or {}).get('locations') or [])

admin_db = AdminDatabase()
