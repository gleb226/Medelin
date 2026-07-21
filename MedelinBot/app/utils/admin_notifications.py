
from app.common.bot_instance import bot

import logging
import html

logger = logging.getLogger(__name__)

async def send_admin_notification(text: str, reply_markup=None, location_id: str | None=None, notification_type: str = 'new_order', order_id: str | None = None) -> None:

    from app.databases.admin_database import admin_db
    from app.databases.mongo_client import get_db

    targets = await admin_db.get_notification_targets(location_id, notification_type)

    if not targets:
        return

    db = await get_db()

    for uid in targets:
        try:
            msg = await bot.send_message(uid, text, parse_mode='HTML', reply_markup=reply_markup)
            if order_id:

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
    if status == 'confirmed': status_label = "✅ ПІДТВЕРДЖЕНО"
    elif status == 'completed': status_label = "🏁 ЗАВЕРШЕНО"
    elif status == 'paid': status_label = "💳 ОПЛАЧЕНО"
    elif status == 'new': status_label = "🆕 НОВЕ"
    else: status_label = "❌ ВІДХИЛЕНО"

    cursor = db.order_notifications.find({'order_id': str(order_id)})
    notifications = await cursor.to_list(length=None)

    for n in notifications:
        try:

            type_map = {
                'takeaway': 'З собою', 'in_house': 'В закладі', 
                'nova_poshta': 'Доставка', 'beans_delivery': 'Доставка', 
                'beans_booking': 'Самовивіз'
            }
            order_type = order.get('order_type')
            type_label = type_map.get(order_type, order_type)

            delivery_info = order.get('delivery_info') or ""
            if not delivery_info and order_type == 'in_house':
                delivery_info = f"Стіл {order.get('table_number', '?')}"

            if order.get('status') == 'paid' or order.get('is_paid'): pay_label = "ОПЛАЧЕНО"
            else: pay_label = "НАКЛАДНИЙ ПЛАТІЖ"

            new_text = f"📦 <b>ЗАМОВЛЕННЯ #{order.get('order_number', '???')}</b>\n"
            new_text += f"👤 <b>{order.get('fullname')}</b>\n"
            new_text += f"📞 <code>{order.get('phone')}</code>\n"
            new_text += f"🚚 Куди: <b>{type_label} {delivery_info}</b>\n"
            new_text += f"💰 Сума: <b>{order.get('total_amount', order.get('total', 0))} ₴</b>\n"
            new_text += f"💳 Оплата: <b>{pay_label}</b>\n\n"
            new_text += f"🛒 <b>СКЛАД:</b>\n{order.get('cart')}\n\n"
            new_text += f"📝 ПОБАЖАННЯ: <b>{order.get('wishes') or '—'}</b>"

            kb = None
            if status == 'confirmed':
                kb = akb.get_active_finish_kb(order_id)

            await bot.edit_message_text(
                text=new_text,
                chat_id=n['admin_id'],
                message_id=n['message_id'],
                reply_markup=kb,
                parse_mode='HTML'
            )
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
