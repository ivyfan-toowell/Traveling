"""
向量数据库管理
"""

import hashlib
import json
from typing import List
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from app.config import BASE_DIR, settings
from app.utils.logger import app_logger

class VectorStoreManager:
    """向量数据库管理器"""
    def __init__(
            self,
            persist_directory:str = None,
            collection_name:str = "travel_guides"
    ):
        self.persist_directory = Path(persist_directory) if persist_directory else Path(BASE_DIR) / "data" / "vectorstore"
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
        """同步全部文档；首次建库，重复执行不重复写入，更新后移除旧分块。"""
        if not documents:
            raise RuntimeError("知识库为空，请在 data/documents/ 的三类目录中添加 UTF-8 Markdown 文件")

        vectorstore = self.get_vectorstore()
        desired = {}
        for doc in documents:
            payload = json.dumps(
                {"content": doc.page_content, "metadata": doc.metadata},
                ensure_ascii=False, sort_keys=True,
            )
            document_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            desired[document_id] = doc

        existing_ids = set(vectorstore.get(include=[])["ids"])
        new_ids = sorted(set(desired) - existing_ids)
        # 先写入新分块；Embedding 接口失败时保留已有索引，便于重试。
        if new_ids:
            vectorstore.add_documents([desired[doc_id] for doc_id in new_ids], ids=new_ids)
        stale_ids = sorted(existing_ids - set(desired))
        if stale_ids:
            vectorstore.delete(ids=stale_ids)

        app_logger.info(f"✅ 向量库同步完成: 新增 {len(new_ids)}，移除 {len(stale_ids)}，总计 {len(desired)} 个分块")
        return vectorstore

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

























