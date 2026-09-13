"""
重排序器：使用 LLM 对检索结果重新排序
"""
import os
from typing import List, Tuple
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.utils.logger import app_logger

load_dotenv()

model = ChatTongyi(
    model="qwen-turbo",  # 使用轻量级模型
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0,  # 重排序需要确定性
)


# ============== 结构化输出模型 ==============

class RelevanceScore(BaseModel):
    """相关性评分"""
    document_index: int = Field(description="文档索引（从0开始）")
    relevance_score: int = Field(description="相关性得分（0-10）", ge=0, le=10)
    reason: str = Field(description="打分理由（简短）")


class RerankingResult(BaseModel):
    """重排序结果"""
    scores: List[RelevanceScore] = Field(description="所有文档的评分列表")


# ============== LLM Reranker ==============

class LLMReranker:
    """
    LLM 重排序器

    使用 LLM 为每个文档打分，然后重新排序
    """

    def __init__(self, top_k: int = 3):
        self.top_k = top_k

        # 定义提示模板
        self.prompt = ChatPromptTemplate.from_template(
            """你是一个文档相关性评估专家。请评估以下文档与用户查询的相关性。

用户查询：{query}

文档列表：
{documents}

任务：为每个文档打分（0-10分），10分表示完全相关，0分表示完全不相关。

评分标准：
- 10分：完美回答查询，信息准确完整
- 7-9分：大部分相关，有用信息较多
- 4-6分：部分相关，有一定参考价值
- 1-3分：相关性很低，几乎没有帮助
- 0分：完全不相关

请返回一个 JSON 对象，包含每个文档的评分和理由。"""
        )

        # 使用结构化输出
        self.structured_model = model.with_structured_output(RerankingResult)

    def rerank(
            self,
            query: str,
            documents: List[Document],
            top_k: int = None
    ) -> List[Document]:
        """
        重排序文档

        Args:
            query: 用户查询
            documents: 待排序的文档列表
            top_k: 返回前 k 个（可选）

        Returns:
            重新排序后的文档列表
        """

        if not documents:
            return []

        top_k = top_k or self.top_k

        app_logger.info(f"开始重排序 {len(documents)} 个文档...")

        # 格式化文档列表
        doc_texts = []
        for i, doc in enumerate(documents):
            content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            doc_texts.append(f"[文档 {i}]\n{content_preview}\n")

        documents_str = "\n".join(doc_texts)

        # 调用 LLM 打分
        messages = self.prompt.format_messages(
            query=query,
            documents=documents_str
        )

        try:
            result: RerankingResult = self.structured_model.invoke(messages)

            # 按分数排序
            sorted_scores = sorted(
                result.scores,
                key=lambda x: x.relevance_score,
                reverse=True
            )

            # 返回前 top_k 个文档
            reranked_docs = []
            for score_item in sorted_scores[:top_k]:
                idx = score_item.document_index
                if 0 <= idx < len(documents):
                    reranked_docs.append(documents[idx])
                    app_logger.debug(
                        f"  [{idx}] 得分: {score_item.relevance_score}/10 - {score_item.reason}"
                    )

            app_logger.info(f"✅ 重排序完成，返回 {len(reranked_docs)} 个文档")

            return reranked_docs

        except Exception as e:
            app_logger.error(f"❌ 重排序失败: {e}，返回原始顺序")
            return documents[:top_k]


class LongContextReorder:
    """
    长上下文重排序

    基于"Lost in the Middle"研究：
    - 最相关的文档放在开头
    - 次相关的放在结尾
    - 不太相关的放在中间
    """

    @staticmethod
    def reorder(documents: List[Document]) -> List[Document]:
        """
        重排序文档列表

        策略：
        - 第1个文档：最相关
        - 最后1个文档：第2相关
        - 中间文档：按降序排列
        """
        if len(documents) <=2:
            return documents

        app_logger.info(f"🔀 长上下文重排序: {len(documents)} 个文档")

        odd_rank = []
        even_rank = []

        for i, doc in enumerate(documents):
            if i % 2 == 0:
                odd_rank.append(doc)
            else:
                even_rank.append(doc)

        reordered = odd_rank + even_rank[::-1]

        order = [i for i, _ in reordered]

        app_logger.debug(f"重排序后顺序:  {order}")

        return reordered


































