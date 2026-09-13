import asyncio
from typing import Optional, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from langgraph.store.postgres import AsyncPostgresStore
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from app.config import settings
from app.utils.logger import app_logger
from app.core.memory_models import UserProfile, TravelHistory,TravelRecord,UserMemory

class StoreManager:
    """store管理器（单例模式）"""
    _instance: Optional["StoreManager"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.pool:Optional[AsyncConnectionPool] = None
        self.store:Optional[AsyncPostgresStore] = None

    @classmethod
    async def get_instance(cls) -> "StoreManager":
        """获取单例实例"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance.initialize()

        return cls._instance

    async def initialize(self):
        """初始化 store"""
        if self.store is not None:
            app_logger.warning(" ⚠️Store 先已初始化 ")
            return

        try:
            app_logger.info("初始化 PostgreSQL Store...")

            self.pool = AsyncConnectionPool(
                conninfo=settings.database_url,
                min_size=2,
                max_size=20,
                timeout=30,
                open=False,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                },
            )
            await self.pool.open()

            self.store = AsyncPostgresStore(self.pool)

            app_logger.info("✅ Store 初始化完成")

        except Exception as e:
            app_logger.error(f"❌ Store 初始化失败: {e}")
            raise

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.store = None
            app_logger.info("Connection Pool 已关闭")

    def get_store(self) -> AsyncPostgresStore:
        if self.store is None:
            raise RuntimeError("Store 未初始化，请先调用 initialize()")
        return self.store

# ============== 便捷函数 ==============

async def get_store() -> AsyncPostgresStore:
    manager = await StoreManager.get_instance()
    return manager.get_store()


@asynccontextmanager
async def store_lifespan():
    """Store 生命周期管理器"""
    manager = await StoreManager.get_instance()
    try:
        yield manager.get_store()
    finally:
        await manager.close()



# ============== 用户长期记忆服务 ==============


class UserMemoryService:
    """
    用户长期记忆服务
    提供用户画像和出行历史的增删改查操作
    """
    def __init__(self, store: AsyncPostgresStore):
        self.store = store

    def _get_current_time(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ========== 用户画像操作 ==========

    async def get_user_profile(self,user_id:str) -> UserProfile:
        """获取用户画像"""
        try:
            result = await self.store.aget(
                namespace=("user_profiles",user_id),
                key = "profile"
            )
            if result and result.value:
                return UserProfile(**result.value)

            return UserProfile()

        except Exception as e:
            app_logger.error(f"❌ 获取用户画像失败: {e}")
            return UserProfile()

    async def save_user_profile(self,user_id:str,profile:UserProfile) -> UserProfile:
        """保存用户画像"""
        profile.updated_at = self._get_current_time()

        await self.store.aput(
            namespace=("user_profiles",user_id),
            key="profile",
            value=profile.model_dump()
        )
        app_logger.info(f"保存用户画像: {user_id}")
        return profile

    async def update_travel_styles(self, user_id:str, styles: List[str]) :
        """更新旅行风格偏好"""
        profile = await self.get_user_profile(user_id)
        # 去重 合并
        current_styles = set(profile.travel_styles)
        current_styles.update(styles)
        profile.travel_styles = list(current_styles)

        await self.save_user_profile(user_id, profile)

    async def update_dietary_restrictions(self, user_id:str, dietary_restrictions: List[str]) :
        """更新饮食禁忌"""
        profile = await self.get_user_profile(user_id)
        current_dietary_restrictions = set(profile.dietary_restrictions)
        current_dietary_restrictions.update(dietary_restrictions)
        profile.dietary_restrictions = list(current_dietary_restrictions)

        await self.save_user_profile(user_id, profile)

    async def update_food_preferences(self, user_id: str, preferences: List[str]):
        """更新饮食偏好"""
        profile = await self.get_user_profile(user_id)
        current = set(profile.food_preferences)
        current.update(preferences)
        profile.food_preferences = list(current)

        await self.save_user_profile(user_id, profile)


    # ========== 出行历史操作 ==========

    async def get_travel_history(self,user_id:str) -> TravelHistory:
        try:
            result = await self.store.aget(
                namespace=("travel_history",user_id),
                key = "history"
            )
            if result and result.value:
                return TravelHistory(**result.value)

            return TravelHistory()

        except Exception as e:
            app_logger.error(f"❌ 获取出行历史失败: {e}")
            return TravelHistory()

    async def save_travel_history(self, user_id: str, history: TravelHistory):
        """保存出行历史"""
        history.updated_at = self._get_current_time()

        await self.store.aput(
            namespace=("travel_history", user_id),
            key="history",
            value=history.model_dump()
        )

        app_logger.info(f"保存出行历史: {user_id}")

    async def add_completed_trip(
            self,
            user_id: str,
            destination: str,
            start_date: str,
            end_date: str,
            visited_attractions: List[str]
    ):
        """添加已完成的旅行记录"""
        history = await self.get_travel_history(user_id)

        trip = TravelRecord(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            visited_attractions=visited_attractions
        )
        history.completed_trips.append(trip)

        current_attractions = set(history.visited_attractions)
        current_attractions.update(visited_attractions)
        history.visited_attractions = list(current_attractions)

        await self.save_travel_history(user_id, history)

        app_logger.info(f"添加旅行记录: {user_id} -> {destination}")

    async def update_accommodation_preference(
            self,
            user_id: str,
            preferred_types: Optional[List[str]] = None,
            avg_budget: Optional[float] = None,
    ):
        """更新住宿偏好。"""
        history = await self.get_travel_history(user_id)
        preference = history.accommodation_preference

        if preferred_types:
            current_types = set(preference.preference_types)
            current_types.update(preferred_types)
            preference.preference_types = list(current_types)

        if avg_budget is not None:
            if avg_budget < 0:
                raise ValueError("每晚住宿预算不能为负数")
            old_avg_budget = preference.avg_budget_per_night
            preference.avg_budget_per_night = (
                (old_avg_budget + avg_budget) / 2
                if old_avg_budget is not None
                else avg_budget
            )

        await self.save_travel_history(user_id, history)
        app_logger.info(f"更新住宿偏好: {user_id}")

    async def get_visited_destinations(self, user_id:str) -> List[str]:
        """获取用户去过的所有目的地。"""
        history = await self.get_travel_history(user_id)
        return list(dict.fromkeys(trip.destination for trip in history.completed_trips))

    async def get_visited_attractions(self, user_id:str) -> List[str]:
        """获取用户去过的所有景点。"""
        history = await self.get_travel_history(user_id)
        return history.visited_attractions


    # ========== 搜索操作 (示例，如果后续需要) ==========

    async def search_memories(self, user_id: str, query: str):
        """
        示例：使用 asearch 进行向量相似度搜索
        注意：这需要 Postgres 启用 pgvector 并且 Store 配置了 embedding 模型
        """
        results = await self.store.asearch(
            namespace=("user_profiles", user_id),
            query=query,
            limit=5
        )
        return results

    async def get_user_memory(self, user_id:str) -> UserMemory:
        """获取用户完整长期记忆"""
        profile, history = await asyncio.gather(
            self.get_user_profile(user_id),
            self.get_travel_history(user_id)
        )
        return UserMemory(
            user_id=user_id,
            profile=profile,
            history=history
        )

    async def format_memory_for_prompt(self, user_id: str) -> str:
        """将用户记忆格式化为提示词文本"""
        memory = await self.get_user_memory(user_id)

        parts = ["**用户历史偏好**："]

        # 用户画像
        if memory.profile.travel_styles:
            parts.append(f"- 旅行风格：{', '.join(memory.profile.travel_styles)}")

        if memory.profile.dietary_restrictions:
            parts.append(f"- 饮食禁忌：{', '.join(memory.profile.dietary_restrictions)}")

        if memory.profile.food_preferences:
            parts.append(f"- 饮食偏好：{', '.join(memory.profile.food_preferences)}")

        # 出行历史
        if memory.history.completed_trips:
            # 提取最近去过的目的地
            destinations = list(dict.fromkeys(t.destination for t in memory.history.completed_trips))
            parts.append(f"- 去过的目的地：{', '.join(destinations[-5:])}")

        visited_attractions = memory.history.visited_attractions
        if visited_attractions:
            parts.append(f"- 去过的景点：{', '.join(visited_attractions[-10:])}（最近10个）")

        # 住宿偏好
        acc_pref = memory.history.accommodation_preference
        if acc_pref.preference_types:
            parts.append(f"- 住宿偏好：{', '.join(acc_pref.preference_types)}")

        if acc_pref.avg_budget_per_night:
            parts.append(f"- 住宿预算：约 {acc_pref.avg_budget_per_night:.0f} 元/晚")

        if len(parts) == 1:
            return ""  # 没有历史数据

        return "\n".join(parts)

# ============== 创建服务实例 ==============

async def get_user_memory_service() -> UserMemoryService:
    """获取用户记忆服务实例"""
    store = await get_store()
    return UserMemoryService(store)
