"""
会话相关的 Pydantic 模型
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional
from datetime import datetime
import uuid


class ConversationCreate(BaseModel):
    """创建会话"""
    title: str = Field(default="新对话", min_length=1, max_length=200)


class ConversationUpdate(BaseModel):
    """更新会话"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    status: Optional[Literal["active", "archived"]] = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    """会话响应"""
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    status: str
    extra_info: dict
    created_at: datetime
    updated_at: datetime
