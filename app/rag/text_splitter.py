from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Tuple, Dict
from langchain_core.documents import Document
from app.utils.logger import app_logger


class AdvancedParentDocumentSplitter:
    """
    高级父文档切分器

    改进点：
    1. 维护父子文档映射表
    2. 支持上下文检索
    """
    def __init__(
            self,
            parent_chunk_size:int = 1000,
            parent_chunk_overlap:int  = 200,
            child_chunk_size:int = 200,
            child_chunk_overlap:int = 50
    ):

        self.parent_spiltter = RecursiveCharacterTextSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=parent_chunk_overlap,
            separators=["\n\n","\n","。",","," ",""]
        )

        self.child_spiltter = RecursiveCharacterTextSplitter(
            chunk_size=child_chunk_size,
            chunk_overlap=child_chunk_overlap,
            separators=["\n\n", "\n", "。", ",", " ", ""]
        )

        # 父子映射表
        self.parent_child_map: Dict[str, str] = {}  # child_id -> parent_id
        self.parent_docs: Dict[str, Document] = {}  # parent_id -> Document


    def split_documents(
            self,
            documents: List[Document]
    ) -> Tuple[List[Document], List[Document]]:
        """
        切分文档为父文档和子文档

        返回：
        (parent_docs, child_docs)
        """

        parent_docs = []
        child_docs = []

        for doc in documents:
            parent_chunks = self.parent_spiltter.split_documents([doc])

            for i, parent_chunk in enumerate(parent_chunks):
                parent_id = f"{doc.metadata.get('source','unknown')}_parent_{i}"
                parent_chunk.metadata["parent_id"] = parent_id
                parent_chunk.metadata["chunk_type"] = "parent"
                parent_docs.append(parent_chunk)

                # 保存父文档
                self.parent_docs[parent_id] = parent_chunk

                child_chunks = self.child_spiltter.split_documents([parent_chunk])

                for j, child_chunk in enumerate(child_chunks):
                    child_id = f"{parent_id}__child_{j}"
                    child_chunk.metadata["child_id"] = child_id
                    child_chunk.metadata["parent_id"] = parent_id
                    child_chunk.metadata["chunk_type"] = "child"
                    child_docs.append(child_chunk)

                    # 建立映射
                    self.parent_child_map[child_id] = parent_id

        app_logger.info(
            f"切分完成: {len(parent_docs)} 个父文档, "
            f"{len(child_docs)} 个子文档"
        )

        return parent_docs, child_docs

    def get_parent_context(self, child_docs: List[Document]) -> List[Document]:
        """
        根据子文档获取对应的父文档（完整上下文）

        Args:
            child_docs: 检索到的子文档列表

        Returns:
            对应的父文档列表（去重）
        """

        app_logger.info(f"映射到父文档: {len(child_docs)} 个子文档")

        parent_ids = set()
        parent_contexts = []

        for child_doc in child_docs:
            parent_id = child_doc.metadata.get("parent_id")

            if parent_id and parent_id not in parent_ids:
                parent_ids.add(parent_id)

                # 从映射表获取父文档
                parent_doc = self.parent_docs.get(parent_id)
                if parent_doc:
                    parent_contexts.append(parent_doc)

        app_logger.info(f"获取了 {len(parent_contexts)} 个父文档")

        return parent_contexts



































