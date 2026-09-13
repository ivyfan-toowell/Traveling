import asyncio
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from typing import Optional
from app.config import settings
from app.utils.logger import app_logger


class CheckpointerManager:

    _instance: Optional["CheckpointerManager"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.pool:Optional[AsyncConnectionPool] = None
        self.checkpointer:Optional[AsyncPostgresSaver] = None

    @classmethod
    async def get_instance(cls) -> "CheckpointerManager":
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance.initialize()

        return cls._instance

    async def initialize(self):
        if self.checkpointer is not None:
            app_logger.warning("⚠️ Checkpointer 先已初始化！")
            return

        try:
            app_logger.info("正在初始化 PostgreSQLCheckpointer...")

            self.pool = AsyncConnectionPool(
                conninfo = settings.database_url,
                min_size=2,
                max_size=20,
                timeout=30,
                open=False,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                },
            )

            await self.pool.open()

            self.checkpointer = AsyncPostgresSaver(self.pool)

            app_logger.info("✅️ Checkpointer 初始化已完成！")

        except Exception as e:
            app_logger.error(f"❌️ Checkpointer 初始化失败：{e}")
            raise

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.checkpointer = None
            app_logger.info("Checkpointer 连接池已关闭")

    def get_checkpointer(self) -> AsyncPostgresSaver:
        if self.checkpointer is None:
            raise RuntimeError("Checkpointer 未初始化，请先调用initialize()")
        return self.checkpointer

async def get_checkpointer() -> AsyncPostgresSaver:
    manager = await CheckpointerManager.get_instance()
    return manager.get_checkpointer()

@asynccontextmanager
async def checkpointer_lifespan():
    manager = await CheckpointerManager.get_instance()
    try:
        yield manager.get_checkpointer()
    finally:
        await manager.close()






































