"""
消息模型
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class Message(Base):
    """消息表"""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )  #主键

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        index=True
    ) #外键

    # 角色：user, assistant, system
    role: Mapped[str] = mapped_column(String(20), index=True)

    # 消息内容
    content: Mapped[str] = mapped_column(Text)

    # 元数据（JSON 格式）
    extra_info: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        index=True
    )

    # 关系
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")