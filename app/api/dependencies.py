"""
API 依赖项
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.base import get_db
from app.models.user import User
from app.utils.security import decode_access_token


security = HTTPBearer()

# HTTPBearer：这是一种安全模型，它告诉 FastAPI：“我的接口要求前端必须在 HTTP 请求头里带上 Authorization: Bearer <token> 格式的数据”。
# 它就像安装了一个只能读特定格式门禁卡的读卡器。

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前登录用户（依赖注入）

    用法：
        @app.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """

    token = credentials.credentials  # 提取出纯粹的 token 字符串

    # 解码 JWT
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期"
        )  # 如果返回 None，说明 token 被篡改了或者过期了，直接抛出 401 Unauthorized (未授权) 异常，请求中断。

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误"
        )

    # 查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    # SQLAlchemy 的特定方法。意思是：“从结果里取出唯一的那一行数据，转换成 User 对象；如果没查到，不要报错，返回 None

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    return user

    # 这段代码最爽的地方在于“复用”。你只需要写一次这个复杂的验证逻辑，
    # 以后所有需要登录才能访问的接口，加一行代码就行了