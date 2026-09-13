"""
消息相关的 Pydantic 模型
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
import uuid


class MessageCreate(BaseModel):
    """创建消息"""
    content: str = Field(..., min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    """消息响应"""
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    extra_info: dict
    created_at: datetime
