"""
测试目的地 Router
"""
import pytest
import asyncio
from app.agents.routers.destination_router import create_destination_router

@pytest.mark.asyncio
async def test_explore_only():
    """测试只调用探索 Agent"""

    router = create_destination_router()

    result = await router.ainvoke({
        "original_query": "西安有什么好玩的景点？",
        "destination": "西安"
    })

    print("\n=== 测试：景点查询 ===")
    print(f"分类结果：{result['classifications']}")
    print(f"\n最终报告：\n{result['final_report']}")

    assert len(result['classifications']) == 1
    assert result['classifications'][0]['agent'] == 'explore'

    print("\n✅ 测试通过：仅调用探索 Agent")

@pytest.mark.asyncio
async def test_weather_only():
    """测试只调用天气 Agent"""

    router = create_destination_router()

    result = await router.ainvoke({
        "original_query": "西安现在天气怎么样？",
        "destination": "西安"
    })

    print("\n=== 测试：天气查询 ===")
    print(f"分类结果：{result['classifications']}")
    print(f"\n最终报告：\n{result['final_report']}")

    assert len(result['classifications']) == 1
    assert result['classifications'][0]['agent'] == 'weather'

    print("\n✅ 测试通过：仅调用天气 Agent")

@pytest.mark.asyncio
async def test_both_agents():
    """测试并行调用两个 Agent"""

    router = create_destination_router()

    result = await router.ainvoke({
        "original_query": "推荐西安旅游",
        "destination": "西安"
    })

    print("\n=== 测试：综合查询 ===")
    print(f"分类结果：{result['classifications']}")
    print(f"\n最终报告：\n{result['final_report']}")

    assert len(result['classifications']) == 2
    assert {c['agent'] for c in result['classifications']} == {'explore', 'weather'}

    print("\n✅ 测试通过：并行调用两个 Agent")


if __name__ == "__main__":
    asyncio.run(test_explore_only())
    asyncio.run(test_weather_only())
    asyncio.run(test_both_agents())