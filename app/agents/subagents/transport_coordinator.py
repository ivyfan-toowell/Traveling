#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/1/7 16:16
@Author  : GGBOND
@File    : transport_coordinator.py
@Software: PyCharm
"""
"""
交通规划协调器（主 Agent）
整合三个 Subagents + 辅助工具
"""
import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from langchain_community.chat_models import ChatTongyi
from langchain.agents import create_agent
from langchain.tools import tool
from app.config import settings
from app.agents.subagents.flight_agent import create_flight_subagent
from app.agents.subagents.train_agent import create_train_subagent
from app.agents.subagents.driving_agent import create_driving_subagent
from app.mcp_core.client import get_mcp_client
from app.tools.date_tools import get_current_date
from app.utils.logger import app_logger


# ============== 获取辅助工具 ==============

async def _get_auxiliary_tools():
    """获取辅助工具"""
    manager = await get_mcp_client()
    all_tools = await manager.get_tools()

    # 筛选辅助工具
    aux_tools = [
        tool for tool in all_tools
        if any(keyword in tool.name.lower() for keyword in [
            'getfutureweather',
            'maps_around_search'
        ])
    ]

    aux_tools.append(get_current_date)

    app_logger.info(f"🛠️ 辅助工具: {[t.name for t in aux_tools]}")
    return aux_tools


# ============== 创建交通规划主 Agent ==============

async def create_transport_coordinator():
    """
    创建交通规划协调器（主 Agent）

    整合：
    - 3个子Agent工具（航班、高铁、自驾）
    - MCP辅助工具（酒店、天气、日期、周边搜索）
    """

    llm = ChatTongyi(
        model=settings.qwen_model_name,
        api_key=settings.dashscope_api_key,
        temperature=0.7
    )

    # 异步创建子Agents
    flight_subagent = await create_flight_subagent()
    train_subagent = await create_train_subagent()
    driving_subagent = await create_driving_subagent()

    # ============== 将 Subagents 包装为 Tools ==============

    @tool("query_flights", description="查询航班信息。需要提供出发城市、目的地城市、出发日期。")
    async def query_flights_tool(
        origin: str,
        destination: str,
        departure_date: str
    ) -> str:
        """查询航班信息（调用航班 Subagent）"""

        app_logger.info(f"🔧 调用航班 Subagent: {origin} -> {destination}")

        try:
            result = await asyncio.wait_for(
                flight_subagent.ainvoke({
                    "messages": [{
                        "role": "user",
                        "content": f"请查询从 {origin} 到 {destination} 的航班，出发日期是 {departure_date}。"
                    }]
                }),
                timeout=60,
            )
            return result["messages"][-1].content
        except asyncio.TimeoutError:
            return "实时航班查询超过 60 秒未返回。请稍后重试，或先按常见航班时段规划。"
        except Exception as exc:
            app_logger.exception("航班 Subagent 查询失败")
            return f"实时航班服务暂时不可用（{type(exc).__name__}），请稍后重试。"

    @tool("query_trains", description="查询高铁/火车信息。需要提供出发城市、目的地城市、出发日期。")
    async def query_trains_tool(
        origin: str,
        destination: str,
        departure_date: str
    ) -> str:
        """查询高铁信息（调用高铁 Subagent）"""

        app_logger.info(f"🔧 调用高铁 Subagent: {origin} -> {destination}")

        try:
            travel_date = date.fromisoformat(departure_date)
        except (TypeError, ValueError):
            return "出发日期格式无效，请使用 YYYY-MM-DD，例如 2026-09-30。"

        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        if travel_date < today:
            return f"{departure_date} 已经过去，请提供今天之后的出发日期。"

        if travel_date > today + timedelta(days=15):
            return (
                f"{departure_date} 尚未进入 12306 的近期预售查询窗口，"
                "目前无法取得可靠的实时车次和余票。可以先规划出发车站、直达偏好和大致时段，"
                "临近出发时再查询实际班次；预售天数请以 12306 最新规则为准。"
            )

        try:
            result = await asyncio.wait_for(
                train_subagent.ainvoke({
                    "messages": [{
                        "role": "user",
                        "content": f"请查询从 {origin} 到 {destination} 的高铁，出发日期是 {departure_date}。"
                    }]
                }),
                timeout=60,
            )
            return result["messages"][-1].content
        except asyncio.TimeoutError:
            return "12306 实时查询超过 60 秒未返回。请稍后重试，或先按非实时信息规划。"
        except Exception as exc:
            app_logger.exception("高铁 Subagent 查询失败")
            return (
                f"12306 实时查询暂时失败（{type(exc).__name__}）。"
                "这不会中断旅行规划，可以先确认高铁偏好，稍后再查询余票。"
            )

    @tool("plan_driving_route", description="规划自驾路线。需要提供出发地和目的地（地址或地名）。")
    async def plan_driving_route_tool(
        origin: str,
        destination: str
    ) -> str:
        """规划自驾路线（调用自驾 Subagent）"""

        app_logger.info(f"🔧 调用自驾 Subagent: {origin} -> {destination}")

        try:
            result = await asyncio.wait_for(
                driving_subagent.ainvoke({
                    "messages": [{
                        "role": "user",
                        "content": f"请规划从 {origin} 到 {destination} 的自驾路线。"
                    }]
                }),
                timeout=60,
            )
            return result["messages"][-1].content
        except asyncio.TimeoutError:
            return "实时自驾路线规划超过 60 秒未返回，请稍后重试。"
        except Exception as exc:
            app_logger.exception("自驾 Subagent 查询失败")
            return f"实时地图服务暂时不可用（{type(exc).__name__}），请稍后重试。"

    # 获取辅助工具
    auxiliary_tools = await _get_auxiliary_tools()

    # 组合所有工具
    all_tools = [
        query_flights_tool,
        query_trains_tool,
        plan_driving_route_tool,
    ] + auxiliary_tools

    coordinator = create_agent(
        model=llm,
        tools=all_tools,
        system_prompt="""你是交通规划协调专家。

