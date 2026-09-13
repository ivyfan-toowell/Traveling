"""
初始化 RAG 系统
加载文档、切分、创建向量数据库
"""
import asyncio
from app.rag.document_loader import DocumentManager
from app.rag.text_splitter import AdvancedParentDocumentSplitter
from app.rag.vectorstore import VectorStoreManager
from app.utils.logger import app_logger


async def main():
    """初始化 RAG 系统"""

    app_logger.info("开始初始化 RAG 系统...")

    # ========== 1. 加载文档 ==========
    app_logger.info("加载文档...")
    doc_manager = DocumentManager()
    documents = doc_manager.load_all_documents()

    if not documents:
        raise RuntimeError("知识库为空，请先添加 UTF-8 Markdown 文件到 data/documents/ 的三类目录")

    # ========== 2. 切分文档 ==========
    app_logger.info("切分文档...")
    splitter = AdvancedParentDocumentSplitter()
    parent_docs, child_docs = splitter.split_documents(documents)

    # ========== 3. 创建向量数据库 ==========
    # 使用子文档创建向量索引（更精细的检索）
    app_logger.info("创建向量数据库...")
    vs_manager = VectorStoreManager()
    vectorstore = vs_manager.create_vectorstore(child_docs)

    # ========== 4. 保存父文档映射（用于后续检索） ==========
    # 父文档映射在运行时从同一批 MD 重新生成；source 使用相对路径，支持不同机器。

    app_logger.info("RAG 系统初始化完成！")
    app_logger.info(f"   - 文档数量：{len(documents)}")
    app_logger.info(f"   - 父文档数量：{len(parent_docs)}")
    app_logger.info(f"   - 子文档数量：{len(child_docs)}")
    app_logger.info(f"   - 向量数据库：{vs_manager.persist_directory}")


if __name__ == "__main__":
    asyncio.run(main())
