
from aiogram import Bot

from app.common.config import BOSS_IDS, BOT_TOKEN

async def send_admin_notification(text: str, reply_markup=None, location_id: str | None=None, include_boss: bool=True) -> None:

    if not BOT_TOKEN:

        return

    from app.databases.admin_database import admin_db

    targets: set[int] = set()

    if include_boss:
        pass # Boss auto-inclusion removed by request

    if location_id:

        shift_ids = await admin_db.get_notification_targets(location_id)

        targets.update(shift_ids)

    if not targets:

        return

    bot = Bot(token=BOT_TOKEN)

    try:

        for uid in targets:

            try:

                await bot.send_message(uid, text, parse_mode='HTML', reply_markup=reply_markup)

            except Exception:

                pass

    finally:

        await bot.session.close()

async def send_developer_error(error_text: str) -> None:

    if not BOT_TOKEN:

        return

    from app.databases.admin_database import admin_db

    targets = set()

    for bid in BOSS_IDS:

        bid = str(bid).strip()

        if bid:

            targets.add(int(bid))

    devs = await admin_db.get_developers()

    targets.update(devs)

    if not targets:

        return

    bot = Bot(token=BOT_TOKEN)

    try:

        for uid in targets:

            try:

                await bot.send_message(uid, f"🛠 <b>DEVELOPER ALERT</b>\n\n{error_text}", parse_mode='HTML')

            except Exception:

                pass

    finally:

        await bot.session.close()
