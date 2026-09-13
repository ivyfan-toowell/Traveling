"""
流式对话 API（SSE）
"""
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse #流式返回
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update
from langchain_core.messages import HumanMessage
from app.models.base import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.message import MessageCreate
from app.api.dependencies import get_current_user
from app.agents.handoffs.travel_agent import create_travel_agent
from app.utils.logger import app_logger


router = APIRouter(prefix="/chat", tags=["对话"])

async def save_message(
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict = None
) -> Message:
    """保存消息到数据库"""

    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        extra_info=metadata or {}
    )

    db.add(message)
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=func.now())
    )
    await db.commit()
    await db.refresh(message)

    return message


def sse(data: dict) -> str:
    """
    SSE 标准 data 帧
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def chunk_text(content) -> str:
    """Extract text from both string and structured model stream chunks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return ""


async def generate_sse_stream(
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
        user:User
):
    assistant_message = ""
    active_tool_runs: set[str] = set()
    streamed_model_runs: set[str] = set()

    try:
        await save_message(
            db,
            conversation_id,
            "user",
            user_message,
        )

        agent = await create_travel_agent()

        input_data = {
            "messages": [HumanMessage(content=user_message)],
            "user_id": str(user.id)
        }

        async for event in agent.astream_events(
            input_data,
            config={
                "configurable": {
                    "thread_id": conversation_id
                }
            },
            version="v2"
        ):
            kind = event.get("event")
            run_id = event.get("run_id", "")
            parent_ids = set(event.get("parent_ids") or [])
            is_nested_tool_event = bool(parent_ids.intersection(active_tool_runs))

            if kind == "on_chat_model_stream" and not is_nested_tool_event:
                chunk = event.get("data",{}).get("chunk")
                if chunk and hasattr(chunk,"content") and chunk.content:
                    token = chunk_text(chunk.content)
                    if not token:
                        continue
                    streamed_model_runs.add(run_id)
                    assistant_message += token
                    yield sse({
                        "type":"token",
                        "content":token
                    })

            elif (
                kind == "on_chat_model_end"
                and not is_nested_tool_event
                and run_id not in streamed_model_runs
            ):
                output = event.get("data", {}).get("output")
                token = chunk_text(getattr(output, "content", ""))
                if token:
                    assistant_message += token
                    yield sse({"type": "token", "content": token})

            elif kind == "on_tool_start":
                if run_id:
                    active_tool_runs.add(run_id)
                tool_name = event.get("name", "")
                yield sse({
                    "type": "tool_call",
                    "tool": tool_name,
                })

            elif kind in {"on_tool_end", "on_tool_error"}:
                active_tool_runs.discard(run_id)

            await asyncio.sleep(0)

        if assistant_message.strip():
            await save_message(
                db,
                conversation_id,
                "assistant",
                assistant_message
            )

        yield sse({"type": "done"})

    except Exception:
        app_logger.exception("❌ SSE 流式对话错误")
        yield sse({
            "type": "error",
            "message": "对话处理失败，请稍后重试",
        })


@router.post("/stream/{conversation_id}")
async def stream_chat(
        conversation_id: str,
        data: MessageCreate,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    流式对话（SSE）

    Returns:
        StreamingResponse: SSE 流式响应
    """

    # 验证会话归属
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == user.id)
        .where(Conversation.status != "deleted")
    )

    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 返回 SSE 流
    return StreamingResponse(
        generate_sse_stream(
            conversation_id,
            data.content,
            db,
            user
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


@router.get("/history/{conversation_id}")
async def get_chat_history(
        conversation_id: str,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取会话历史消息"""

    # 验证会话归属
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == user.id)
        .where(Conversation.status != "deleted")
    )

    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 查询消息
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )

    messages = result.scalars().all()

    return {
        "conversation": conversation.to_dict(),
        "messages": [m.to_dict() for m in messages]
    }
