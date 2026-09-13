"""
长期记忆数据模型
使用 Pydantic BaseModel 定义结构化的用户记忆数据
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

# ============== 用户画像模型 ==============

class UserProfile(BaseModel):
    """
    用户画像
    存储用户的基础偏好和个人信息
    """
    # 旅行风格偏好(可多选)
    travel_styles: list[str] = Field(
        default_factory=list,
        description = "旅行风格偏好，如：城市风光、休闲度假、文化探索、户外冒险、美食之旅"
    )
    # 饮食禁忌/过敏
    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description = "饮食禁忌，如：素食、清真、无麸质、海鲜过敏、花生过敏、乳糖不耐受"
    )

    # 饮食偏好
    food_preferences: list[str] = Field(
        default_factory=list,
        description="饮食偏好，如：辣、甜、酸、清淡、重口味、当地特色、火锅、烧烤"
    )

    # 更新时间
    updated_at: Optional[str] = Field(
        default=None,
        description="最后更新时间"
    )

# ============== 出行历史模型 ==============

class TravelRecord(BaseModel):
    """
    单次旅行记录
    """
    destination: str = Field(...,description="目的地")
    start_date: str = Field(...,description="开始日期，格式：YYYY-MM-DD")
    end_date: str = Field(...,description="开始日期，格式：YYYY-MM-DD")
    visited_attractions: list[str] = Field(
        default_factory=list,
        description="已经游玩过的景点列表"
    )

class AccommodationPreference(BaseModel):
    """
    住宿偏好
    """
    preference_types: list[str] = Field(
        default_factory=list,
        description="偏好的住宿类型，如：星级酒店、经济酒店、特色民宿、青年旅社"
    )
    avg_budget_per_night: Optional[float] = Field(
        default=None,
        description="平均每晚预算（单位：元）"
    )

class TravelHistory(BaseModel):
    """
    出行历史
    存储用户的历史旅行记录和住宿偏好
    """
    # 已完成的旅行记录
    completed_trips: list[TravelRecord] = Field(
        default_factory=list,
        description="已完成的旅行记录列表"
    )

    # 去过的景点(汇总,用于避免重复推荐)
    visited_attractions: list[str] = Field(
        default_factory=list,
        description="所有去过的景点汇总，用于避免重复推荐"
    )

    # 住宿偏好
    accommodation_preference: AccommodationPreference = Field(
        default_factory=AccommodationPreference,
        description="用户的住宿偏好设置"
    )

    # 更新时间
    updated_at: Optional[str] = Field(
        default=None,
        description="最后更新时间"
    )

# ============== 完整用户记忆模型 ==============

class UserMemory(BaseModel):
    """
    用户完整长期记忆
    整合用户画像和出行历史
    """
    user_id: str = Field(..., description="用户唯一标识ID")

    profile:UserProfile = Field(
        default_factory=UserProfile,
        description="用户画像信息"
    )

    history:TravelHistory = Field(
        default_factory=TravelHistory,
        description="用户出行历史记录"
    )














