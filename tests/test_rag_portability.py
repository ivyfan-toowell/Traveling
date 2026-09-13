"""离线验证知识库可移植性和 Chroma 索引同步，不调用云端 API。"""
import os
from collections import Counter
from shutil import copytree

# 测试只使用本地模拟向量；避免要求测试机器持有作者的配置。
os.environ.setdefault("DASHSCOPE_API_KEY", "offline-test-placeholder")
os.environ.setdefault("POSTGRES_DB", "offline_test")
os.environ.setdefault("POSTGRES_USER", "offline_test")
os.environ.setdefault("POSTGRES_PASSWORD", "offline_test")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ["DEBUG"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from app.rag.document_loader import DocumentManager
from app.rag.text_splitter import AdvancedParentDocumentSplitter
from app.rag import vectorstore as vectorstore_module


class OfflineEmbeddings(Embeddings):
    def __init__(self):
        self.calls = 0
        self.fail = False

    def embed_documents(self, texts):
        if self.fail:
            raise RuntimeError("simulated embedding failure")
        self.calls += 1
        return [[float(len(text)), float(sum(map(ord, text)) % 97), 1.0] for text in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


@pytest.fixture
def manager(tmp_path, monkeypatch):
    embeddings = OfflineEmbeddings()
    monkeypatch.setattr(vectorstore_module, "DashScopeEmbeddings", lambda **kwargs: embeddings)
    result = vectorstore_module.VectorStoreManager(str(tmp_path / "index"))
    return result, embeddings


def test_all_categories_and_parent_ids_survive_relocation(tmp_path):
    original = DocumentManager().load_all_documents()
    assert Counter(doc.metadata["category"] for doc in original) == {
        "destinations": 8, "food": 8, "accommodation": 8,
    }
    copytree(DocumentManager().base_dir, tmp_path / "relocated")
    relocated = DocumentManager(str(tmp_path / "relocated")).load_all_documents()
    assert [(d.page_content, d.metadata) for d in original] == [(d.page_content, d.metadata) for d in relocated]
    first, second = AdvancedParentDocumentSplitter(), AdvancedParentDocumentSplitter()
    _, indexed_children = first.split_documents(original)
    _, reloaded_children = second.split_documents(relocated)
    assert [d.metadata["child_id"] for d in indexed_children] == [d.metadata["child_id"] for d in reloaded_children]
    assert second.get_parent_context(indexed_children[:3])


def test_empty_chroma_is_populated_and_repeat_does_not_embed(manager):
    index, embeddings = manager
    assert index.load_vectorstore().get(include=[])["ids"] == []
    docs = [Document(page_content="成都景点", metadata={"source": "destinations/chengdu.md"})]
    store = index.create_vectorstore(docs)
    assert len(store.get(include=[])["ids"]) == 1
    calls = embeddings.calls
    index.create_vectorstore(docs)
    assert embeddings.calls == calls
    assert len(store.get(include=[])["ids"]) == 1


def test_update_and_removal_synchronize_existing_collection(manager):
    index, _ = manager
    store = index.create_vectorstore([
        Document(page_content="旧景点信息", metadata={"source": "destinations/a.md"}),
        Document(page_content="将删除的住宿", metadata={"source": "accommodation/b.md"}),
    ])
    assert len(store.get(include=[])["ids"]) == 2
    index.create_vectorstore([Document(page_content="更新后的景点", metadata={"source": "destinations/a.md"})])
    assert store.get()["documents"] == ["更新后的景点"]


def test_embedding_failure_preserves_previous_index(manager):
    index, embeddings = manager
    store = index.create_vectorstore([Document(page_content="已存在的内容")])
    embeddings.fail = True
    with pytest.raises(RuntimeError, match="simulated embedding failure"):
        index.create_vectorstore([Document(page_content="新内容")])
    assert store.get()["documents"] == ["已存在的内容"]


def test_empty_knowledge_base_is_an_explicit_error(manager):
    index, embeddings = manager
    with pytest.raises(RuntimeError, match="知识库为空"):
        index.create_vectorstore([])
    assert embeddings.calls == 0


def test_default_vectorstore_path_does_not_depend_on_cwd(tmp_path, monkeypatch):
    monkeypatch.setattr(vectorstore_module, "DashScopeEmbeddings", lambda **kwargs: OfflineEmbeddings())
    monkeypatch.setattr(vectorstore_module, "BASE_DIR", str(tmp_path / "project"))
    monkeypatch.chdir(tmp_path)
    index = vectorstore_module.VectorStoreManager()
    assert index.persist_directory == tmp_path / "project" / "data" / "vectorstore"


def test_cache_keys_change_when_knowledge_base_changes():
    from app.rag.cache import RAGCache
    before = RAGCache(enabled=False, namespace="before-edit")
    after = RAGCache(enabled=False, namespace="after-edit")
    assert before._generate_key("成都景点", 3) != after._generate_key("成都景点", 3)


@pytest.mark.asyncio
async def test_optional_mcp_failure_keeps_available_tools(monkeypatch):
    from app.mcp_core import client as client_module

    for key in ("AMAP_API_KEY", "VARIFLIGHT_API_KEY", "AIGOHOTEL_MCP_API"):
        monkeypatch.delenv(key, raising=False)

    class OfflineClient:
        def __init__(self, configs):
            assert set(configs) == {"weather", "search", "12306-mcp"}

        async def get_tools(self, *, server_name):
            if server_name == "12306-mcp":
                raise ConnectionError("offline remote service")
            return [f"available-{server_name}-tool"]

    monkeypatch.setattr(client_module, "MultiServerMCPClient", OfflineClient)
    manager = client_module.MCPClientManager()
    await manager.initialize()
    assert await manager.get_tools() == ["available-weather-tool", "available-search-tool"]


def test_frontend_and_health_routes_without_starting_external_services():
    from fastapi.testclient import TestClient
    from app.main import app

    # 不使用上下文管理器，避免启动依赖真实数据库和 MCP 的 lifespan。
    client = TestClient(app)
    home = client.get("/")
    assert home.status_code == 200
    assert "text/html" in home.headers["content-type"]
    assert "chatMessages" in home.text
    assert client.get("/health").json()["status"] == "healthy"
