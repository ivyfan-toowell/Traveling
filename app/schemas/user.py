"""
用户相关的 Pydantic 模型
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class UserRegister(BaseModel):
    """用户注册"""
    username: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码的 UTF-8 长度不能超过 72 字节")
        return value


class UserLogin(BaseModel):
    """用户登录"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=72)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    """用户信息响应"""
    id: uuid.UUID
    username: str
    email: str
    preferences: Optional[Dict[str, Any]] = None
    created_at: datetime



class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse  #from_attributes = True的作用是：允许这个 Pydantic 模型直接读取 SQLAlchemy 的数据库对象。
