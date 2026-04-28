from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from deerflow.agents.middlewares.knowledge_base_middleware import (
    KnowledgeBaseMiddleware,
    _extract_message_text,
    _format_knowledge_context,
)
from deerflow.config.knowledge_search_config import KnowledgeSearchConfig, get_knowledge_search_config, set_knowledge_search_config


def _make_runtime_with_metadata(owner_user_id=None, workspace_id=None):
    mock_config = MagicMock()
    mock_config.metadata = {"owner_user_id": owner_user_id, "workspace_id": workspace_id}
    mock_runtime = MagicMock()
    mock_runtime.config = mock_config
    return mock_runtime


def _set_test_kb_config(**overrides) -> KnowledgeSearchConfig:
    config = KnowledgeSearchConfig(**get_knowledge_search_config().model_dump())
    for key, value in overrides.items():
        setattr(config, key, value)
    set_knowledge_search_config(config)
    return config


class TestExtractMessageText:
    def test_string_content(self):
        msg = MagicMock(content="hello world")
        assert _extract_message_text(msg) == "hello world"

    def test_list_content_with_strings(self):
        msg = MagicMock(content=["hello", "world"])
        assert _extract_message_text(msg) == "hello world"

    def test_list_content_with_dicts(self):
        msg = MagicMock(content=[{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}])
        assert _extract_message_text(msg) == "hello world"

    def test_list_content_mixed(self):
        msg = MagicMock(content=["prefix", {"type": "text", "text": "hello"}])
        assert _extract_message_text(msg) == "prefix hello"

    def test_empty_content(self):
        msg = MagicMock(content="")
        assert _extract_message_text(msg) == ""


class TestFormatKnowledgeContext:
    def test_empty_results(self):
        result = _format_knowledge_context([])
        assert result == ""

    def test_single_result(self):
        results = [
            {
                "document_name": "test.md",
                "chunk_content": "This is a test chunk about authentication.",
                "similarity_score": 0.82,
                "kb_name": "Engineering Wiki",
            }
        ]
        ctx = _format_knowledge_context(results)
        assert "<knowledge_context>" in ctx
        assert "Found 1 relevant knowledge match." in ctx
        assert "[KB: Engineering Wiki]" in ctx
        assert "[Doc: test.md]" in ctx
        assert "[Score: 0.82]" in ctx
        assert "This is a test chunk about authentication." in ctx
        assert "</knowledge_context>" in ctx

    def test_multiple_results_plural(self):
        results = [
            {"document_name": "a.md", "chunk_content": "chunk a", "similarity_score": 0.8, "kb_name": "KB1"},
            {"document_name": "b.md", "chunk_content": "chunk b", "similarity_score": 0.7, "kb_name": "KB2"},
        ]
        ctx = _format_knowledge_context(results)
        assert "Found 2 relevant knowledge matches." in ctx

    def test_truncation_long_chunk(self):
        long_chunk = "x" * 500
        results = [{"document_name": "big.md", "chunk_content": long_chunk, "similarity_score": 0.9, "kb_name": "KB"}]
        ctx = _format_knowledge_context(results)
        assert "..." in ctx
        assert len(ctx) < len(long_chunk) * 2


