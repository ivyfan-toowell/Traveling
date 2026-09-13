"""
初始化 RAG 系统
加载文档、切分、创建向量数据库
"""
import asyncio
from app.rag.document_loader import DocumentManager
from app.rag.text_splitter import ParentDocumentSplitter
from app.rag.vectorstore import VectorStoreManager
from app.utils.logger import app_logger


async def main():
    """初始化 RAG 系统"""

    app_logger.info("开始初始化 RAG 系统...")

    # ========== 1. 加载文档 ==========
    app_logger.info("加载文档...")
    doc_manager = DocumentManager()
    documents = doc_manager.load_destination_documents()

    if not documents:
        app_logger.error("未找到文档，请先添加文档到 data/documents/destinations/")
        return

    # ========== 2. 切分文档 ==========
    app_logger.info("切分文档...")
    splitter = ParentDocumentSplitter()
    parent_docs, child_docs = splitter.split_documents(documents)

    # ========== 3. 创建向量数据库 ==========
    # 使用子文档创建向量索引（更精细的检索）
    app_logger.info("创建向量数据库...")
    vs_manager = VectorStoreManager()
    vectorstore = vs_manager.create_vectorstore(child_docs)

    # ========== 4. 保存父文档映射（用于后续检索） ==========
    # 在实际应用中，需要将 parent_docs 也存储到数据库
    # 这里简化处理

    app_logger.info("RAG 系统初始化完成！")
    app_logger.info(f"   - 文档数量：{len(documents)}")
    app_logger.info(f"   - 父文档数量：{len(parent_docs)}")
    app_logger.info(f"   - 子文档数量：{len(child_docs)}")
    app_logger.info(f"   - 向量数据库：{vs_manager.persist_directory}")


if __name__ == "__main__":
    asyncio.run(main())