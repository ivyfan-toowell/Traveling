"""
查询优化模块
包含 Multi-Query、HyDE、查询改写等策略
"""
import os
from typing import List
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from app.utils.logger import app_logger
from langchain_community.chat_models import ChatTongyi
from app.config import settings

load_dotenv()

model = ChatTongyi(
    model = "qwen-turbo",
    api_key = settings.dashscope_api_key,
    temperature = 0
)


# optimize 优化
class MultiQueryOptimizer:
    """
    Multi-Query 优化器
    生成查询的多个变体以提高召回率
    """
    def __init__(self, num_variants: int = 3):
        self.num_variants = num_variants

        self.prompt = ChatPromptTemplate.from_template(
            """你是一个查询优化专家。给定一个用户查询，生成 {num} 个语义相似但表述不同的查询变体。
    
            原始查询：{query}
    
            要求：
            1. 保持原查询的核心意图
            2. 使用不同的词汇和表述方式
            3. 考虑同义词、相关概念
            4. 每一行一个变体，不要编号
    
            变体列表："""
        )

    def optimize(self, query: str) -> List[str]:
        """
        生成查询变体

        Args:
            query: 原始查询

        Returns:
            包含原始查询和变体的列表
        """
        app_logger.info(f"生成查询变体: {query}")

        messages = self.prompt.format_messages(
            query = query,
            num = self.num_variants
        )
        response = model.invoke(messages)

        variants = [line.strip() for line in response.content.strip().split("\n") if line.strip()]

        all_queries = [query] + variants[:self.num_variants]

        app_logger.debug(f"生成了 {len(all_queries)} 个查询变体")

        for i, q in enumerate(all_queries):
            app_logger.debug(f"  {i + 1}. {q}")

        return all_queries

if __name__ == "__main__":
    optimizer = MultiQueryOptimizer(num_variants = 3)

    original_query = "西安有哪些适合亲子游的景点？"
    variants = optimizer.optimize(original_query)

    print("\n=== Multi-Query 优化结果 ===")
    for i, q in enumerate(variants, 1):
        print(f"{i}. {q}")







class HyDEOptimizer:
    """
    HyDE (Hypothetical Document Embeddings) 优化器
    生成假设性文档用于检索
    """

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_template(
            """请根据以下问题，生成一段假设性的回答文档。这个文档应该包含可能的答案内容。
    
            问题：{query}
    
            要求：
            1. 200-300 字
            2. 包含具体的景点名称、特点、推荐理由
            3. 使用旅游攻略的语言风格
    
            假设性文档："""
        )

    def generate_hypothetical_doc(self, query: str) -> str:
        """
        生成假设性回答

        Args:
            query: 原始查询

        Returns:
            假设性回答文本
        """
        app_logger.info(f"生成假设性回答: {query}")

        messages = self.prompt.format_messages(query = query)
        response = model.invoke(messages)

        hypothetical_doc = response.content.strip()

        app_logger.debug(f"假设性文档: {hypothetical_doc[:100]}...")

        return hypothetical_doc

if __name__ == "__main__":
    hyde = HyDEOptimizer()

    query = "西安有哪些适合亲子游的景点？"
    doc = hyde.generate_hypothetical_doc(query)

    print("\n=== HyDE 生成的假设性文档 ===")
    print(doc)







class QueryRewriter:
    """
    查询改写器
    修正错别字、口语化表达
    """

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_template(
            """你是一个查询改写专家。请将用户的口语化查询改写为更规范的书面表达。
    
            原始查询：{query}
    
            要求：
            1. 修正错别字
            2. 将口语转为书面语
            3. 保持查询意图不变
            4. 只返回改写后的查询，不要解释
    
            改写后："""
        )
    def rewrite(self, query: str) -> str:
        """
        改写查询

        Args:
            query: 原始查询

        Returns:
            改写后的查询
        """

        app_logger.info(f"改写查询: {query}")

        messages = self.prompt.format_messages(query = query)
        response = model.invoke(messages)

        rewritten = response.content.strip()

        app_logger.debug(f"改写结果: {rewritten}")

        return rewritten




class AdvancedQueryOptimizer():
    """
    综合查询优化器
    整合 Multi-Query、HyDE、查询改写
    """
    def __init__(self, strategy: str = "multi_query"):
        """
        Args:
            strategy: 优化策略
                - "multi_query": 使用 Multi-Query
                - "hyde": 使用 HyDE
                - "rewrite": 使用查询改写
                - "hybrid": 组合使用
        """

        self.strategy = strategy
        self.multi_query = MultiQueryOptimizer()
        self.hyde = HyDEOptimizer()
        self.rewrite = QueryRewriter()

    def optimize(self, query: str) -> List[str]:
        """
        根据策略优化查询

        Returns:
            优化后的查询列表
        """

        if self.strategy == "multi_query":
            return self.multi_query.optimize(query)

        elif self.strategy == "hyde":
            hypothetical_doc = self.hyde.generate_hypothetical_doc(query)
            return [query, hypothetical_doc]

        elif self.strategy == "rewrite":
            rewritten = self.rewriter.rewrite(query)
            return [rewritten]

        elif self.strategy == "hybrid":
            rewritten = self.rewriter.rewrite(query)
            variants = self.multi_query.optimize(rewritten)
            return variants

        else:
            app_logger.warning(f"未知策略: {self.strategy}，使用原始查询")
            return [query]





























