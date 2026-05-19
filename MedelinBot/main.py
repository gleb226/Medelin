
import asyncio

import logging

from aiogram import Bot, Dispatcher

from aiogram.fsm.storage.memory import MemoryStorage

from fastapi import FastAPI

import uvicorn

from contextlib import asynccontextmanager

from app.common.config import BOT_TOKEN

from app.handlers.user_handlers import user_router

from app.handlers.admin_handlers import admin_router

from app.handlers.order_handlers import order_router

from app.handlers.error_handler import error_router

from app.utils.scheduler import start_scheduler

from api import app as fastapi_app

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher(storage=MemoryStorage())

dp.include_router(user_router)

dp.include_router(admin_router)

dp.include_router(order_router)

dp.include_router(error_router)

@asynccontextmanager

async def lifespan(app: FastAPI):

    logger.info("Starting Telegram Bot polling...")

    polling_task = asyncio.create_task(dp.start_polling(bot))

    start_scheduler()

    yield

    logger.info("Stopping Telegram Bot polling...")

    polling_task.cancel()

    try:

        await polling_task

    except asyncio.CancelledError:

        pass

    await bot.session.close()

async def run():

    from app.utils.data_cache import public_data_cache

    @asynccontextmanager

    async def merged_lifespan(app: FastAPI):

        logger.info("Starting Bot and warming cache...")

        cache_task = asyncio.create_task(public_data_cache.warm_all(max_retries=3))

        polling_task = asyncio.create_task(dp.start_polling(bot))

        start_scheduler()

        yield

        logger.info("Shutting down...")

        polling_task.cancel()

        cache_task.cancel()

        try:

            await asyncio.gather(polling_task, cache_task, return_exceptions=True)

        except Exception:

            pass

        await bot.session.close()

    fastapi_app.router.lifespan_context = merged_lifespan

    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")

    server = uvicorn.Server(config)

    await server.serve()

if __name__ == "__main__":

    asyncio.run(run())
