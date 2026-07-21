
from datetime import datetime, timezone, timedelta

from app.common.config import WORK_START_HOUR, WORK_END_HOUR

def get_kyiv_time() -> datetime:

    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=3)))

def is_working_hours() -> bool:

    now = get_kyiv_time()

    return WORK_START_HOUR <= now.hour < WORK_END_HOUR

def get_closed_message() -> str:

    return f'😴 <b>Наразі ми зачинені.</b>\n\nНаші робочі години: з {WORK_START_HOUR:02d}:00 до {WORK_END_HOUR:02d}:00.\nБудемо раді бачити вас в робочий час! ☕️'
