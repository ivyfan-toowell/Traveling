"""
航班查询 Subagent
调用 Aviation MCP 的多个工具
"""
import asyncio
from langchain_community.chat_models import ChatTongyi
from langchain.agents import create_agent
from app.config import settings
from app.mcp_core.client import get_mcp_client
from app.tools.date_tools import get_today_date
from app.utils.logger import app_logger


async def _get_aviation_tools():
    """获取航班相关的MCP工具"""
    manager = await get_mcp_client()
    all_tools = await manager.get_tools()

    # 筛选航班工具
    aviation_tools = [
        tool for tool in all_tools
        if any(keyword in tool.name.lower() for keyword in [
            'flight', 'aviation', 'searchflights'
        ])
    ]

    aviation_tools.append(get_today_date)

    app_logger.info(f"✈️ 航班工具: {[t.name for t in aviation_tools]}")
    return aviation_tools


async def create_flight_subagent():
    """创建航班查询 Subagent"""

    llm = ChatTongyi(
        model=settings.qwen_model_name,
        api_key=settings.dashscope_api_key,
        temperature=0.1
    )

    # 异步获取工具
    aviation_tools = await _get_aviation_tools()

    agent = create_agent(
        model=llm,
        tools=aviation_tools,
        system_prompt="""你是航班查询专家，负责处理航班查询、机票价格比较及航班状态查询。可以使用以下工具：

**可用工具**：
1.  **日期与基础信息**：
    - `getTodayDate`: 获取今天日期（用于用户提供相对日期时）

2.  **航班查询（核心）**：
    - `searchFlightsByDepArr`: 按出发/到达城市查询航班（需IATA三字码）
    - `searchFlightsByNumber`: 按航班号查询航班信息
    - `getFlightTransferInfo`: 查询中转航班信息
    - `searchFlightItineraries`: 查询可购买航班行程和最低价

**IATA三字码示例**：
- 城市码：北京=BJS, 上海=SHA, 广州=CAN, 西安=XIY, 成都=CTU
- 机场码：首都机场=PEK, 浦东=PVG, 虹桥=SHA

**工作流程**：
1. 分析用户查询，提取出发地、目的地、日期
2. 如果用户说"明天"等相对日期，先调用getTodayDate获取今天日期
3. 如果查询城市有多个机场，使用depcity/arrcity参数
4. 如果查询具体机场，使用dep/arr参数

**输出格式**：
✈️ 航班 {航班号}
- 出发：{机场} {时间}
- 到达：{机场} {时间}
- 价格：¥{价格}

**注意**：
- 一定要调用工具，不要编造数据
- 日期格式必须是YYYY-MM-DD
- 如果没找到航班，明确告知用户
"""
    )

    app_logger.info("✅ 航班 Subagent 创建完成")
    return agent


if __name__ == "__main__":
    async def main():
        print("\n" + "=" * 50)
        print("🚀 正在初始化航班查询 Subagent...")
        print("=" * 50)

        flight_agent = await create_flight_subagent()

        test_query = "帮我查一下明天从北京到上海的航班"

        print(f"\n❓ 用户提问: {test_query}")
        print("-" * 30)

        response = await flight_agent.ainvoke({
            "messages": [{"role": "user", "content": test_query}]
        })

        print("-" * 30)
        print("✅ Agent 回复:")
        final_message = response["messages"][-1].content
        print(final_message)

        print("\n" + "=" * 50)
        print("测试结束")
        print("=" * 50)


    asyncio.run(main())
