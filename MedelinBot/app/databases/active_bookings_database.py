
from __future__ import annotations

from datetime import datetime, timedelta

from bson import ObjectId

from app.databases.mongo_client import get_db

class ActiveBookingsDatabase:

    @staticmethod

    def _parse_booking_datetime(date_time: str) -> datetime:

        value = (date_time or '').strip().replace(' о ', ' ').replace(' ? ', ' ')

        if not value:

            return datetime.utcnow()

        formats = ('%d.%m %H:%M', '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M')

        for fmt in formats:

            try:

                parsed = datetime.strptime(value, fmt)

                if fmt == '%d.%m %H:%M':

                    return parsed.replace(year=datetime.now().year)

                return parsed

            except ValueError:

                continue

        return datetime.utcnow()

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def add_booking(self, order_id, fullname, location_id, date_time, people_count):

        db = await get_db()

        booking_dt = self._parse_booking_datetime(date_time)

        await db.active_bookings.insert_one({

            'order_id': str(order_id),

            'fullname': fullname,

            'location_id': str(location_id),

            'date_time_str': date_time,

            'booking_at': booking_dt,

            'people_count': people_count,

            'created_at': datetime.utcnow()

        })

    async def add_active_booking(self, order_id, user_id, fullname, phone, location_id, date_time, people_count, wishes):

        db = await get_db()

        booking_dt = self._parse_booking_datetime(date_time)

        await db.active_bookings.insert_one({'order_id': str(order_id), 'user_id': int(user_id) if user_id is not None else None, 'fullname': fullname, 'phone': phone, 'location_id': str(location_id), 'date_time_str': date_time, 'booking_at': booking_dt, 'people_count': people_count, 'wishes': wishes, 'created_at': datetime.utcnow()})

    async def get_active_bookings(self, location_ids=None):

        db = await get_db()

        query = {}

        if location_ids:

            query['location_id'] = {'$in': [str(x) for x in location_ids]}

        cutoff = datetime.now() - timedelta(hours=1)

        await db.active_bookings.delete_many({'booking_at': {'$lt': cutoff}})

        cur = db.active_bookings.find(query).sort('booking_at', 1)

        return await cur.to_list(length=None)

    async def remove_booking(self, active_id):

        db = await get_db()

        await db.active_bookings.delete_one({'_id': ObjectId(str(active_id))})

    async def remove_booking_by_order_id(self, order_id):

        db = await get_db()

        await db.active_bookings.delete_one({'order_id': str(order_id)})

    async def get_all_active_bookings(self):
        db = await get_db()
        # Clean up old ones first (optional here as it's done in get_active_bookings)
        cur = db.active_bookings.find({}).sort('booking_at', 1)
        return await cur.to_list(length=None)

active_bookings_db = ActiveBookingsDatabase()
