
from datetime import datetime

from app.databases.mongo_client import get_db

class Logger:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def log_activity(self, user_id: int, username: str, action: str, details: str=''):

        db = await get_db()

        await db.activity_logs.insert_one({'user_id': int(user_id), 'username': username, 'action': action, 'details': details, 'timestamp': datetime.utcnow()})

logger = Logger()

async def log_activity(user_id: int, username: str, action: str, details: str=''):

    await logger.log_activity(user_id, username, action, details)
