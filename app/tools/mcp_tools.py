"""
MCP 工具筛选器
按需获取特定类型的 MCP 工具
"""
from typing import List
from langchain_core.tools import BaseTool
from app.mcp_core.client import get_mcp_client
from app.tools.date_tools import get_current_date, get_today_date
from app.utils.logger import app_logger


async def get_all_mcp_tools() -> List[BaseTool]:
    """获取所有 MCP 工具"""
    manager = await get_mcp_client()
    tools = await manager.get_tools()
    app_logger.info(f"📦 获取了 {len(tools)} 个 MCP 工具")
    return tools


async def get_hotel_tools() -> List[BaseTool]:
    """
    获取酒店相关工具

    Returns:
        酒店搜索、周边查询等工具
    """
    manager = await get_mcp_client()
    all_tools = await manager.get_tools()

    hotel_tools = [
        tool for tool in all_tools
        if any(keyword in tool.name.lower() for keyword in [
            'find-hotels',           # 酒店搜索
            'maps_around_search',    # 周边POI搜索（找附近餐厅等）
        ])
    ]

    app_logger.info(f"🏨 酒店工具: {[t.name for t in hotel_tools]}")
    return hotel_tools


async def get_weather_tools() -> List[BaseTool]:
    """
    获取天气相关工具

    Returns:
        天气查询工具
    """
    manager = await get_mcp_client()
    all_tools = await manager.get_tools()

    weather_tools = [
        tool for tool in all_tools
        if any(keyword in tool.name.lower() for keyword in [
            'get_weather_forecast',      # 自建天气服务
        ])
    ]

    app_logger.info(f"🌤️ 天气工具: {[t.name for t in weather_tools]}")
    return weather_tools


async def get_search_tools() -> List[BaseTool]:
    """
    获取搜索相关工具

    Returns:
        旅游信息搜索工具
    """
    manager = await get_mcp_client()
    all_tools = await manager.get_tools()

    search_tools = [
        tool for tool in all_tools
        if any(keyword in tool.name.lower() for keyword in [
            'search_travel_info',  # 自建搜索服务
        ])
    ]

    app_logger.info(f"🔍 搜索工具: {[t.name for t in search_tools]}")
    return search_tools


async def get_date_tools() -> List[BaseTool]:
    """获取不依赖外部 MCP 的本地日期工具。"""
    date_tools = [get_current_date, get_today_date]
    app_logger.info(f"📅 本地日期工具: {[t.name for t in date_tools]}")
    return date_tools
