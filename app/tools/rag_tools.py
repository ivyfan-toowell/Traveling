"""
RAG 检索工具
将 Advanced RAG 管道封装为 Agent 可自主调用的工具
"""
import asyncio
from typing import Optional
from langchain.tools import tool
from langchain_core.tools import ToolException
from app.rag.pipeline import AdvancedRAGPipeline
from app.rag.document_loader import DocumentManager
from app.rag.text_splitter import AdvancedParentDocumentSplitter
from app.rag.vectorstore import VectorStoreManager
from app.utils.logger import app_logger


# ============== 全局 RAG 管道实例（懒加载） ==============

_rag_pipeline: Optional[AdvancedRAGPipeline] = None
_parent_splitter: Optional[AdvancedParentDocumentSplitter] = None
_rag_lock = asyncio.Lock()


async def _get_rag_pipeline() -> AdvancedRAGPipeline:
    """获取或初始化全局 RAG 管道实例（单例模式）"""
    global _rag_pipeline

    if _rag_pipeline is None:
        async with _rag_lock:
            if _rag_pipeline is None:
                _rag_pipeline = await asyncio.to_thread(_build_rag_pipeline)

    return _rag_pipeline


def _build_rag_pipeline() -> AdvancedRAGPipeline:
    """在工作线程中构建同步 RAG 组件，避免阻塞 SSE 事件循环。"""
    global _parent_splitter

    app_logger.info("🔧 初始化 RAG 管道...")

    # 1. 加载文档
    doc_manager = DocumentManager()
    documents = [
        *doc_manager.load_destination_documents(),
        *doc_manager.load_food_documents(),
        *doc_manager.load_accommodation_documents(),
    ]

    if not documents:
        app_logger.warning("⚠️ 未找到知识库文档，RAG 功能不可用")

    # 2. 切分文档
    _parent_splitter = AdvancedParentDocumentSplitter()
    _, child_docs = _parent_splitter.split_documents(documents)

    # 3. 加载或创建向量数据库
    vs_manager = VectorStoreManager()
    try:
        vectorstore = vs_manager.load_vectorstore()
        app_logger.info("✅ 向量数据库加载成功")
    except Exception as exc:
        app_logger.warning(f"向量数据库加载失败，将重新创建: {exc}")
        if not child_docs:
            raise RuntimeError("知识库为空，无法创建向量数据库") from exc
        vectorstore = vs_manager.create_vectorstore(child_docs)

    # 4. 创建 RAG 管道
    pipeline = AdvancedRAGPipeline(
        vectorstore=vectorstore,
        all_documents=child_docs,
        parent_splitter=_parent_splitter,
        query_strategy="multi_query",
        use_llm_reranker=False,
        top_k=3,
        enable_cache=True
    )

    app_logger.info("✅ RAG 管道初始化完成")
    return pipeline


def _format_rag_results(documents: list, query: str) -> str:
    """格式化 RAG 检索结果"""
    if not documents:
        return f"未找到与「{query}」相关的信息。"

    result_parts = []
    for i, doc in enumerate(documents, 1):
        content = doc.page_content[:800]
        if len(doc.page_content) > 800:
            content += "..."

        source = doc.metadata.get("source", "未知来源")
        result_parts.append(f"【资料 {i}】\n{content}\n来源：{source}")

    return "\n\n".join(result_parts)


# ============== RAG 检索工具定义 ==============

@tool
async def search_destination_guide(query: str) -> str:
    """
    从旅游攻略知识库中检索目的地相关信息。

    当你需要获取以下信息时应该使用此工具：
    - 目的地的景点介绍、门票价格、开放时间
    - 旅游攻略、游玩建议、推荐路线
    - 目的地的交通指南、住宿区域推荐
    - 任何需要从知识库获取的旅游相关信息

    Args:
        query: 检索查询，例如 "西安兵马俑门票和游玩建议"、"成都必去景点推荐"

    Returns:
        检索到的相关攻略信息，如果没有找到会返回提示信息
    """
    app_logger.info(f"RAG 工具被调用: {query}")

    try:
        pipeline = await _get_rag_pipeline()
        documents = await asyncio.to_thread(pipeline.retrieve, query)
        result = _format_rag_results(documents, query)
        app_logger.info(f"✅ RAG 检索完成，返回 {len(documents)} 个文档")
        return result
    except Exception as e:
        app_logger.error(f"❌ RAG 检索失败: {e}")
        raise ToolException(f"检索过程中出现错误：{str(e)}")


@tool
async def search_food_recommendations(query: str) -> str:
    """
    从美食知识库中检索目的地美食信息。

    当你需要获取以下信息时应该使用此工具：
    - 目的地的特色美食、必吃小吃
    - 餐厅推荐、美食街区
    - 菜品价格参考

    Args:
        query: 美食相关查询，例如 "西安特色美食推荐"、"成都火锅哪家好"

    Returns:
        检索到的美食推荐信息
    """
    app_logger.info(f"美食检索工具被调用: {query}")

    try:
        pipeline = await _get_rag_pipeline()
        # 增强查询，确保聚焦美食
        enhanced_query = f"{query} 美食 餐厅 小吃"
        documents = await asyncio.to_thread(pipeline.retrieve, enhanced_query)
        return _format_rag_results(documents, query)
    except Exception as e:
        app_logger.error(f"❌ 美食检索失败: {e}")
        raise ToolException(f"检索过程中出现错误：{str(e)}")


@tool
async def search_accommodation_info(query: str) -> str:
    """
    从住宿知识库中检索目的地住宿信息。

    当你需要获取以下信息时应该使用此工具：
    - 目的地的住宿区域推荐
    - 不同类型住宿的特点和价格范围
    - 酒店/民宿选择建议

    Args:
        query: 住宿相关查询，例如 "西安住哪个区域好"、"成都民宿推荐"

    Returns:
        检索到的住宿推荐信息
    """
    app_logger.info(f"住宿检索工具被调用: {query}")

    try:
        pipeline = await _get_rag_pipeline()
        enhanced_query = f"{query} 住宿 酒店 民宿"
        documents = await asyncio.to_thread(pipeline.retrieve, enhanced_query)
        return _format_rag_results(documents, query)
    except Exception as e:
        app_logger.error(f"❌ 住宿检索失败: {e}")
        raise ToolException(f"检索过程中出现错误：{str(e)}")


@tool
async def search_travel_tips(query: str) -> str:
    """
    从知识库中检索旅行实用信息和注意事项。

    当你需要获取以下信息时应该使用此工具：
    - 目的地的旅行注意事项、避坑指南
    - 最佳旅游季节、穿衣建议
    - 当地交通、消费水平等实用信息

    Args:
        query: 实用信息查询，例如 "西安旅游注意事项"、"成都几月去最好"

    Returns:
        检索到的旅行实用信息
    """
    app_logger.info(f"旅行贴士检索工具被调用: {query}")

    try:
        pipeline = await _get_rag_pipeline()
        enhanced_query = f"{query} 注意事项 建议 提示"
        documents = await asyncio.to_thread(pipeline.retrieve, enhanced_query)
        return _format_rag_results(documents, query)
    except Exception as e:
        app_logger.error(f"❌ 旅行贴士检索失败: {e}")
        raise ToolException(f"检索过程中出现错误：{str(e)}")


# ============== 工具集合 ==============

def get_rag_tools() -> list:
    """获取所有 RAG 相关工具"""
    return [
        search_destination_guide,
        search_food_recommendations,
        search_accommodation_info,
        search_travel_tips,
    ]
