"""
数据库初始化脚本
"""

import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore
from app.config import settings
from app.utils.logger import app_logger
from app.models.base import init_db

async def init_database():
    """初始化所有数据库表"""

    db_url = settings.database_url
    app_logger.info(f"连接数据库：{settings.postgres_host}：{settings.postgres_port}/{settings.postgres_db}")

    try:
        # 1. 初始化业务表（用户、会话、消息）在第九章会使用
        app_logger.info("初始化业务表...")
        await init_db()
        app_logger.info("✅ 业务表创建成功")

        # 2. 初始化 LangGraph Checkpointer 表
        async with AsyncConnectionPool(conninfo=db_url,min_size=2,max_size=10) as pool:
            app_logger.info("初始化Checkpointer表...")
            async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
                await checkpointer.setup()
            app_logger.info("✅ Checkpointer 表创建成功")

            app_logger.info("初始化Store表...")
            async with AsyncPostgresStore.from_conn_string(db_url) as store:
                await store.setup()
            app_logger.info("✅ Store 表创建成功")

            app_logger.info("启用pgvector扩展...")
            async with pool.connection() as conn:   #从连接池中拿出一个数据库连接作为变量
                async with conn.cursor() as cur:    #cur负责在连接上执行SQL
                    await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;") # cur.execute()执行SQL
                    await conn.commit()
                app_logger.info("✅ pgvector 扩展启用成功")

        app_logger.info("数据库初始化完成啦！")

    except Exception as e:
        app_logger.error(f"❌ 数据库初始化失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(init_database())






























