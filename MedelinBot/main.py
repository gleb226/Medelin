
import asyncio

import logging

from aiogram import Dispatcher

from aiogram.fsm.storage.memory import MemoryStorage

from fastapi import FastAPI

import uvicorn

from contextlib import asynccontextmanager

from app.common.bot_instance import bot

from app.handlers.user_handlers import user_router

from app.handlers.admin_handlers import admin_router

from app.handlers.order_handlers import order_router

from app.handlers.error_handler import error_router

from app.utils.scheduler import start_scheduler

from app.utils.data_cache import public_data_cache

from api import app as fastapi_app

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

dp = Dispatcher(storage=MemoryStorage())

dp.include_router(user_router)

dp.include_router(admin_router)

dp.include_router(order_router)

dp.include_router(error_router)

async def run():

    @asynccontextmanager
    async def merged_lifespan(app: FastAPI):
        logger.info("Starting Medelin system (Bot + API + Cache)...")
        
        # 1. Warm cache
        cache_task = asyncio.create_task(public_data_cache.warm_all(max_retries=3))
        
        async def polling_with_retry():
            while True:
                try:
                    logger.info("Starting Telegram Bot polling...")
                    await bot.delete_webhook(drop_pending_updates=True)
                    await dp.start_polling(bot, handle_signals=False, allowed_updates=dp.resolve_used_update_types())
                    logger.warning("Polling finished normally. Restarting...")
                except Exception as e:
                    logger.error(f"Polling error: {e}. Restarting in 10 seconds...")
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    logger.info("Polling task cancelled.")
                    break

        polling_task = asyncio.create_task(polling_with_retry())
        
        # 3. Start Scheduler
        start_scheduler()
        
        yield
        
        logger.info("Shutting down Medelin system...")
        polling_task.cancel()
        cache_task.cancel()
        try:
            await asyncio.gather(polling_task, cache_task, return_exceptions=True)
        except Exception:
            pass
        await bot.session.close()

    # Apply the merged lifespan to the FastAPI app
    fastapi_app.router.lifespan_context = merged_lifespan

    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")

    server = uvicorn.Server(config)

    await server.serve()

if __name__ == "__main__":

    asyncio.run(run())
