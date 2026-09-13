
"""
app/main.py
FastAPI 应用入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.logger import app_logger
from app.api.v1 import conversations, chat, users
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import asyncio

    # 打印当前事件循环信息（调试用）
    loop = asyncio.get_running_loop()
    app_logger.info(f"FastAPI 使用的事件循环: {type(loop).__name__}")

    from app.core.checkpointer import checkpointer_lifespan
    from app.core.store import store_lifespan
    from app.mcp_core.client import MCPClientManager

    app_logger.info("🚀 启动应用...")

    async with checkpointer_lifespan():
        app_logger.info("✅ Checkpointer 已就绪")

        # 启动 Store (在这里加入)
        async with store_lifespan():
            app_logger.info("✅ Store 已就绪")

            # 初始化 MCP 服务
            mcp = await MCPClientManager.get_instance()
            app_logger.info("✅ MCP 服务初始化成功")

            yield
            # --- 关闭流程 (自动按相反顺序执行 context manager 的 exit，这里手动关闭 MCP) ---
            await mcp.close()
            app_logger.info("MCP 服务已关闭")

    # store_lifespan 的 exit 会在这里自动执行

    # checkpointer_lifespan 的 exit 会在这里自动执行

    app_logger.info("🛑 关闭应用...")


app = FastAPI(
    title="旅行规划系统",
    description="企业级多 Agent 旅行规划服务",
    version="1.0.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(users.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "service": "Travel Planner",
        "docs": "/docs",
        "status": "healthy",
        "version": "1.0.0"
    }
