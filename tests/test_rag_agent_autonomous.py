"""
测试 Agent 自主调用 RAG 工具
"""
import pytest
import asyncio
from langchain_community.chat_models import ChatTongyi
from langchain.agents import create_agent
from app.config import settings
from app.tools.rag_tools import get_rag_tools

@pytest.mark.asyncio
async def test_agent_autonomous_rag():
    """测试 Agent 自主决定是否调用 RAG 工具"""

    print("\n" + "=" * 60)
    print("测试 Agent 自主调用 RAG 工具")
    print("=" * 60)

    # 创建 LLM
    llm = ChatTongyi(
        model=settings.qwen_model_name,
        api_key=settings.dashscope_api_key,
        temperature=0.7
    )

    # 获取 RAG 工具
    rag_tools = get_rag_tools()
    print(f"\n已加载 {len(rag_tools)} 个 RAG 工具:")
    for tool in rag_tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")

    # 创建 Agent
    agent = create_agent(
        model=llm,
        tools=rag_tools,
        system_prompt="""你是一位专业的旅行顾问。
你有多个工具可以从知识库检索信息。
根据用户的问题，自主决定是否需要调用工具。
如果问题需要具体的旅游信息，就调用工具；
如果是简单的问题，直接回答即可。"""
    )

    # 测试用例
    test_cases = [
        # 1. 应该调用 RAG 工具
        "西安兵马俑的门票多少钱？有什么游玩建议？",

        # 2. 应该调用 RAG 工具
        "成都有什么必吃的美食？",

        # 3. 可能不需要调用工具（简单问候）
        "你好，我想规划一次旅行",

        # 4. 应该调用多个工具
        "我想去西安，帮我介绍一下景点、美食和住宿建议",
    ]

    for i, query in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}: {query}")
        print("=" * 60)

        response = await agent.ainvoke({
            "messages": [{"role": "user", "content": query}]
        })

        # 打印 Agent 的回复
        print(f"\nAgent 回复:\n{response['messages'][-1].content}")

        # 检查是否调用了工具
        tool_calls = [
            msg for msg in response["messages"]
            if hasattr(msg, "tool_calls") and msg.tool_calls
        ]

        if tool_calls:
            print(f"\n📋 Agent 调用了以下工具:")
            for msg in tool_calls:
                for tc in msg.tool_calls:
                    print(f"  - {tc['name']}: {tc['args']}")
        else:
            print("\n📋 Agent 没有调用任何工具（直接回答）")

    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)

@pytest.mark.asyncio
async def test_router_with_autonomous_rag():
    """测试 Router 中的探索 Agent 自主调用 RAG"""

    print("\n" + "=" * 60)
    print("测试 Router + 自主 RAG")
    print("=" * 60)

    from app.agents.routers.destination_router import create_destination_router

    router = create_destination_router()

    result = await router.ainvoke({
        "original_query": "推荐西安旅游，告诉我景点和美食",
        "destination": "西安"
    })

    print(f"\n分类结果: {result['classifications']}")
    print(f"\n最终报告:\n{result['final_report']}")

    print("\n✅ Router 测试完成!")


if __name__ == "__main__":
    asyncio.run(test_agent_autonomous_rag())
    asyncio.run(test_router_with_autonomous_rag())