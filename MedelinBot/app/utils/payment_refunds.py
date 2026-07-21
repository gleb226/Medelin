from __future__ import annotations

import logging
from liqpay import LiqPay
from app.common.config import LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY

async def process_refund(order_id: str) -> tuple[bool, str | None]:
    if not LIQPAY_PUBLIC_KEY or not LIQPAY_PRIVATE_KEY:
        return (False, 'LiqPay keys not configured')
    try:
        liqpay = LiqPay(LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY)
        res = liqpay.api("request", {
            "action": "refund",
            "version": "3",
            "order_id": str(order_id)
        })
        if res.get('result') == 'ok' or res.get('status') in ('reversed', 'wait_refund'):
            return (True, None)
        return (False, res.get('err_description') or str(res))
    except Exception as e:
        logging.exception('Refund error')
        return (False, str(e))
