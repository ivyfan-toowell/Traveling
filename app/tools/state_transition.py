"""
状态转换工具
用于 Handoffs 流程中的步骤跳转和数据记录
"""
from datetime import datetime
from langchain.tools import tool, ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from app.core.state import (
    TravelState,
    UserRequirement,
    TravelStyle,
    BudgetLevel,
    TransportType,
    AccommodationType,
    FoodType
)
from app.utils.logger import app_logger
from typing import Literal, Optional


# ============== 1️.需求收集工具 ==============

@tool
def record_requirement_tool(
        departure_city: str,
        departure_date: str,
        travel_days: int,
        budget_min: float,
        budget_max: float,
        travel_styles: list[str],  # 传入字符串列表，工具内转换
        special_needs: str = "",
        adult_count: Optional[int] = 1,
        children_count: Optional[int] = 0,
        destination: Optional[str] = None,
        runtime: ToolRuntime[None, TravelState] = None
) -> Command:
    """
    记录用户旅行需求，并转换到目的地推荐步骤。

    参数(可为空)说明：
    - destination 目的地
    - departure_city 出发地
    - departure_date: 出发日期，格式 YYYY-MM-DD，如 "2025-08-01"
    - travel_days: 出行天数，如 5
    - adult_count: 成人数量
    - children_count: 儿童数量（< 12 岁）
    - budget_min: 预算下限（元/人）
    - budget_max: 预算上限（元/人）
    - travel_styles: 旅行风格列表，可选值：["relaxation", "culture", "adventure", "food"]
    - special_needs: 特殊需求（可选），如 "需要无障碍设施"
    """

    app_logger.info(f"记录用户需求: {departure_date}, {travel_days}天, 预算 {budget_min}-{budget_max}")

    adult_count = 1 if adult_count is None else adult_count
    children_count = 0 if children_count is None else children_count
    valid_styles = {"relaxation", "culture", "adventure", "food"}
    if (
        not departure_city.strip()
        or travel_days < 1
        or adult_count < 1
        or children_count < 0
        or budget_min < 0
        or budget_max < budget_min
        or not travel_styles
        or any(style not in valid_styles for style in travel_styles)
    ):
        return Command(update={
            "messages": [
                ToolMessage(
                    content="旅行需求参数无效，请确认出发城市、天数、人数、预算范围和旅行风格。",
                    tool_call_id=runtime.tool_call_id,
                )
            ]
        })

    # 验证日期格式
    try:
        datetime.strptime(departure_date, "%Y-%m-%d")
    except ValueError:
        return Command(update={
            "messages": [
                ToolMessage(
                    content="❌ 日期格式错误，请使用 YYYY-MM-DD 格式，如 2025-08-01",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })

    # 推断预算等级
    avg_budget = (budget_min + budget_max) / 2
    if avg_budget < 3000:
        budget_level = "economy"
    elif avg_budget < 8000:
        budget_level = "comfort"
    else:
        budget_level = "luxury"

    # 构建需求对象
    requirement = UserRequirement(
        departure_city=departure_city,
        destination=destination,
        departure_date=departure_date,
        travel_days=travel_days,
        adult_count=adult_count,
        children_count=children_count,
        budget_min=budget_min,
        budget_max=budget_max,
        budget_level=budget_level,
        travel_styles=travel_styles,
        special_needs=special_needs if special_needs else None
    )

    # 返回 Command：更新状态并跳转到下一步
    return Command(update={
        "messages": [
            ToolMessage(
                content=f"需求已记录！\n"
                        f"出发日期：{departure_date}\n"
                        f"{travel_days} 天 | {adult_count + children_count} 人\n"
                        f"预算：{budget_min}-{budget_max} 元/人（{budget_level}级）\n"
                        f"风格：{', '.join(travel_styles)}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "user_requirement": requirement,
        "current_step": "destination_recommendation"  # 跳转到步骤2
    })


# ============== 2️.目的地选择工具 ==============

@tool
def select_destination_tool(
        destination: str,
        runtime: ToolRuntime[None, TravelState] = None
) -> Command:
    """
    确认用户选择的目的地，并转换到交通规划步骤。

    参数说明：
    - destination: 目的地名称，如 "西安"、"成都"
    """

    app_logger.info(f"用户选择目的地: {destination}")

    destination = destination.strip()
    if not destination:
        return Command(update={
            "messages": [
                ToolMessage(
                    content="目的地不能为空，请重新确认。",
                    tool_call_id=runtime.tool_call_id,
                )
            ]
        })

    return Command(update={
        "messages": [
            ToolMessage(
                content=f"目的地已确认：{destination}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "selected_destination": destination,
        "current_step": "transport_planning"  # 跳转到步骤3
    })


# ============== 3️.交通方式选择工具 ==============

@tool
def select_transport_tool(
        transport_type: str,
        runtime: ToolRuntime[None, TravelState] = None
) -> Command:
    """
    确认用户选择的交通方式，并转换到住宿规划步骤。

    参数说明：
    - transport_type: 交通方式，可选值：flight（航班）、train（高铁）、driving（自驾）
    """

    app_logger.info(f"用户选择交通方式：{transport_type}")

    if transport_type not in ["flight", "train", "driving"]:
        return Command(update={
            "messages": [
                ToolMessage(
                    content = "❌️交通方式无效，请选择：flight、train 或 driving",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })
    transport_labels={
        "flight": "航班",
        "train": "高铁",
        "driving": "自驾"
    }

    return Command(update={
        "messages": [
            ToolMessage(
                content = f"交通方式已确认：{transport_labels[transport_type]}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "selected_transport": transport_type,
        "current_step": "accommodation_planning"
    })




# ============== 4️.住宿偏好选择工具 ==============

@tool
def select_accommodation_tool(
        accommodation_types: list[str], #可多选
        runtime: ToolRuntime[None, TravelState] = None
) -> Command:
    """
   确认用户选择的住宿偏好（可多选），并转换到餐饮规划步骤。

   参数说明：
   - accommodation_types: 住宿类型列表，可选值：
     ["star_hotel", "economy_hotel", "hostel", "youth_hostel"]
   """

    app_logger.info(f"用户选择住宿类型: {accommodation_types}")

    valid_types = {"star_hotel", "economy_hotel", "hostel", "youth_hostel"}
    if not accommodation_types or not all(t in valid_types for t in accommodation_types):
        return Command(update={
            "messages": [
                ToolMessage(
                    content = f"❌住宿类型无效，请从以下选择：{', '.join(valid_types)}",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })
    type_labels = {
        "star_hotel": "星级酒店",
        "economy_hotel": "经济酒店",
        "hostel": "特色民宿",
        "youth_hostel": "青年旅社"
    }

    selected_labels = [type_labels[t] for t in accommodation_types]

    return Command(update={
        "messages": [
            ToolMessage(
                content = f"住宿偏好已确认：{', '.join(selected_labels)}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "selected_accommodation_types": accommodation_types,
        "current_step": "food_planning"
    })

# ============== 5️.餐饮偏好选择工具 ==============

@tool
def select_food_tool(
        food_types: list[str],  # 可多选
        runtime: ToolRuntime[None, TravelState] = None
) -> Command:
    """
    确认用户选择的餐饮偏好（可多选），并转换到行程生成步骤。

    参数说明：
    - food_types: 餐饮类型列表，可选值：["specialty", "chain", "local"]
    """

    app_logger.info(f"用户选择餐饮类型: {food_types}")

    # 验证枚举值
    valid_types = {"specialty", "chain", "local"}
    if not food_types or not all(t in valid_types for t in food_types):
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"❌ 餐饮类型无效，请从以下选择：{', '.join(valid_types)}",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })

    type_labels = {
        "specialty": "🍽️ 特色美食",
        "chain": "🍔 连锁快餐",
        "local": "🥘 本地小吃"
    }

    selected_labels = [type_labels[t] for t in food_types]

    return Command(update={
        "messages": [
            ToolMessage(
                content=f"餐饮偏好已确认：{', '.join(selected_labels)}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "selected_food_types": food_types,
        "current_step": "itinerary_generation"  # 跳转到步骤6
    })


# ============== 6️.行程生成工具 ==============

@tool
def generate_itinerary_tool(
        itinerary: list[dict],
        runtime: ToolRuntime[None, TravelState] = None
) -> Command:
    """
    生成完整行程安排，并转换到预算汇总步骤。

    此工具会综合：
    - 用户需求（天数、人数、风格）
    - 目的地信息
    - 交通信息
    - 住宿信息
    - 餐饮信息

    生成详细的每日行程。
    """

    app_logger.info("开始生成行程...")

    state = runtime.state

    # 检查必要信息是否完整
    required_fields = [
        "user_requirement",
        "selected_destination",
        "selected_transport",
        "selected_accommodation_types",
        "selected_food_types"
    ]

    missing = [f for f in required_fields if f not in state or state[f] is None]
    if missing:
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"❌ 信息不完整，缺少：{', '.join(missing)}",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })

    travel_days = state["user_requirement"]["travel_days"]
    if len(itinerary) != travel_days:
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"行程必须包含 {travel_days} 天，目前收到 {len(itinerary)} 天。",
                    tool_call_id=runtime.tool_call_id,
                )
            ]
        })

    normalized_itinerary = []
    for day_number, day in enumerate(itinerary, 1):
        activities = day.get("activities") or []
        meals = day.get("meals") or []
        if not activities:
            return Command(update={
                "messages": [
                    ToolMessage(
                        content=f"第 {day_number} 天缺少活动安排，请补充后再确认。",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            })
        normalized_itinerary.append({
            "day_number": day_number,
            "activities": [str(item) for item in activities],
            "meals": [str(item) for item in meals],
            "accommodation": str(day.get("accommodation") or "待确认"),
        })

    return Command(update={
        "messages": [
            ToolMessage(
                content=f"已生成 {travel_days} 天详细行程！",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "itinerary": normalized_itinerary,
        "current_step": "budget_summarization"  # 跳转到步骤7
    })


# ============== 7️.预算汇总工具 ==============

@tool
def summarize_budget_tool(
        runtime: ToolRuntime[None, TravelState] = None
) -> Command:
    """
    汇总各项费用，生成预算明细，并转换到报告生成步骤。

    预算明细包括：
    - 交通费用
    - 住宿费用
    - 餐饮费用
    - 景点门票
    - 其他杂费
    """

    app_logger.info("开始计算预算...")

    state = runtime.state

    # 简化版计算（实际应基于查询结果）
    requirement = state["user_requirement"]
    total_people = requirement["adult_count"] + requirement["children_count"]
    travel_days = requirement["travel_days"]

    # 估算费用
    transport_cost = 500 * total_people  # 人均交通
    accommodation_cost = 300 * travel_days * total_people  # 人均住宿
    food_cost = 150 * travel_days * total_people  # 人均餐饮
    attractions_cost = 200 * travel_days * total_people  # 人均门票
    misc_cost = 100 * travel_days * total_people  # 人均杂费

    total_cost = transport_cost + accommodation_cost + food_cost + attractions_cost + misc_cost

    budget_breakdown = {
        "transport": transport_cost,
        "accommodation": accommodation_cost,
        "food": food_cost,
        "attractions": attractions_cost,
        "misc": misc_cost,
        "total": total_cost
    }

    return Command(update={
        "messages": [
            ToolMessage(
                content=f"预算汇总完成！\n"
                        f"总计：{total_cost:.2f} 元\n"
                        f"   - 交通：{transport_cost:.2f}\n"
                        f"   - 住宿：{accommodation_cost:.2f}\n"
                        f"   - 餐饮：{food_cost:.2f}\n"
                        f"   - 门票：{attractions_cost:.2f}\n"
                        f"   - 其他：{misc_cost:.2f}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "budget": budget_breakdown,
        "current_step": "report_generation"  # 跳转到步骤8
    })
























# ============== 8 报告生成工具 ==============

@tool
def generate_report_tool(
        runtime: ToolRuntime[None, TravelState] = None
) -> Command:
    """
    生成完整的旅行规划报告（Markdown 格式），完成整个旅行规划流程。

    报告包含：
    - 旅行概览
    - 详细行程安排
    - 预算明细
    - 行程流程图（Mermaid）
    - 注意事项
    """

    app_logger.info("📋 生成旅行报告...")

    state = runtime.state

    # 获取必要信息
    requirement = state.get("user_requirement", {})
    destination = state.get("selected_destination", "未知目的地")
    transport = state.get("selected_transport", "未知")
    accommodation = state.get("selected_accommodation_types", [])
    food_types = state.get("selected_food_types", [])
    itinerary = state.get("itinerary", [])
    budget = state.get("budget", {})

    # 交通方式映射
    transport_labels = {
        "flight": "✈️ 航班",
        "train": "🚄 高铁",
        "driving": "🚗 自驾"
    }
    transport_display = transport_labels.get(transport, transport)

    # 住宿类型映射
    accommodation_labels = {
        "star_hotel": "星级酒店",
        "economy_hotel": "经济酒店",
        "hostel": "特色民宿",
        "youth_hostel": "青年旅社"
    }
    accommodation_display = "、".join([accommodation_labels.get(a, a) for a in accommodation])

    # 餐饮类型映射
    food_labels = {
        "specialty": "特色美食",
        "chain": "连锁快餐",
        "local": "本地小吃"
    }
    food_display = "、".join([food_labels.get(f, f) for f in food_types])

    # 生成行程 Mermaid 流程图
    mermaid_steps = ["graph TD"]
    mermaid_steps.append(f"    A[🏠 出发] --> B[{transport_display}]")
    mermaid_steps.append(f"    B --> C[📍 抵达{destination}]")

    prev_node = "C"
    for i, day in enumerate(itinerary, 1):
        day_node = f"D{i}"
        activities = day.get("activities", [f"第{i}天活动"])
        activity_text = activities[0] if activities else f"第{i}天"
        mermaid_steps.append(f"    {prev_node} --> {day_node}[Day{i}: {activity_text}]")
        prev_node = day_node

    mermaid_steps.append(f"    {prev_node} --> E[🏠 返程]")
    mermaid_diagram = "\n".join(mermaid_steps)

    # 生成每日行程详情
    itinerary_details = ""
    for day in itinerary:
        day_num = day.get("day_number", 0)
        activities = day.get("activities", [])
        meals = day.get("meals", [])
        accommodation_name = day.get("accommodation", "")

        itinerary_details += f"""
### 📅 第 {day_num} 天

**活动安排**：
{chr(10).join([f"- {act}" for act in activities])}

**餐饮**：{", ".join(meals)}

**住宿**：{accommodation_name}

---
"""

    # 生成预算明细表格
    budget_table = f"""
| 项目 | 费用（元） |
|------|-----------|
| 🚗 交通 | {budget.get('transport', 0):.2f} |
| 🏨 住宿 | {budget.get('accommodation', 0):.2f} |
| 🍽️ 餐饮 | {budget.get('food', 0):.2f} |
| 🎫 门票 | {budget.get('attractions', 0):.2f} |
| 📦 其他 | {budget.get('misc', 0):.2f} |
| **💰 总计** | **{budget.get('total', 0):.2f}** |
"""

    # 组装完整报告
    report = f"""# 🌍 {destination}旅行规划报告

---

## 📋 旅行概览

| 项目 | 详情 |
|------|------|
| 📍 目的地 | {destination} |
| 📅 出发日期 | {requirement.get('departure_date', '待定')} |
| 🗓️ 行程天数 | {requirement.get('travel_days', 0)} 天 |
| 👨‍👩‍👧‍👦 出行人数 | {requirement.get('adult_count', 0)} 成人 + {requirement.get('children_count', 0)} 儿童 |
| 🚗 交通方式 | {transport_display} |
| 🏨 住宿类型 | {accommodation_display} |
| 🍽️ 餐饮偏好 | {food_display} |
| 🎨 旅行风格 | {", ".join(requirement.get('travel_styles', []))} |

---

## 🗺️ 行程流程图
```mermaid
{mermaid_diagram}
```

---

## 📖 详细行程

{itinerary_details}

---

## 💰 预算明细

{budget_table}

---

## ⚠️ 注意事项

1. **证件准备**：请携带身份证等有效证件
2. **天气关注**：出行前请关注目的地天气预报
3. **保险建议**：建议购买旅行意外险
4. **紧急联系**：记录当地紧急救援电话

---

## 📞 服务支持

如需修改行程或有任何疑问，请随时联系我们！

> 📧 邮箱：support@travel-planner.com  
> 📱 电话：400-XXX-XXXX

---

*本报告由 AI 旅行规划助手自动生成*  
*生成时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return Command(update={
        "messages": [
            ToolMessage(
                content=f"🎉 旅行规划报告已生成！\n\n"
                        f"📍 目的地：{destination}\n"
                        f"🗓️ 行程：{requirement.get('travel_days', 0)} 天\n"
                        f"💰 预算：{budget.get('total', 0):.2f} 元\n\n"
                        f"报告已保存，您可以随时查看或导出。",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "report": report,
        # 流程结束，不再更新 current_step
      })






























# ========================退回工具==========================

# ============== 回退工具 ==============

# 所有可用步骤
ALL_STEPS = [
    "requirement_collection",       # 步骤1：需求收集
    "destination_recommendation",   # 步骤2：目的地推荐
    "transport_planning",           # 步骤3：交通规划
    "accommodation_planning",       # 步骤4：住宿规划
    "food_planning",                # 步骤5：餐饮规划
    "itinerary_generation",         # 步骤6：行程生成
    "budget_summarization",         # 步骤7：预算汇总
    "report_generation"             # 步骤8：报告生成
]

# 步骤中文名称映射
STEP_LABELS = {
    "requirement_collection": "需求收集",
    "destination_recommendation": "目的地推荐",
    "transport_planning": "交通规划",
    "accommodation_planning": "住宿规划",
    "food_planning": "餐饮规划",
    "itinerary_generation": "行程生成",
    "budget_summarization": "预算汇总",
    "report_generation": "报告生成"
}

# 每个步骤回退时需要清除的状态字段
STEP_STATE_FIELDS = {
    "requirement_collection": ["user_requirement"],
    "destination_recommendation": ["selected_destination", "destination_options"],
    "transport_planning": ["selected_transport", "transport_options"],
    "accommodation_planning": ["selected_accommodation_types", "accommodation_options"],
    "food_planning": ["selected_food_types", "food_options"],
    "itinerary_generation": ["itinerary"],
    "budget_summarization": ["budget"],
    "report_generation": ["report"]
}


# ============== 通用回退工具 ==============

def _go_back_to_step_impl(
        target_step: Literal[
            "requirement_collection",
            "destination_recommendation",
            "transport_planning",
            "accommodation_planning",
            "food_planning",
            "itinerary_generation",
            "budget_summarization"
        ],
        reason: str,
        clear_subsequent_data: bool = True,
        runtime: ToolRuntime = None
) -> Command:
    """
    回退到指定的历史步骤，允许用户重新进行规划。

    使用场景示例：
    - 用户说"我想重新选择目的地" -> target_step="destination_recommendation"
    - 用户说"我想重新制定旅行计划" -> target_step="requirement_collection"
    - 用户说"换个交通方式" -> target_step="transport_planning"
    - 用户说"住宿要求改一下" -> target_step="accommodation_planning"
    - 用户说"餐饮偏好不对" -> target_step="food_planning"
    - 用户说"行程安排需要调整" -> target_step="itinerary_generation"
    - 用户说"预算超了，重新算" -> target_step="budget_summarization"

    参数说明：
    - target_step: 要回退到的目标步骤
        * "requirement_collection" - 重新收集旅行需求（出发日期、人数、预算等）
        * "destination_recommendation" - 重新选择目的地
        * "transport_planning" - 重新选择交通方式（航班/高铁/自驾）
        * "accommodation_planning" - 重新选择住宿类型
        * "food_planning" - 重新选择餐饮偏好
        * "itinerary_generation" - 重新生成行程安排
        * "budget_summarization" - 重新计算预算

    - reason: 回退原因，用于记录和展示给用户
        示例："用户希望更换目的地为三亚"
        示例："预算超出用户预期，需要调整住宿标准"

    - clear_subsequent_data: 是否清除目标步骤之后的所有数据（默认 True）
        * True: 回退时清除后续步骤产生的选择和数据
        * False: 保留后续数据（谨慎使用，可能导致数据不一致）

    返回：
        Command 对象，包含状态更新和步骤跳转指令

    注意：
    - 不能把报告生成阶段作为回退目标（它是最终步骤）
    - 回退会在消息历史中记录，方便追溯
    """

    app_logger.info(f"回退请求: target_step={target_step}, reason={reason}, clear_data={clear_subsequent_data}")

    # 验证目标步骤
    if target_step not in ALL_STEPS:
        app_logger.warning(f"无效的目标步骤: {target_step}")
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"无效的目标步骤: {target_step}",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })

    # 不允许回退到报告生成（最终步骤）
    if target_step == "report_generation":
        app_logger.warning("尝试回退到报告生成步骤，已拒绝")
        return Command(update={
            "messages": [
                ToolMessage(
                    content="报告生成是最终步骤，无法回退到此步骤。如需修改，请回退到更早的步骤。",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })

    # 获取当前步骤（用于日志）
    current_step = runtime.state.get("current_step", "unknown") if runtime.state else "unknown"
    app_logger.info(f"执行回退: {current_step} -> {target_step}")

    # 构建状态更新
    state_update = {
        "current_step": target_step
    }

    # 如果需要清除后续数据
    cleared_fields = []
    if clear_subsequent_data:
        target_index = ALL_STEPS.index(target_step)
        for step in ALL_STEPS[target_index:]:
            for field in STEP_STATE_FIELDS.get(step, []):
                state_update[field] = None
                cleared_fields.append(field)

        if cleared_fields:
            app_logger.debug(f"清除的状态字段: {cleared_fields}")

    # 获取步骤标签
    step_label = STEP_LABELS.get(target_step, target_step)

    # 构建响应消息
    response_parts = [
        f"已回退到【{step_label}】阶段",
        f"原因: {reason}"
    ]
    if clear_subsequent_data and cleared_fields:
        response_parts.append("已清除后续步骤的数据")

    state_update["messages"] = [
        ToolMessage(
            content="\n".join(response_parts),
            tool_call_id=runtime.tool_call_id
        )
    ]

    app_logger.info(f"回退完成: {target_step}, 清除字段数: {len(cleared_fields)}")

    return Command(update=state_update)


go_back_to_step = tool(_go_back_to_step_impl)


# ============== 快捷回退工具 ==============

@tool
def go_back_to_requirement(
        reason: str = "用户需要修改旅行需求",
        runtime: ToolRuntime = None
) -> Command:
    """
    快捷回退：返回到需求收集步骤，重新开始规划。

    使用场景：
    - 用户说"我想重新规划"
    - 用户说"出发日期要改"
    - 用户说"预算变了"
    - 用户说"人数不对"
    - 用户说"从头开始"

    参数：
    - reason: 回退原因（可选，默认为"用户需要修改旅行需求"）

    效果：
    - 清除所有已收集的数据
    - 返回到最初的需求收集阶段
    """
    app_logger.info(f"快捷回退到需求收集: {reason}")

    return _go_back_to_step_impl(
        target_step="requirement_collection",
        reason=reason,
        clear_subsequent_data=True,
        runtime=runtime,
    )


@tool
def go_back_to_destination(
        reason: str = "用户需要重新选择目的地",
        runtime: ToolRuntime = None
) -> Command:
    """
    快捷回退：返回到目的地推荐步骤。

    使用场景：
    - 用户说"换个目的地"
    - 用户说"这个地方不想去了"
    - 用户说"有没有其他推荐"
    - 用户说"目的地选错了"

    参数：
    - reason: 回退原因（可选）

    效果：
    - 保留用户需求
    - 清除目的地选择及后续所有数据
    """
    app_logger.info(f"快捷回退到目的地推荐: {reason}")

    return _go_back_to_step_impl(
        target_step="destination_recommendation",
        reason=reason,
        clear_subsequent_data=True,
        runtime=runtime,
    )


@tool
def go_back_to_transport(
        reason: str = "用户需要更换交通方式",
        runtime: ToolRuntime = None
) -> Command:
    """
    快捷回退：返回到交通规划步骤。

    使用场景：
    - 用户说"不想坐飞机了"
    - 用户说"改成高铁"
    - 用户说"还是自驾吧"
    - 用户说"交通方式重新选"

    参数：
    - reason: 回退原因（可选）

    效果：
    - 保留用户需求和目的地选择
    - 清除交通方式及后续数据
    """
    app_logger.info(f"快捷回退到交通规划: {reason}")

    return _go_back_to_step_impl(
        target_step="transport_planning",
        reason=reason,
        clear_subsequent_data=True,
        runtime=runtime,
    )


@tool
def go_back_to_accommodation(
        reason: str = "用户需要调整住宿偏好",
        runtime: ToolRuntime = None
) -> Command:
    """
    快捷回退：返回到住宿规划步骤。

    使用场景：
    - 用户说"住宿要求改一下"
    - 用户说"想住民宿"
    - 用户说"酒店太贵了"
    - 用户说"换个住宿类型"

    参数：
    - reason: 回退原因（可选）

    效果：
    - 保留需求、目的地、交通方式
    - 清除住宿选择及后续数据
    """
    app_logger.info(f"快捷回退到住宿规划: {reason}")

    return _go_back_to_step_impl(
        target_step="accommodation_planning",
        reason=reason,
        clear_subsequent_data=True,
        runtime=runtime,
    )


@tool
def go_back_to_food(
        reason: str = "用户需要调整餐饮偏好",
        runtime: ToolRuntime = None
) -> Command:
    """
    快捷回退：返回到餐饮规划步骤。

    使用场景：
    - 用户说"餐饮偏好改一下"
    - 用户说"想多吃特色美食"
    - 用户说"简单点就行"

    参数：
    - reason: 回退原因（可选）

    效果：
    - 保留需求、目的地、交通、住宿
    - 清除餐饮选择及后续数据
    """
    app_logger.info(f"快捷回退到餐饮规划: {reason}")

    return _go_back_to_step_impl(
        target_step="food_planning",
        reason=reason,
        clear_subsequent_data=True,
        runtime=runtime,
    )


@tool
def go_back_to_itinerary(
        reason: str = "用户需要调整行程安排",
        runtime: ToolRuntime = None
) -> Command:
    """
    快捷回退：返回到行程生成步骤。

    使用场景：
    - 用户说"行程安排不太合理"
    - 用户说"想加点景点"
    - 用户说"太累了，减少活动"
    - 用户说"重新排一下行程"

    参数：
    - reason: 回退原因（可选）

    效果：
    - 保留所有偏好设置
    - 仅清除行程和预算数据
    """
    app_logger.info(f"快捷回退到行程生成: {reason}")

    return _go_back_to_step_impl(
        target_step="itinerary_generation",
        reason=reason,
        clear_subsequent_data=True,
        runtime=runtime,
    )


@tool
def go_back_to_budget(
        reason: str = "用户需要重新计算预算",
        runtime: ToolRuntime = None
) -> Command:
    """
    快捷回退：返回到预算汇总步骤。

    使用场景：
    - 用户说"预算超了"
    - 用户说"重新算一下费用"
    - 用户说"看看能不能便宜点"

    参数：
    - reason: 回退原因（可选）

    效果：
    - 保留行程安排
    - 仅清除预算和订单数据
    """
    app_logger.info(f"快捷回退到预算汇总: {reason}")

    return _go_back_to_step_impl(
        target_step="budget_summarization",
        reason=reason,
        clear_subsequent_data=True,
        runtime=runtime,
    )


# ============== 查询当前进度工具 ==============

@tool
def check_current_progress(
        runtime: ToolRuntime = None
) -> str:
    """
    查询当前规划进度，展示已完成和待完成的步骤。

    使用场景：
    - 用户问"现在到哪一步了"
    - 用户问"还有几步"
    - 用户问"进度如何"
    - 需要向用户汇报当前状态

    返回：
        格式化的进度信息字符串
    """
    state = runtime.state
    current_step = state.get("current_step", "requirement_collection")

    app_logger.debug(f"查询进度: current_step={current_step}")

    try:
        current_index = ALL_STEPS.index(current_step)
    except ValueError:
        app_logger.warning(f"未知的当前步骤: {current_step}")
        current_index = 0

    # 构建进度展示
    progress_lines = ["当前规划进度", ""]

    for i, step in enumerate(ALL_STEPS):
        label = STEP_LABELS.get(step, step)
        step_num = i + 1
        if i < current_index:
            progress_lines.append(f"  [{step_num}] {label} - 已完成")
        elif i == current_index:
            progress_lines.append(f"  [{step_num}] {label} - 当前步骤")
        else:
            progress_lines.append(f"  [{step_num}] {label} - 待完成")

    # 添加已收集的关键信息
    progress_lines.append("")
    progress_lines.append("已收集信息:")

    if state.get("user_requirement"):
        req = state["user_requirement"]
        progress_lines.append(f"  - 出发日期: {req.get('departure_date', '未设置')}")
        progress_lines.append(f"  - 出行天数: {req.get('travel_days', '未设置')} 天")
        progress_lines.append(f"  - 人数: {req.get('adult_count', 0)} 成人 + {req.get('children_count', 0)} 儿童")

    if state.get("selected_destination"):
        progress_lines.append(f"  - 目的地: {state['selected_destination']}")

    if state.get("selected_transport"):
        transport_labels = {"flight": "航班", "train": "高铁", "driving": "自驾"}
        progress_lines.append(
            f"  - 交通: {transport_labels.get(state['selected_transport'], state['selected_transport'])}")

    if state.get("selected_accommodation_types"):
        progress_lines.append(f"  - 住宿: {', '.join(state['selected_accommodation_types'])}")

    if state.get("selected_food_types"):
        progress_lines.append(f"  - 餐饮: {', '.join(state['selected_food_types'])}")

    app_logger.info(f"进度查询完成: 当前步骤={current_step}, 进度={current_index + 1}/{len(ALL_STEPS)}")

    return "\n".join(progress_lines)


# ============== 导出所有回退工具 ==============

ALL_ROLLBACK_TOOLS = [
    go_back_to_step,            # 通用回退（推荐）
    go_back_to_requirement,     # 快捷：回到需求收集
    go_back_to_destination,     # 快捷：回到目的地
    go_back_to_transport,       # 快捷：回到交通
    go_back_to_accommodation,   # 快捷：回到住宿
    go_back_to_food,            # 快捷：回到餐饮
    go_back_to_itinerary,       # 快捷：回到行程
    go_back_to_budget,          # 快捷：回到预算
    check_current_progress      # 查询进度
]