**可用工具**：

**交通查询（主要）**：
1. query_flights：查询航班信息（适合长途，速度快）
2. query_trains：查询高铁信息（适合中短途，舒适便捷）
3. plan_driving_route：规划自驾路线（适合深度游，自由灵活）

**辅助工具（按需使用）**：
- getFutureWeatherByAirport：查询机场未来天气
- get-current-date：获取今天日期（调用需要时间的工具前,获取实时时间）

**工作流程**：
1. 理解用户的交通需求（出发地、目的地、日期、人数）
2. 如果用户明确指定交通方式，直接调用对应工具
3. 如果用户未指定，根据距离推荐：
   * < 300km：推荐高铁
   * 300-1000km：推荐高铁或航班
   * > 1000km：推荐航班
4. 调用工具后，用清晰格式展示结果
5. 可以主动询问用户偏好（时间优先还是价格优先）

**注意事项**：
- 用户说的今天和明天之类的词要以get-current-date获取的时间为标准
- 一定要调用工具获取实时信息，不要编造数据
- 如果查询失败，告知用户并提供替代方案
- 航班和高铁需要提供日期，自驾不需要
- 调用工具前，先调用get-current-date获取今天日期
"""
    )

    app_logger.info("✅ 交通规划协调器（主 Agent）创建完成")

    return coordinator


if __name__ == "__main__":
    async def main():
        print("\n" + "=" * 50)
        print("🚀 正在初始化交通规划协调器...")
        print("=" * 50)

        coordinator = await create_transport_coordinator()

        test_query = "我想从北京去上海，明天出发，帮我推荐交通方式"

        print(f"\n❓ 用户提问: {test_query}")
        print("-" * 30)

        response = await coordinator.ainvoke({
            "messages": [{"role": "user", "content": test_query}]
        })

        print("-" * 30)
        print("✅ 协调器回复:")
        final_message = response["messages"][-1].content
        print(final_message)

        print("\n" + "=" * 50)
        print("测试结束")
        print("=" * 50)

    asyncio.run(main())
