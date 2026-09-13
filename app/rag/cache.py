"""
RAG 缓存层
使用 Redis 缓存检索结果
"""
import os
import json
import hashlib
from typing import List, Optional
from dotenv import load_dotenv
import redis
from langchain_core.documents import Document
from app.utils.logger import app_logger

load_dotenv()


class RAGCache:
    """
    RAG 检索结果缓存

    使用 Redis 存储，key 为查询的 hash
    """

    def __init__(
            self,
            ttl: int = 3600,  # 缓存过期时间（秒）
            enabled: bool = True
    ):
        self.ttl = ttl
        self.enabled = enabled

        if enabled:
            try:
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    db=int(os.getenv("REDIS_DB", 0)),
                    password=os.getenv("REDIS_PASSWORD", None),
                    decode_responses=False  # 存储二进制数据
                )
                # 测试连接
                self.redis_client.ping()
                app_logger.info("Redis 缓存已启用")
            except Exception as e:
                app_logger.warning(f"Redis 连接失败，禁用缓存: {e}")
                self.enabled = False

    def _generate_key(self, query: str, top_k: int) -> str:
        """生成缓存 key"""
        content = f"{query}__k{top_k}"
        hash_value = hashlib.md5(content.encode()).hexdigest()
        return f"rag:cache:.{hash_value}"

    def get(self, query: str, top_k: int) -> Optional[List[Document]]:
        """从缓存获取结果"""

        if not self.enabled:
            return None

        key = self._generate_key(query, top_k)

        try:
            cached_data = self.redis_client.get(key)

            if cached_data:
                app_logger.info(f"命中缓存: {query[:30]}...")

                # 反序列化
                docs_data = json.loads(cached_data)
                documents = [
                    Document(
                        page_content=item["page_content"],
                        metadata=item["metadata"]
                    )
                    for item in docs_data
                ]

                return documents

        except Exception as e:
            app_logger.error(f"缓存读取失败: {e}")

        return None

    def set(self, query: str, top_k: int, documents: List[Document]):
        """缓存结果"""

        if not self.enabled:
            return

        key = self._generate_key(query, top_k)

        try:
            # 序列化文档
            docs_data = [
                {
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in documents
            ]

            serialized = json.dumps(docs_data, ensure_ascii=False)

            # 存入 Redis
            self.redis_client.setex(key, self.ttl, serialized)

            app_logger.debug(f"已缓存结果: {query[:30]}...")

        except Exception as e:
            app_logger.error(f"缓存写入失败: {e}")