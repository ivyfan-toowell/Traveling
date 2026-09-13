"""
目的地 Router
Agent 自主决定是否调用 RAG 工具
"""
from typing import TypedDict, Annotated, Literal
from operator import add
from pydantic import BaseModel, Field
from langchain_community.chat_models import ChatTongyi
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from app.config import settings
from app.tools.rag_tools import get_rag_tools  # 导入 RAG 工具
from app.mcp_core.servers.weather_server import get_weather_forecast
from app.utils.logger import app_logger


# ============== State 定义 ==============

class Classification(TypedDict):
    agent: Literal["explore", "weather"]
    query: str


class AgentOutput(TypedDict):
    agent_name: str
    result: str


class DestinationRouterState(TypedDict):
    original_query: str
    destination: str
    classifications: list[Classification]
    agent_results: Annotated[list[AgentOutput], add]
    final_report: str


# ============== 分类器（保持不变） ==============

class ClassificationResult(BaseModel):
    classifications: list[Classification] = Field(
        description="要调用的 Agent 列表及其子查询"
    )


def classifier_node(state: DestinationRouterState) -> dict:
    """分类器节点"""
    app_logger.info(f"分类器分析查询: {state['original_query']}")

    llm = ChatTongyi(
        model=settings.qwen_model_name,
        api_key=settings.dashscope_api_key
    )
    structured_llm = llm.with_structured_output(ClassificationResult)

    result = structured_llm.invoke([
        {
            "role": "system",
            "content": """你是旅行查询分类专家。分析用户查询，决定需要调用哪些 Agent：

**可用 Agent**：
- explore：景点攻略、美食推荐、住宿信息、交通指南（从知识库检索）
- weather：实时天气信息（调用天气 API）

**分类规则**：
1. 涉及景点、美食、住宿、攻略 → explore
2. 涉及天气、气温、降雨 → weather
3. 综合性查询（如"推荐XX旅游"）→ 两个都调用"""
        },
        {
            "role": "user",
            "content": f"目的地：{state['destination']}\n查询：{state['original_query']}"
        }
    ])

    app_logger.info(f"✅ 分类完成：{len(result.classifications)} 个 Agent")
    return {"classifications": result.classifications}


def route_to_agents(state: DestinationRouterState) -> list[Send]:
    """路由函数"""
    sends = []
    for classification in state["classifications"]:
        sends.append(
            Send(
                classification["agent"],
                {
                    "query": classification["query"],
                    "destination": state["destination"]
                }
            )
        )
    app_logger.info(f"并行发送 {len(sends)} 个任务")
    return sends


# ============== 探索 Agent（使用 RAG 工具） ==============

# 创建探索 Agent（带 RAG 工具）
def _create_explore_agent():
    """创建带 RAG 工具的探索 Agent"""

    llm = ChatTongyi(
        model=settings.qwen_model_name,
        api_key=settings.dashscope_api_key,
        temperature=0.7
    )

    # 获取 RAG 工具
    rag_tools = get_rag_tools()

    # 创建 Agent - Agent 会自主决定调用哪些工具
    agent = create_agent(
        model=llm,
        tools=rag_tools,
        system_prompt="""你是一位专业的旅行顾问，负责为用户提供目的地的详细信息。

你有以下工具可以使用：
- search_destination_guide: 检索景点攻略、门票、游玩建议
- search_food_recommendations: 检索美食推荐
- search_accommodation_info: 检索住宿建议
- search_travel_tips: 检索旅行注意事项

**工作方式**：
1. 分析用户的查询需求
2. 根据需要选择合适的工具进行检索
3. 你可以调用多个工具来获取全面的信息
4. 基于检索到的信息，生成专业、详细的回答

**注意**：
- 只有当你需要知识库中的信息时才调用工具
- 如果用户只是闲聊或问简单问题，直接回答即可
- 整合多个工具的结果时，注意信息的逻辑性和连贯性
"""
    )

    return agent


