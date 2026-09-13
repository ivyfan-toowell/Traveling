"""
会话管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.base import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from app.api.dependencies import get_current_user
from app.core.checkpointer import get_checkpointer

router = APIRouter(prefix="/conversations", tags=["会话管理"])

@router.post("", response_model=ConversationResponse)
async def create_conversation(
        data: ConversationCreate,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """创建新会话"""

    conversation = Conversation(
        user_id=user.id,
        title=data.title,
        status="active"
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取用户的所有会话"""

    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .where(Conversation.status != "deleted")
        .order_by(desc(Conversation.updated_at))
    )

    conversations = result.scalars().all()

    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
        conversation_id: str,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取会话详情"""

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

    return ConversationResponse.model_validate(conversation)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
        conversation_id: str,
        data: ConversationUpdate,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """更新会话"""

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

    # 更新字段
    if data.title is not None:
        conversation.title = data.title
    if data.status is not None:
        conversation.status = data.status

    await db.commit()
    await db.refresh(conversation)

    return ConversationResponse.model_validate(conversation)


@router.delete("/{conversation_id}")
async def delete_conversation(
        conversation_id: str,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """删除会话（软删除）"""

    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == user.id)
    )

    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    conversation.status = "deleted"
    await db.commit()

    try:
        checkpointer = await get_checkpointer()
        await checkpointer.adelete_thread(conversation_id)
    except Exception:
        # 会话已完成软删除；检查点清理失败不应让客户端误以为删除失败。
        from app.utils.logger import app_logger
        app_logger.exception("清理已删除会话的 Agent 检查点失败")

    return {"message": "会话已删除"}
