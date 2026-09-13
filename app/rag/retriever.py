"""
混合检索器：BM25 + Dense + RRF 融合（优化版）
"""
from typing import List, Tuple
from collections import defaultdict
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from app.utils.logger import app_logger


class AdvancedHybridRetriever:
    """
    高级混合检索器

    改进点：
    1. 支持查询优化
    2. 权重可配置
    3. 缓存机制
    """

    def __init__(
            self,
            vectorstore: Chroma,
            documents: List[Document],
            k: int = 5,
            bm25_weight: float = 0.4,
            dense_weight: float = 0.6,
            use_cache: bool = True
    ):
        self.vectorstore = vectorstore
        self.documents = documents
        self.k = k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self.use_cache = use_cache

        # 缓存
        self._cache = {} if use_cache else None

        # 初始化 BM25
        self._init_bm25()

    def _init_bm25(self):
        """初始化 BM25 索引"""

        app_logger.info("🔧 初始化 BM25 索引...")

        # 创建 BM25 检索器
        self.bm25_retriever = BM25Retriever.from_documents(self.documents)
        self.bm25_retriever.k = self.k * 2

        app_logger.info("✅ BM25 索引初始化完成")

    def _bm25_search(self, query: str, k: int) -> List[Document]:
        """BM25 检索"""
        return self.bm25_retriever.invoke(query)[:k]

    def _dense_search(self, query: str, k: int) -> List[Tuple[Document, float]]:
        """Dense 检索（向量相似度）"""
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        #Chroma中默认使用L2距离，这样输出的distance是无上限的，而我们希望把其控制在0到1之间，也就是相似度
        # Chroma 返回的是 (doc, distance)，需要转换为 (doc, similarity)
        similarity_results = [
            (doc, 1 / (1 + distance))
            for doc, distance in results
        ]

        return similarity_results

    def _rrf_fusion(
            self,
            bm25_results: List[Document],
            dense_results: List[Tuple[Document, float]],
            k: int = 60
    ) -> List[Document]:
        """
        倒数排名融合（Reciprocal Rank Fusion）

        公式：RRF_score(d) = Σ 1/(k + rank_r(d))
        """

        scores = defaultdict(float)
        doc_map = {}

        # BM25 贡献
        for rank, doc in enumerate(bm25_results, 1):
            doc_id = hash(doc.page_content[:200])
            doc_map[doc_id] = doc
            scores[doc_id] += self.bm25_weight * (1 / (k + rank))

        # Dense 贡献
        for rank, (doc, score) in enumerate(dense_results, 1):
            doc_id = hash(doc.page_content[:200])
            doc_map[doc_id] = doc
            scores[doc_id] += self.dense_weight * (1 / (k + rank))

        # 排序
        sorted_docs = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [doc_map[doc_id] for doc_id, _ in sorted_docs[:self.k]]

    def retrieve(self, query: str, queries: List[str] = None) -> List[Document]:
        """
        混合检索

        Args:
            query: 主查询
            queries: 可选的查询变体（来自查询优化）

        Returns:
            检索结果列表
        """

        # 检查缓存
        if self.use_cache and query in self._cache:
            app_logger.info("命中缓存")
            return self._cache[query]

        # 如果提供了查询变体，合并结果
        if queries and len(queries) > 1:
            app_logger.info(f"使用 {len(queries)} 个查询变体进行检索")
            all_results = []

            for q in queries:
                results = self._single_retrieve(q)
                all_results.extend(results)

            # 去重并重新排序
            seen = set()
            unique_results = []
            for doc in all_results:
                doc_id = hash(doc.page_content[:200])
                if doc_id not in seen:
                    seen.add(doc_id)
                    unique_results.append(doc)

            final_results = unique_results[:self.k]
        else:
            final_results = self._single_retrieve(query)

        # 缓存结果
        if self.use_cache:
            self._cache[query] = final_results

        return final_results

    def _single_retrieve(self, query: str) -> List[Document]:
        """单个查询的检索"""

        # BM25 检索
        bm25_results = self._bm25_search(query, k=self.k * 2)
        app_logger.debug(f"BM25 检索到 {len(bm25_results)} 个候选")

        # Dense 检索
        dense_results = self._dense_search(query, k=self.k * 2)
        app_logger.debug(f"Dense 检索到 {len(dense_results)} 个候选")

        # RRF 融合
        fused_docs = self._rrf_fusion(bm25_results, dense_results)

        app_logger.info(f"混合检索完成，返回 {len(fused_docs)} 个结果")

        return fused_docs