# 全局 Agent 实例（避免重复创建）
_explore_agent = None


async def explore_agent_node(state: dict) -> dict:
    """
    探索 Agent 节点
    Agent 自主决定是否调用 RAG 工具
    """
    global _explore_agent

    query = state["query"]
    destination = state["destination"]

    app_logger.info(f"🏛️ 探索 Agent 执行: {destination} - {query}")

    # 懒加载 Agent
    if _explore_agent is None:
        _explore_agent = _create_explore_agent()

    # 构建用户消息
    user_message = f"请为我提供关于 {destination} 的以下信息：{query}"

    # 调用 Agent - Agent 会自主决定是否使用 RAG 工具
    response = await _explore_agent.ainvoke({
        "messages": [{"role": "user", "content": user_message}]
    })

    # 提取 Agent 的最终回复
    final_message = response["messages"][-1].content

    formatted_result = f"""## {destination} 旅游信息

{final_message}

---
*信息来源：知识库检索*
"""

    return {
        "agent_results": [
            {
                "agent_name": "explore",
                "result": formatted_result
            }
        ]
    }


# ============== 天气 Agent ==============

CITY_ADCODES = {
    "北京": "110000", "上海": "310000", "天津": "120000", "重庆": "500000",
    "西安": "610100", "成都": "510100", "深圳": "440300", "杭州": "330100",
    "广州": "440100", "南京": "320100", "武汉": "420100", "长沙": "430100",
    "青岛": "370200", "大理": "532900", "昆明": "530100", "厦门": "350200",
    "三亚": "460200", "哈尔滨": "230100", "乌鲁木齐": "650100", "拉萨": "540100",
}

async def weather_agent_node(state: dict) -> dict:
    """查询高德天气；无法确定城市编码时明确提示，不生成虚构天气。"""
    destination = state["destination"]

    app_logger.info(f"🌤️ 天气 Agent 执行: {destination}")
    adcode = next((code for city, code in CITY_ADCODES.items() if city in destination), None)

    if adcode is None:
        result = (
            f"## {destination} 天气信息\n\n"
            "暂时无法将该目的地匹配到天气服务支持的城市编码，因此不提供猜测性天气。"
            "建议出发前通过官方天气渠道再次确认。"
        )
    else:
        weather_data = await get_weather_forecast.fn(city_adcode=adcode)
        result = f"## {destination} 天气信息\n\n{weather_data}"

    return {
        "agent_results": [
            {"agent_name": "weather", "result": result}
        ]
    }


# ============== 综合器 ==============

async def synthesizer_node(state: DestinationRouterState) -> dict:
    """综合 Agent 结果"""
    app_logger.info("综合 Agent 结果...")

    results = state["agent_results"]
    destination = state["destination"]

    if not results:
        return {"final_report": "未找到相关信息。"}

    # 简单合并（可以用 LLM 进行更智能的综合）
    sections = [r["result"] for r in results]
    final_report = "\n\n".join(sections)

    app_logger.info("✅ 综合完成")
    return {"final_report": final_report}


# ============== 构建 Router 图 ==============

def create_destination_router():
    """创建目的地 Router"""

    workflow = StateGraph(DestinationRouterState)

    workflow.add_node("classifier", classifier_node)
    workflow.add_node("explore", explore_agent_node)
    workflow.add_node("weather", weather_agent_node)
    workflow.add_node("synthesizer", synthesizer_node)

    workflow.add_edge(START, "classifier")
    workflow.add_conditional_edges(
        "classifier",
        route_to_agents,
        ["explore", "weather"]
    )
    workflow.add_edge("explore", "synthesizer")
    workflow.add_edge("weather", "synthesizer")
    workflow.add_edge("synthesizer", END)

    app = workflow.compile()
    app_logger.info("✅ 目的地 Router 创建完成")

    return app
