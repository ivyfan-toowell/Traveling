"""测试搜索 MCP Server"""
import pytest
import asyncio
from app.mcp_core.servers.search_server import search_travel_info

@pytest.mark.asyncio
async def test():
    print("=== 测试景点搜索 ===")
    result = await search_travel_info.fn("西安必去景点推荐")
    print(result)

    print("\n=== 测试美食搜索 ===")
    result = await search_travel_info.fn("西安特色美食小吃", 3)
    print(result)


if __name__ == "__main__":
    asyncio.run(test())