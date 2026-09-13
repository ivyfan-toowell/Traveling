"""
完整的 Advanced RAG 管道
整合所有优化策略
"""
import os
from typing import List
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.chat_models import ChatTongyi
from app.rag.query_optimizer import AdvancedQueryOptimizer
from app.rag.retriever import AdvancedHybridRetriever
from app.rag.reranker import LLMReranker, LongContextReorder
from app.rag.text_splitter import AdvancedParentDocumentSplitter
from app.utils.logger import app_logger
from app.rag.cache import RAGCache

load_dotenv()


class AdvancedRAGPipeline:
    """
    高级 RAG 管道

    完整流程：
    查询优化 → 混合检索 → 重排序 → 上下文优化
    """

    def __init__(
            self,
            vectorstore: Chroma,
            all_documents: List[Document],
            parent_splitter: AdvancedParentDocumentSplitter,
            query_strategy: str = "multi_query",
            use_llm_reranker: bool = False,
            top_k: int = 3,
            enable_cache: bool = True
    ):
        """
        Args:
            vectorstore: 向量数据库（包含子文档）
            all_documents: 所有子文档列表
            parent_splitter: 父文档切分器（用于映射）
            query_strategy: 查询优化策略
            use_llm_reranker: 是否使用 LLM 重排序
            top_k: 最终返回的文档数量
        """

        self.top_k = top_k

        # 1. 查询优化器
        self.query_optimizer = AdvancedQueryOptimizer(strategy=query_strategy)

        # 2. 混合检索器
        self.retriever = AdvancedHybridRetriever(
            vectorstore=vectorstore,
            documents=all_documents,
            k=top_k * 3  # 先检索更多候选
        )

        # 3. 重排序器
        self.reranker = LLMReranker(top_k=top_k * 2)

        # 4. 父文档映射器
        self.parent_splitter = parent_splitter

        # 5. 长上下文重排序
        self.context_reorder = LongContextReorder()

        # 6. 缓存层
        self.cache = RAGCache(enabled=enable_cache)

    def retrieve(self, query: str) -> List[Document]:
        """
        完整检索流程

        Args:
            query: 用户查询

        Returns:
            优化后的上下文文档列表
        """

        # 尝试从缓存获取
        cached_result = self.cache.get(query, self.top_k)
        if cached_result:
            return cached_result

        app_logger.info(f"✅ 开始 Advanced RAG 检索: {query}")

        # ========== 阶段 1：查询优化 ==========
        optimized_queries = self.query_optimizer.optimize(query)
        app_logger.info(f"1️. 查询优化完成，生成 {len(optimized_queries)} 个查询")

        # ========== 阶段 2：混合检索 ==========
        child_docs = self.retriever.retrieve(
            query=query,
            queries=optimized_queries
        )
        app_logger.info(f"2️. 混合检索完成，获得 {len(child_docs)} 个候选文档")

        # ========== 阶段 3：重排序 ==========
        reranked_child_docs = self.reranker.rerank(
            query=query,
            documents=child_docs,
            top_k=self.top_k * 2
        )
        app_logger.info(f"3️. 重排序完成，保留 {len(reranked_child_docs)} 个文档")

        # ========== 阶段 4：上下文优化 ==========
        # 4.1 映射到父文档
        parent_docs = self.parent_splitter.get_parent_context(reranked_child_docs)
        app_logger.info(f"4️. 父文档映射完成，获得 {len(parent_docs)} 个完整上下文")

        # 4.2 长上下文重排序
        final_docs = self.context_reorder.reorder(parent_docs[:self.top_k])
        app_logger.info(f"✅ RAG 检索完成，最终返回 {len(final_docs)} 个文档")

        # 缓存结果
        self.cache.set(query, self.top_k, final_docs)

        return final_docs