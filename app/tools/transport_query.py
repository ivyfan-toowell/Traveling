"""
交通查询工具
调用交通规划协调器（Subagents 主 Agent）
"""
import asyncio

from langchain.tools import tool
from app.agents.subagents.transport_coordinator import create_transport_coordinator
from app.utils.logger import app_logger


@tool
async def query_transport_options(
        origin_city: str,
        destination_city: str,
        departure_date: str,
        transport_type: str = None
) -> str:
    """
    查询交通选项（调用交通规划协调器）

    参数说明：
    - origin_city: 出发城市
    - destination_city: 目的地城市
    - departure_date: 出发日期，格式 YYYY-MM-DD
    - transport_type: 交通方式（可选），可选值：flight（航班）、train（高铁）、driving（自驾）

    返回：
    - 格式化的交通选项信息
    """

    app_logger.info(f"🔧 调用交通规划协调器")

    # 异步创建协调器（主 Agent）
    coordinator = await create_transport_coordinator()

    # 构建用户查询
    if transport_type:
        type_labels = {
            "flight": "航班",
            "train": "高铁",
            "driving": "自驾"
        }
        user_query = (
            f"我想从 {origin_city} 去 {destination_city}，"
            f"出发日期是 {departure_date}，"
            f"交通方式选择 {type_labels.get(transport_type, transport_type)}，"
            f"请帮我查询详细信息。"
        )
    else:
        user_query = (
            f"我想从 {origin_city} 去 {destination_city}，"
            f"出发日期是 {departure_date}，"
            f"请推荐合适的交通方式并提供详细信息。"
        )

    # 调用协调器
    try:
        result = await asyncio.wait_for(
            coordinator.ainvoke({
                "messages": [{"role": "user", "content": user_query}]
            }),
            timeout=90,
        )
        return result["messages"][-1].content
    except asyncio.TimeoutError:
        app_logger.warning("交通规划协调器查询超时")
        return (
            "实时交通服务暂时没有在 90 秒内返回。"
            "我们可以先确认交通偏好并继续规划，稍后再补充具体班次和价格。"
        )
    except Exception as exc:
        app_logger.exception("交通规划协调器查询失败")
        return (
            f"实时交通查询暂时失败（{type(exc).__name__}）。"
            "这不会中断本次规划，可以先确认交通方式，稍后再补查实时信息。"
        )
