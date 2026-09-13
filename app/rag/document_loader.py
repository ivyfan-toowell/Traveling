"""
文档加载与预处理
"""
from pathlib import Path
from typing import List
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from app.utils.logger import app_logger


class DocumentManager:
    """文档管理器"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # 获取项目根目录 (从当前文件向上找到项目根)
            # document_loader.py -> rag -> app -> 项目根
            project_root = Path(__file__).parent.parent.parent
            self.base_dir = project_root / "data" / "documents"
        else:
            self.base_dir = Path(base_dir)

    def load_destination_documents(self) -> List[Document]:
        """加载所有目的地文档"""

        destinations_dir = self.base_dir / "destinations"

        if not destinations_dir.exists():
            app_logger.warning(f"目的地文档目录不存在: {destinations_dir}")
            return []

        # 加载 Markdown 文件
        loader = DirectoryLoader(
            str(destinations_dir),
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )

        documents = loader.load()
        app_logger.info(f"加载了 {len(documents)} 个目的地文档")

        # 添加元数据
        for doc in documents:
            doc.metadata["source"] = Path(doc.metadata["source"]).relative_to(self.base_dir).as_posix()
            doc.metadata["source_type"] = "destination_guide"
            doc.metadata["category"] = "destinations"

        return documents

    def load_food_documents(self) -> List[Document]:
        """加载美食文档"""
        food_dir = self.base_dir / "food"

        if not food_dir.exists():
            app_logger.warning(f"目的地文档目录不存在: {food_dir}")
            return []

        loader = DirectoryLoader(
            str(food_dir),
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )

        documents = loader.load()
        app_logger.info(f"加载了 {len(documents)} 个目的地文档")

        for doc in documents:
            doc.metadata["source"] = Path(doc.metadata["source"]).relative_to(self.base_dir).as_posix()
            doc.metadata["source_type"] = "food_guide"
            doc.metadata["category"] = "food"

        return documents


    def load_accommodation_documents(self) -> List[Document]:
        """加载住宿文档"""
        accommodation_dir = self.base_dir / "accommodation"

        if not accommodation_dir.exists():
            app_logger.warning(f"目的地文档目录不存在: {accommodation_dir}")
            return []

        loader = DirectoryLoader(
            str(accommodation_dir),
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        documents = loader.load()
        app_logger.info(f"加载了 {len(documents)} 个目的地文档")

        for doc in documents:
            doc.metadata["source"] = Path(doc.metadata["source"]).relative_to(self.base_dir).as_posix()
            doc.metadata["source_type"] = "accommodation"
            doc.metadata["category"] = "accommodation"

        return documents

    def load_all_documents(self) -> List[Document]:
        """按稳定顺序加载三类知识库，供初始化脚本和运行时共用。"""
        documents = [
            *self.load_destination_documents(),
            *self.load_food_documents(),
            *self.load_accommodation_documents(),
        ]
        return sorted(documents, key=lambda doc: doc.metadata["source"])
