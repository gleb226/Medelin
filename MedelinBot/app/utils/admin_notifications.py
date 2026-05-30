
from app.common.bot_instance import bot

async def send_admin_notification(text: str, reply_markup=None, location_id: str | None=None, include_boss: bool=True) -> None:

    from app.databases.admin_database import admin_db

    targets: set[int] = set()

    # Get targets based on location
    shift_ids = await admin_db.get_notification_targets(location_id)
    targets.update(shift_ids)

    if not targets:
        return

    for uid in targets:

        try:

            await bot.send_message(uid, text, parse_mode='HTML', reply_markup=reply_markup)

        except Exception:

            pass

async def send_developer_error(error_text: str) -> None:

    from app.common.config import DEVELOPER_IDS
    from app.databases.admin_database import admin_db

    targets = set()

    for bid in DEVELOPER_IDS:

        bid = str(bid).strip()

        if bid:

            try: targets.add(int(bid))
            except: pass

    devs = await admin_db.get_developers()

    targets.update(devs)

    if not targets:

        return

    for uid in targets:

        try:

            await bot.send_message(uid, f"🛠 <b>DEVELOPER ALERT</b>\n\n{error_text}", parse_mode='HTML')

        except Exception:

            pass
