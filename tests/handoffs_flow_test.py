#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/1/6 16:09
@Author  : GGBOND
@File    : travel_agent.py
@Software: PyCharm
"""
import asyncio
import os
import sys
import uuid
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage, AIMessage
from app.agents.handoffs.travel_agent import create_travel_agent
from app.tools.state_transition import (
    record_requirement_tool,
    select_destination_tool,
    select_transport_tool,
    select_accommodation_tool,
    select_food_tool,
    generate_itinerary_tool,
    summarize_budget_tool,
    generate_report_tool,
    go_back_to_requirement,
    go_back_to_destination
)

load_dotenv()

model = ChatTongyi(
    model="qwen-max",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)

all_tools = [
    record_requirement_tool,
    select_destination_tool,
    select_transport_tool,
    select_accommodation_tool,
    select_food_tool,
    generate_itinerary_tool,
    summarize_budget_tool,
    generate_report_tool,
    go_back_to_requirement,
    go_back_to_destination
]



async def run_interactive_chat():
    """
    运行持续对话的测试循环
    """
    # 1. 生成一个唯一的会话 ID (thread_id)
    # LangGraph 的 Checkpointer 需要这个 ID 来区分不同的用户/会话历史

    travel_agent = await create_travel_agent()

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print(f"=== 开始测试 (会话 ID: {thread_id}) ===")
    print("输入 'q', 'quit', 'exit' 退出对话")
    print("-" * 50)

    while True:
        try:
            # 2. 获取用户输入
            user_input = input("\nUser (你): ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["q", "quit", "exit"]:
                print("结束对话。")
                break

            # 3. 构造输入状态
            # 假设 TravelState 中包含 'messages' 字段
            inputs = {"messages": [HumanMessage(content=user_input)]}

            # 4. 运行 Agent 并流式获取输出
            # stream_mode="values" 会返回每一步的状态快照
            print("\nAssistant (Agent): ", end="", flush=True)

            last_message_id = None

            # 使用 stream 来处理图的执行
            async for event in travel_agent.astream(inputs, config=config, stream_mode="values"):
                # 获取当前状态下的消息列表
                messages = event.get("messages", [])

                if messages:
                    last_msg = messages[-1]

                    # 避免重复打印相同的消息 (因为 stream 会输出每一步的状态)
                    if last_msg.id == last_message_id:
                        continue

                    last_message_id = last_msg.id

                    # 只打印 AI 的回复，跳过中间的 Tool 调用消息
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        print(last_msg.content)

                    # 如果想看工具调用的细节，可以取消下面的注释
                    # elif isinstance(last_msg, ToolMessage):
                    #     print(f"\n[系统日志] 工具执行完毕: {last_msg.name}")

        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_interactive_chat())
