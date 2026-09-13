"""
配置管理模块
使用 pydantic-settings 管理环境变量
"""
import os
from urllib.parse import quote
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

# 获取当前文件的上级目录（即项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    """应用配置"""

    # ============== 应用基础配置 ==============
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=14726, alias="APP_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    cors_origins: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000,http://localhost:14726,http://127.0.0.1:14726",
        alias="CORS_ORIGINS",
    )

    # ============== LLM 配置 ==============
    dashscope_api_key: str = Field(alias="DASHSCOPE_API_KEY")
    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    qwen_model_name: str = Field(default="qwen-max", alias="QWEN_MODEL_NAME")
    qwen_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="QWEN_BASE_URL"
    )
    qwen_temperature: float = 0.7
    qwen_max_tokens: int = 8000

    # ============== LangSmith 配置 ==============
    langsmith_api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="travel-planner-dev", alias="LANGSMITH_PROJECT")
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        alias="LANGSMITH_ENDPOINT"
    )

    # ============== 数据库配置 ==============
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")

    # ============== MCP 服务配置 ==============
    amap_api_key: str = Field(default="", alias="AMAP_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    model_config = SettingsConfigDict(
        env_file = os.path.join(BASE_DIR, ".env"),
        env_file_encoding = "utf-8",
        case_sensitive = False,
        extra = "ignore"
    )

    @property
    def database_url(self) -> str:
        """生成供 psycopg/psycopg_pool 使用的 PostgreSQL 连接字符串。"""
        return (
            f"postgresql://{quote(self.postgres_user, safe='')}:{quote(self.postgres_password, safe='')}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sqlalchemy_database_url(self) -> str:
        """生成供 SQLAlchemy 异步引擎使用的 Psycopg 3 连接字符串。"""
        return (
            f"postgresql+psycopg://{quote(self.postgres_user, safe='')}:{quote(self.postgres_password, safe='')}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """生成 Redis 连接字符串"""
        if self.redis_password:
            return f"redis://:{quote(self.redis_password, safe='')}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def cors_origin_list(self) -> list[str]:
        """返回去除空白后的 CORS 来源列表。"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（缓存）"""
    return Settings()


# 全局配置对象
settings = get_settings()

# 测试
#if __name__ == '__main__':
#     print(settings.database_url)
#     print(settings.redis_url)
#     print(settings.qwen_model_name)
#     print(settings.qwen_base_url)
#     print(settings.qwen_temperature)
#     print(settings.qwen_max_tokens)
#     print(settings.langsmith_api_key)
