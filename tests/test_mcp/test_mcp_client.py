"""测试 MCP 客户端"""
import pytest
import json
from app.mcp_core.client import MCPClientManager


@pytest.fixture(autouse=True)
def reset_singleton():
    """每个测试前重置单例"""
    MCPClientManager.reset_instance()
    yield
    MCPClientManager.reset_instance()


@pytest.mark.asyncio
async def test_print_mcp_tools():
    """测试打印所有 MCP 工具"""

    print("\n" + "=" * 60)
    print("🚀 正在初始化 MCP 客户端管理器...")

    manager = await MCPClientManager.get_instance(
        servers=["weather", "search", "amap", "12306-mcp","VariFlight-Aviation","aigohotel-mcp"]
    )

    try:
        # 获取所有工具
        tools = await manager.get_tools()

        print(f"✅ 连接成功！共发现 {len(tools)} 个工具")
        print("=" * 60)

        # 打印工具详情
        for i, tool in enumerate(tools, 1):
            print(f"🛠️  工具 [{i}]")
            print(f"📌 名称: {tool.name}")
            print(f"📝 描述: {tool.description}")
            print(f"⚙️  参数结构:")
            try:
                args = tool.args
            except Exception:
                args = tool.args_schema

            print(json.dumps(args, indent=2, ensure_ascii=False, default=str))

        assert len(tools) > 0, "应该至少有一个工具"

    finally:
        print("\n🔌 正在关闭连接...")
        await manager.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_print_mcp_tools())