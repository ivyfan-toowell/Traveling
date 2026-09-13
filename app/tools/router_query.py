"""
Router 查询工具
"""
from langchain.tools import tool
from app.agents.routers.destination_router import create_destination_router
from app.utils.logger import app_logger


@tool
async def query_destination_info(destination: str, query: str = "") -> str:
    """
    查询目的地详细信息（并行查询多个源）

    此工具会调用 Router，并行执行：
    1. 探索 Agent：从 RAG 系统检索景点攻略
    2. 天气 Agent：查询实时天气信息

    参数：
    - destination: 目的地名称，如 "西安"
    - query: 具体查询（可选），如 "景点推荐"

    返回：
    - 综合的目的地信息（景点 + 天气）
    """

    app_logger.info(f"调用目的地 Router: {destination}")

    # 创建 Router
    router = create_destination_router()

    # 如果没有提供具体查询，使用默认
    if not query:
        query = f"推荐{destination}旅游"

    # 调用 Router
    result = await router.ainvoke({
        "original_query": query,
        "destination": destination
    })

    # 返回综合报告
    return result["final_report"]