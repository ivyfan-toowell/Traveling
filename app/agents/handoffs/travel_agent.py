"""
Handoffs 主 Agent
一个 Agent + 中间件实现整个旅行规划流程
"""
import asyncio
from typing import Any, Optional

from app.tools.mcp_tools import get_all_mcp_tools
from app.tools.router_query import query_destination_info
from app.tools.transport_query import query_transport_options
from langchain.agents import create_agent
from app.config import settings
from app.core.state import TravelState
from app.core.checkpointer import get_checkpointer
from langchain_openai import ChatOpenAI
from app.core.middleware import create_step_config_middleware
from app.tools.state_transition import (
    record_requirement_tool,
    select_destination_tool,
    select_transport_tool,
    select_accommodation_tool,
    select_food_tool,
    generate_itinerary_tool,
    summarize_budget_tool,
    generate_report_tool,
    ALL_ROLLBACK_TOOLS
)
from app.utils.logger import app_logger

_travel_agent: Optional[Any] = None
_travel_agent_lock = asyncio.Lock()


def _deduplicate_tools(tools: list[Any]) -> list[Any]:
    """De-duplicate agent tools by the name LangChain uses for dispatch."""
    tools_by_name: dict[str, Any] = {}
    for tool in tools:
        name = getattr(tool, "name", None)
        if not name:
            raise ValueError("Agent 工具缺少 name")
        tools_by_name.setdefault(name, tool)
    return list(tools_by_name.values())

# ============== 初始化 LLM ==============

def get_llm():
    """获取配置好的千问模型"""
    return ChatOpenAI(
        model=settings.qwen_model_name,
        base_url=settings.qwen_base_url,
        api_key=settings.dashscope_api_key,
        temperature=settings.qwen_temperature,
        max_tokens=settings.qwen_max_tokens,
        streaming=True
    )


# ============== 创建 Agent ==============

async def create_travel_agent():
    """
    创建 Handoffs 旅行规划 Agent

    返回：
        编译好的 Agent（可直接调用）
    """

    global _travel_agent

    if _travel_agent is not None:
        return _travel_agent

    async with _travel_agent_lock:
        if _travel_agent is not None:
            return _travel_agent

        app_logger.info("创建 Travel Agent（带审批）...")

        llm = get_llm()
        all_mcp_tools = await get_all_mcp_tools()

        # 异步创建中间件（预加载配置）
        step_config_middleware = await create_step_config_middleware()
        checkpointer = await get_checkpointer()

        base_tools = [
            record_requirement_tool,
            select_destination_tool,
            select_transport_tool,
            select_accommodation_tool,
            select_food_tool,
            generate_itinerary_tool,
            summarize_budget_tool,
            generate_report_tool,
            *ALL_ROLLBACK_TOOLS,
            query_destination_info,
            query_transport_options,
            *all_mcp_tools,
        ]

        # Middleware may expose a different subset at each planning step.
        # Every possible step tool must also be registered on the base agent;
        # otherwise LangChain raises "Middleware returned unknown tool names"
        # before the model can answer.
        all_tools = _deduplicate_tools([
            *step_config_middleware.get_configured_tools(),
            *base_tools,
        ])

        _travel_agent = create_agent(
            model=llm,
            tools=all_tools,
            state_schema=TravelState,
            middleware=[step_config_middleware],
            checkpointer=checkpointer,
        )

        app_logger.info("✅ Travel Agent（带持久化状态）创建完成")

        return _travel_agent
