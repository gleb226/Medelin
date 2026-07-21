
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger_stdout = logging.getLogger('activity')

class Logger:

    async def connect(self):
        pass

    async def close(self):
        return

    async def log_activity(self, user_id: int, username: str, action: str, details: str=''):
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] User: {user_id} (@{username or '—'}) | Action: {action} | Details: {details}"
        print(log_msg)
        logger_stdout.info(log_msg)

logger = Logger()

async def log_activity(user_id: int, username: str, action: str, details: str=''):

    await logger.log_activity(user_id, username, action, details)