class TestKnowledgeBaseMiddleware:
    def setup_method(self):
        self._original = get_knowledge_search_config()

    def teardown_method(self):
        set_knowledge_search_config(self._original)

    def test_returns_none_when_disabled(self):
        _set_test_kb_config(enabled=False)
        middleware = KnowledgeBaseMiddleware()
        state = {"messages": [HumanMessage(content="hello")]}
        result = middleware.before_agent(state, MagicMock())
        assert result is None

    def test_returns_none_when_no_messages(self):
        _set_test_kb_config(enabled=True)
        middleware = KnowledgeBaseMiddleware()
        state = {"messages": []}
        result = middleware.before_agent(state, MagicMock())
        assert result is None

    def test_returns_none_when_last_message_not_human(self):
        _set_test_kb_config(enabled=True)
        middleware = KnowledgeBaseMiddleware()
        state = {"messages": [AIMessage(content="hello")]}
        result = middleware.before_agent(state, MagicMock())
        assert result is None

    def test_returns_none_when_no_user_id(self):
        _set_test_kb_config(enabled=True)
        middleware = KnowledgeBaseMiddleware()
        state = {"messages": [HumanMessage(content="hello")]}
        runtime = _make_runtime_with_metadata(owner_user_id=None)
        with patch("deerflow.agents.middlewares.knowledge_base_middleware._get_current_user_id_from_context", return_value=None):
            result = middleware.before_agent(state, runtime)
        assert result is None

    def test_strips_upload_block_before_search(self):
        _set_test_kb_config(enabled=True)
        middleware = KnowledgeBaseMiddleware()
        msg_content = "<uploaded_files><file>doc.pdf</file></uploaded_files>\n\nTell me about authentication"
        state = {"messages": [HumanMessage(content=msg_content)]}
        captured_query = None

        def capture_search(user_id, workspace_id, query, **kwargs):
            nonlocal captured_query
            captured_query = query

            class FakeResult:
                results = []
                kb_count = 0
                searched_kb_count = 0
                duration_ms = 0

            return FakeResult()

        runtime = _make_runtime_with_metadata(owner_user_id="user123", workspace_id="ws1")
        with patch("deerflow.agents.middlewares.knowledge_base_middleware.search_accessible_knowledge_bases", side_effect=capture_search):
            middleware.before_agent(state, runtime)

        assert captured_query is not None
        assert "<uploaded_files>" not in captured_query
        assert "Tell me about authentication" in captured_query

    def test_injects_knowledge_context_string_content(self):
        _set_test_kb_config(enabled=True, top_k=5, similarity_threshold=0.5)
        middleware = KnowledgeBaseMiddleware()
        state = {"messages": [HumanMessage(content="Tell me about auth")]}
        search_results = [{"document_name": "auth.md", "chunk_content": "Auth is done via JWT tokens", "similarity_score": 0.82, "kb_name": "Wiki"}]

        class FakeResult:
            results = search_results
            kb_count = 1
            searched_kb_count = 1
            duration_ms = 50

        runtime = _make_runtime_with_metadata(owner_user_id="user123", workspace_id="ws1")
        with patch("deerflow.agents.middlewares.knowledge_base_middleware.search_accessible_knowledge_bases", return_value=FakeResult()):
            result = middleware.before_agent(state, runtime)

        assert result is not None
        assert "knowledge_context" in result
        assert "<knowledge_context>" in result["knowledge_context"]
        assert "Auth is done via JWT tokens" in result["knowledge_context"]
        assert result["knowledge_results"] == search_results
        assert result["knowledge_search_meta"]["result_count"] == 1
        updated_msg = result["messages"][-1]
        assert "<knowledge_context>" in updated_msg.content
        assert "Tell me about auth" in updated_msg.content

    def test_injects_knowledge_context_list_content(self):
        _set_test_kb_config(enabled=True)
        middleware = KnowledgeBaseMiddleware()
        state = {"messages": [HumanMessage(content=[{"type": "text", "text": "What is OAuth?"}])]}
        search_results = [{"document_name": "oauth.md", "chunk_content": "OAuth 2.0 is a standard", "similarity_score": 0.9, "kb_name": "Sec"}]

        class FakeResult:
            results = search_results
            kb_count = 1
            searched_kb_count = 1
            duration_ms = 30

        runtime = _make_runtime_with_metadata(owner_user_id="user123", workspace_id="ws1")
        with patch("deerflow.agents.middlewares.knowledge_base_middleware.search_accessible_knowledge_bases", return_value=FakeResult()):
            result = middleware.before_agent(state, runtime)

        assert result is not None
        ctx = result["knowledge_context"]
        assert "OAuth 2.0 is a standard" in ctx

    def test_skips_injection_when_no_results(self):
        _set_test_kb_config(enabled=True)

        class FakeResult:
            results = []
            kb_count = 3
            searched_kb_count = 3
            duration_ms = 80

        middleware = KnowledgeBaseMiddleware()
        state = {"messages": [HumanMessage(content="unrelated query")]}
        runtime = _make_runtime_with_metadata(owner_user_id="user123", workspace_id="ws1")
        with patch("deerflow.agents.middlewares.knowledge_base_middleware.search_accessible_knowledge_bases", return_value=FakeResult()):
            result = middleware.before_agent(state, runtime)

        assert result is not None
        assert result["knowledge_context"] is None
        assert result["knowledge_results"] == []
        assert result["knowledge_search_meta"]["result_count"] == 0

    def test_avoids_duplicate_injection(self):
        _set_test_kb_config(enabled=True)
        middleware = KnowledgeBaseMiddleware()
        existing_kb = "<knowledge_context>Old context</knowledge_context>"
        state = {"messages": [HumanMessage(content=f"{existing_kb}\n\nTell me about API")]}

        captured_query = None

        class FakeResult:
            results = []
            kb_count = 0
            searched_kb_count = 0
            duration_ms = 0

        def capture_search(**kwargs):
            nonlocal captured_query
            captured_query = kwargs.get("query", "")
            return FakeResult()

        runtime = _make_runtime_with_metadata(owner_user_id="user123", workspace_id="ws1")
        with patch("deerflow.agents.middlewares.knowledge_base_middleware.search_accessible_knowledge_bases", side_effect=capture_search):
            middleware.before_agent(state, runtime)

        assert captured_query is not None
        assert "Old context" not in captured_query
        assert "Tell me about API" in captured_query

    def test_handles_search_exception_gracefully(self):
        _set_test_kb_config(enabled=True)
        middleware = KnowledgeBaseMiddleware()
        state = {"messages": [HumanMessage(content="query")]}
        runtime = _make_runtime_with_metadata(owner_user_id="user123", workspace_id="ws1")
        with patch("deerflow.agents.middlewares.knowledge_base_middleware.search_accessible_knowledge_bases", side_effect=RuntimeError("DB error")):
            result = middleware.before_agent(state, runtime)
        assert result is None

    def test_max_context_chars_truncation(self):
        _set_test_kb_config(enabled=True, max_context_chars=200)
        middleware = KnowledgeBaseMiddleware()
        long_chunk = "x" * 500
        search_results = [{"document_name": "big.md", "chunk_content": long_chunk, "similarity_score": 0.9, "kb_name": "KB"}]

        class FakeResult:
            results = search_results
            kb_count = 1
            searched_kb_count = 1
            duration_ms = 10

        state = {"messages": [HumanMessage(content="test")]}
        runtime = _make_runtime_with_metadata(owner_user_id="user123", workspace_id="ws1")
        with patch("deerflow.agents.middlewares.knowledge_base_middleware.search_accessible_knowledge_bases", return_value=FakeResult()):
            result = middleware.before_agent(state, runtime)

        assert result is not None
        assert "...(truncated)" in result["knowledge_context"]
        assert len(result["knowledge_context"]) <= 200 + len("\n...(truncated)")
