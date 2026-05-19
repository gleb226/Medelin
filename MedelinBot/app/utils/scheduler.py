
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.databases.booking_database import booking_db

from app.databases.sales_database import sales_db

from app.databases.mongo_client import get_db

from app.utils.logger import log_activity

from datetime import datetime, timedelta

async def cleanup_old_data():

    try:

        cutoff = datetime.utcnow() - timedelta(days=180)

        deleted_bookings = await booking_db.cleanup_old_bookings(months=6)

        db = await get_db()

        res_logs = await db.activity_logs.delete_many({'timestamp': {'$lt': cutoff}})

        res_errors = await db.errors.delete_many({'timestamp': {'$lt': cutoff}})

        res_sales = await db.sales.delete_many({'timestamp': {'$lt': cutoff}})

        deleted_total = int(deleted_bookings) + int(res_logs.deleted_count or 0) + int(res_errors.deleted_count or 0) + int(res_sales.deleted_count or 0)

        if deleted_total > 0:

            await log_activity(0, 'system', 'db_cleanup', f'Deleted old records: bookings={deleted_bookings}, logs={res_logs.deleted_count}, errors={res_errors.deleted_count}, sales={res_sales.deleted_count}')

    except Exception as e:

        await log_activity(0, 'system', 'db_cleanup_error', str(e))

async def monthly_full_cleanup():

    try:

        deleted_bookings = await booking_db.clear_all_bookings()

        deleted_sales = await sales_db.clear_all_sales()

        db = await get_db()

        res_logs = await db.activity_logs.delete_many({})

        res_errors = await db.errors.delete_many({})

        await log_activity(0, 'system', 'monthly_cleanup', f'Monthly cleanup completed: bookings={deleted_bookings}, sales={deleted_sales}, logs={res_logs.deleted_count}, errors={res_errors.deleted_count}')

    except Exception as e:

        await log_activity(0, 'system', 'monthly_cleanup_error', str(e))

def start_scheduler():

    scheduler = AsyncIOScheduler()

    scheduler.add_job(cleanup_old_data, 'cron', hour=3, minute=0)

    scheduler.add_job(monthly_full_cleanup, 'cron', day=1, hour=4, minute=0)

    scheduler.start()
