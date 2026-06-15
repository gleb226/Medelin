
from app.common.bot_instance import bot

import logging
import html

logger = logging.getLogger(__name__)

async def send_admin_notification(text: str, reply_markup=None, location_id: str | None=None, notification_type: str = 'new_order') -> None:

    from app.databases.admin_database import admin_db

    # Get targets based on role and notification type
    targets = await admin_db.get_notification_targets(location_id, notification_type)

    if not targets:
        return

    for uid in targets:
        try:
            await bot.send_message(uid, text, parse_mode='HTML', reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Failed to send admin notification to {uid}: {e}")

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
