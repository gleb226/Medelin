
from app.common.bot_instance import bot

import logging
import html

logger = logging.getLogger(__name__)

async def send_admin_notification(text: str, reply_markup=None, location_id: str | None=None, notification_type: str = 'new_order', order_id: str | None = None) -> None:

    from app.databases.admin_database import admin_db
    from app.databases.mongo_client import get_db

    # Get targets based on role and notification type
    targets = await admin_db.get_notification_targets(location_id, notification_type)

    if not targets:
        return

    db = await get_db()

    for uid in targets:
        try:
            msg = await bot.send_message(uid, text, parse_mode='HTML', reply_markup=reply_markup)
            if order_id:
                # Store message mapping for sync
                await db.order_notifications.insert_one({
                    'order_id': str(order_id),
                    'admin_id': int(uid),
                    'message_id': int(msg.message_id),
                    'timestamp': datetime.utcnow()
                })
        except Exception as e:
            logger.error(f"Failed to send admin notification to {uid}: {e}")

async def update_order_notifications(order_id: str, status: str) -> None:
    """Updates all Telegram messages related to this order with new status."""
    from app.databases.mongo_client import get_db
    from app.databases.orders_database import orders_db
    import app.keyboards.admin_keyboards as akb
    from app.utils.message_utils import safe_edit_message
    
    db = await get_db()
    order = await orders_db.get_order_by_id(order_id)
    if not order: return
    
    order_num = order.get('order_number', '—')
    status_label = "✅ ПІДТВЕРДЖЕНО" if status == 'confirmed' else "❌ ВІДХИЛЕНО"
    if status == 'completed': status_label = "🏁 ЗАВЕРШЕНО"
    
    # Find all messages sent for this order
    cursor = db.order_notifications.find({'order_id': str(order_id)})
    notifications = await cursor.to_list(length=None)
    
    for n in notifications:
        try:
            # We don't have the original text easily, but we can reconstruct a summary or just append status
            # For simplicity, we edit the keyboard to remove action buttons and add status text
            # Better: use bot.edit_message_reply_markup and maybe bot.edit_message_text if we had text.
            # Since we don't have text, we'll try to get it if possible, but safe_edit_message needs text.
            
            # Reconstruct basic info
            new_text = f"📦 <b>ЗАМОВЛЕННЯ #{order_num}</b>\nСтатус: <b>{status_label}</b>"
            
            kb = None
            if status == 'confirmed':
                kb = akb.get_active_finish_kb(order_id)
            
            await bot.edit_message_reply_markup(
                chat_id=n['admin_id'],
                message_id=n['message_id'],
                reply_markup=kb
            )
            
            # Optional: edit text to show who did it?
            # await bot.edit_message_text(...)
            
        except Exception as e:
            logger.error(f"Failed to update notification for admin {n['admin_id']}: {e}")

from datetime import datetime

async def send_developer_error(error_text: str) -> None:

    from app.common.config import DEVELOPER_IDS
    from app.databases.admin_database import admin_db

    targets = set()

    for bid in DEVELOPER_IDS:
        bid = str(bid).strip()
        if bid:
            try: targets.add(int(bid))
            except: pass

    try:
        devs = await admin_db.get_developers()
        targets.update(devs)
    except Exception as e:
        logger.error(f"Failed to get developers from DB: {e}")

    if not targets:
        logger.warning("No developer targets found to send error.")
        return

    for uid in targets:
        try:
            await bot.send_message(uid, f"🛠 <b>DEVELOPER ALERT</b>\n\n{error_text}", parse_mode='HTML')
        except Exception as e:
            logger.error(f"CRITICAL: Failed to send developer alert to {uid}: {e}. Error text was: {error_text}")
