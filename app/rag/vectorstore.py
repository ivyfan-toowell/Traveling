"""
向量数据库管理
"""

from typing import List
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from app.config import settings
from app.utils.logger import app_logger

class VectorStoreManager:
    """向量数据库管理器"""
    def __init__(
            self,
            persist_directory:str = "data/vectorstore",
            collection_name:str = "travel_guides"
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.embeddings = DashScopeEmbeddings(
            model="text-embedding-v2",
            dashscope_api_key=settings.dashscope_api_key
        )

        self.vectorstore = None

    def create_vectorstore(
            self,
            documents: List[Document],
    ) -> Chroma:
        """创建向量数据库"""

        app_logger.info(f"创建向量数据库（{len(documents)} 个文档）...")

        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=str(self.persist_directory),
            collection_name=self.collection_name
        )

        app_logger.info("✅ 向量数据库创建完成")

        return self.vectorstore

    def load_vectorstore(self) ->Chroma:
        """加载已有向量数据库"""

        app_logger.info("加载向量数据库...")

        self.vectorstore = Chroma(
            persist_directory=str(self.persist_directory),
            collection_name=self.collection_name,
            embedding_function=self.embeddings
        )

        app_logger.info("✅ 向量数据库加载完成")

        return self.vectorstore

    def get_vectorstore(self) -> Chroma:
        """获取向量数据库实例"""
        if self.vectorstore is None:
            try:
                return self.load_vectorstore()
            except Exception as exc:
                app_logger.warning("⚠️ 向量数据库不存在或无法读取")
                raise RuntimeError("向量数据库未初始化") from exc
        return self.vectorstore

























