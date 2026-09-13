"""测试天气 MCP Server"""
import pytest
from fastmcp import Client

from app.mcp_core.servers.weather_server import mcp


@pytest.mark.asyncio
async def test():

    async with Client(mcp) as client:

        print("=== 测试西安天气（adcode: 610100）===")

        result = await client.call_tool(
            "get_weather_forecast",
            {"city_adcode": "610100"}
        )

        print(result.data)


        print("\n=== 测试北京天气（adcode: 110000）===")

        result = await client.call_tool(
            "get_weather_forecast",
            {"city_adcode": "110000"}
        )

        print(result.data)