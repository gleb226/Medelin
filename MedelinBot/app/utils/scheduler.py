
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from datetime import datetime, timedelta

from app.databases.admin_database import admin_db
from app.databases.mongo_client import get_db
from app.utils.logger import log_activity

async def cleanup_old_data() -> None:
    db = await get_db()
    now = datetime.utcnow()

    # Retention rules (user request)
    cut_active = now - timedelta(days=5)
    cut_logs = now - timedelta(days=5)
    cut_sales_bookings = now - timedelta(days=5)
    cut_users = now - timedelta(days=180)
    cut_support = now - timedelta(days=3)
    cut_errors = now - timedelta(days=30)

    try:
        res_active_b = await db.active_bookings.delete_many({'created_at': {'$lt': cut_active}})
        res_active_o = await db.active_orders.delete_many({'created_at': {'$lt': cut_active}})

        res_logs = await db.activity_logs.delete_many({'timestamp': {'$lt': cut_logs}})

        res_sales = await db.sales.delete_many({'timestamp': {'$lt': cut_sales_bookings}})
        res_bookings = await db.bookings.delete_many({'created_at': {'$lt': cut_sales_bookings}})

        # Users: keep admins; remove inactive users older than 6 months
        admins = await admin_db.get_admins_basic()
        admin_ids = {int(a[0]) for a in admins or []}
        res_users = await db.users.delete_many({'joined_at': {'$lt': cut_users}, 'user_id': {'$nin': list(admin_ids)}})

        # Support messages / notifications-like docs
        res_msgs = await db.guest_messages.delete_many({'created_at': {'$lt': cut_support}})
        res_notif = None
        if 'notifications' in await db.list_collection_names():
            res_notif = await db.notifications.delete_many({'created_at': {'$lt': cut_support}})

        res_errors = await db.errors.delete_many({'timestamp': {'$lt': cut_errors}})

        deleted_total = sum([
            int(res_active_b.deleted_count or 0),
            int(res_active_o.deleted_count or 0),
            int(res_logs.deleted_count or 0),
            int(res_sales.deleted_count or 0),
            int(res_bookings.deleted_count or 0),
            int(res_users.deleted_count or 0),
            int(res_msgs.deleted_count or 0),
            int(res_errors.deleted_count or 0),
            int(res_notif.deleted_count or 0) if res_notif else 0,
        ])

        if deleted_total:
            await log_activity(
                0,
                'system',
                'db_cleanup',
                (
                    f'Cleanup: active_bookings={res_active_b.deleted_count}, active_orders={res_active_o.deleted_count}, '
                    f'logs={res_logs.deleted_count}, sales={res_sales.deleted_count}, bookings={res_bookings.deleted_count}, '
                    f'users={res_users.deleted_count}, guest_messages={res_msgs.deleted_count}, errors={res_errors.deleted_count}'
                ),
            )
    except Exception as e:
        await log_activity(0, 'system', 'db_cleanup_error', str(e))

from app.common.bot_instance import bot
import html

async def send_monthly_stats() -> None:
    db = await get_db()
    
    # Calculate for the previous month
    now = datetime.utcnow()
    # Go to the first day of current month, then subtract one day to get into previous month
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_prev_month = first_day_this_month - timedelta(seconds=1)
    first_day_prev_month = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    query = {
        'record_type': 'sale',
        'timestamp': {'$gte': first_day_prev_month, '$lte': last_day_prev_month}
    }
    
    sales = await db.sales.find(query).to_list(length=None)
    
    if not sales:
        stats_text = f"📊 <b>ЗВІТ ЗА {first_day_prev_month.strftime('%m/%Y')}</b>\n\nПродажів не знайдено."
    else:
        total_sum = sum(s.get('total', 0) for s in sales)
        order_count = len(sales)
        unique_users = len(set(s.get('user_id') for s in sales if s.get('user_id')))
        
        # Estimate items sold from cart strings if possible, or just use order count
        # For now, let's use order count as requested "кількість замовлень" and "продано товарів"
        # Since 'items' is a string, parsing it accurately might be tricky, 
        # but we can count lines or "xN" patterns.
        total_items = 0
        for s in sales:
            items_str = s.get('items', '')
            # Count lines starting with '-' or containing 'x'
            lines = [l for l in items_str.split('\n') if l.strip()]
            for l in lines:
                match = re.search(r'x(\d+)', l)
                if match: total_items += int(match.group(1))
                else: total_items += 1

        avg_check = total_sum / order_count if order_count > 0 else 0
        
        stats_text = (
            f"📊 <b>ЗВІТ ЗА {first_day_prev_month.strftime('%m/%Y')}</b>\n\n"
            f"📦 Продано товарів: <b>{total_items}</b>\n"
            f"🧾 Кількість замовлень: <b>{order_count}</b>\n"
            f"💰 Загальна сума: <b>{total_sum} ₴</b>\n"
            f"📈 Середній чек: <b>{avg_check:.2f} ₴</b>"
        )

    # Send to developers
    dev_ids = await admin_db.get_developers()
    for dev_id in dev_ids:
        try:
            await bot.send_message(dev_id, stats_text, parse_mode='HTML')
        except:
            pass

def start_scheduler() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_old_data, 'cron', hour=3, minute=0)
    # Monthly stats on the 1st day of each month at 00:01
    scheduler.add_job(send_monthly_stats, 'cron', day=1, hour=0, minute=1)
    scheduler.start()
