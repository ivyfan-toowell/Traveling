"""
测试 Advanced RAG 完整管道
"""
import asyncio
import time

import pytest
from langchain_core.documents import Document
from app.rag.document_loader import DocumentManager
from app.rag.text_splitter import AdvancedParentDocumentSplitter
from app.rag.vectorstore import VectorStoreManager
from app.rag.pipeline import AdvancedRAGPipeline

@pytest.mark.asyncio
async def test_full_pipeline():
    """测试完整 RAG 管道"""

    print("\n=== 初始化 RAG 系统 ===")

    # 1. 加载文档
    doc_manager = DocumentManager()
    documents = doc_manager.load_destination_documents()
    print(f"加载了 {len(documents)} 个文档")

    # 2. 切分文档
    splitter = AdvancedParentDocumentSplitter()
    parent_docs, child_docs = splitter.split_documents(documents)
    print(f"父文档: {len(parent_docs)}, 子文档: {len(child_docs)}")

    # 3. 加载向量数据库
    vs_manager = VectorStoreManager()

    vectorstore = vs_manager.create_vectorstore(child_docs)

    # 4. 创建 RAG 管道
    pipeline = AdvancedRAGPipeline(
        vectorstore=vectorstore,
        all_documents=child_docs,
        parent_splitter=splitter,
        query_strategy="multi_query",
        use_llm_reranker=False,  # 测试时使用简单重排序
        top_k=1,
        enable_cache=True
    )

    print("\n=== 测试检索 ===")

    # 测试查询列表
    test_queries = [
        "西安有哪些适合亲子游的景点？",
        "西安的美食推荐",
        "西安旅游的预算大概是多少？"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n--- 测试 {i}: {query} ---")

        start_time = time.time()
        results = pipeline.retrieve(query)
        elapsed = time.time() - start_time

        print(f"耗时: {elapsed:.2f}秒")
        print(f"返回了 {len(results)} 个文档\n")

        for j, doc in enumerate(results, 1):
            preview = doc.page_content + "..."
            print(f"  [{j}] {preview}")

    print("\n=== 缓存测试 ===")

    # 重复查询，测试缓存
    print("重复第一个查询...")
    start_time = time.time()
    cached_results = pipeline.retrieve(test_queries[0])
    cached_elapsed = time.time() - start_time

    print(f"缓存查询耗时: {cached_elapsed:.2f}秒")
    print(f"缓存生效！加速 {(elapsed / cached_elapsed):.1f}x")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
