import logging
import re
from typing import Any, NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from deerflow.auth_context import get_current_user_id as _get_current_user_id_from_context
from deerflow.config.knowledge_search_config import get_knowledge_search_config
from deerflow.knowledge.service import search_accessible_knowledge_bases

logger = logging.getLogger(__name__)

_UPLOAD_BLOCK_RE = re.compile(r"<uploaded_files>[\s\S]*?</uploaded_files>\n*", re.IGNORECASE)
_KB_CONTEXT_RE = re.compile(r"<knowledge_context>[\s\S]*?</knowledge_context>\n*", re.IGNORECASE)
_TRUNCATE_CHARS = 400


class KnowledgeBaseMiddlewareState(AgentState):
    knowledge_context: NotRequired[str | None]
    knowledge_results: NotRequired[list[dict[str, Any]] | None]
    knowledge_search_meta: NotRequired[dict[str, Any] | None]


def _extract_message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text_val = part.get("text")
                if isinstance(text_val, str):
                    parts.append(text_val)
        return " ".join(parts)
    return str(content) if content else ""


def _format_knowledge_context(results: list[dict[str, Any]]) -> str:
    if not results:
        return ""

    lines = ["<knowledge_context>"]
    lines.append(f"Found {len(results)} relevant knowledge match{'es' if len(results) > 1 else ''}.")

    for i, result in enumerate(results, 1):
        doc_name = result.get("document_name", "unknown")
        chunk = result.get("chunk_content", "")
        score = result.get("similarity_score", 0.0)
        kb = result.get("kb_name", "")

        chunk_truncated = chunk[:_TRUNCATE_CHARS] + ("..." if len(chunk) > _TRUNCATE_CHARS else "")

        header = f"{i}. [KB: {kb}] [Doc: {doc_name}] [Score: {score:.2f}]"
        lines.append(header)
        lines.append(chunk_truncated)
        lines.append("")

    lines.append("</knowledge_context>")
    return "\n".join(lines)


class KnowledgeBaseMiddleware(AgentMiddleware[KnowledgeBaseMiddlewareState]):
    state_schema = KnowledgeBaseMiddlewareState

    @override
    def before_agent(self, state: KnowledgeBaseMiddlewareState, runtime: Runtime) -> dict | None:
        config = get_knowledge_search_config()
        if not config.enabled:
            return None

        messages = list(state.get("messages", []))
        if not messages:
            return None

        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            return None

        raw_content = _extract_message_text(last_message)

        clean_content = _UPLOAD_BLOCK_RE.sub("", raw_content)
        clean_content = _KB_CONTEXT_RE.sub("", clean_content).strip()

        if not clean_content:
            return None

        user_id: str | None = None
        workspace_id: str | None = None

        runtime_config = getattr(runtime, "config", None)
        if runtime_config is not None:
            metadata = getattr(runtime_config, "metadata", None) or {}
            user_id = metadata.get("owner_user_id")
            workspace_id = metadata.get("workspace_id")

        if not user_id:
            user_id = _get_current_user_id_from_context()
        if not user_id:
            logger.debug("No user_id available (runtime metadata + auth context); skipping KB search")
            return None

        try:
            search_result = search_accessible_knowledge_bases(
                user_id=user_id,
                workspace_id=workspace_id,
                query=clean_content,
                top_k=config.top_k,
                similarity_threshold=config.similarity_threshold,
                max_kbs=config.max_kbs,
                max_results_per_kb=config.max_results_per_kb,
            )
        except Exception as e:
            logger.warning(f"KB search failed: {e}")
            return None

        last_idx = len(messages) - 1

        if not search_result.results:
            return {
                "knowledge_context": None,
                "knowledge_results": [],
                "knowledge_search_meta": {
                    "kb_count": search_result.kb_count,
                    "searched_kb_count": search_result.searched_kb_count,
                    "result_count": 0,
                    "duration_ms": search_result.duration_ms,
                },
            }

        kb_context = _format_knowledge_context(search_result.results)

        total_chars = len(kb_context)
        if total_chars > config.max_context_chars:
            kb_context = kb_context[: config.max_context_chars] + "\n...(truncated)"
            logger.debug(f"KB context truncated from {total_chars} to {config.max_context_chars} chars")

        original_content = last_message.content
        if isinstance(original_content, str):
            new_content = kb_context + "\n\n" + original_content
        elif isinstance(original_content, list):
            new_content = [{"type": "text", "text": kb_context + "\n\n"}] + original_content
        else:
            new_content = kb_context + "\n\n" + str(original_content)

        updated_message = HumanMessage(
            content=new_content,
            id=last_message.id,
            additional_kwargs=last_message.additional_kwargs,
        )

        updated_messages = list(messages)
        updated_messages[last_idx] = updated_message

        return {
            "messages": updated_messages,
            "knowledge_context": kb_context,
            "knowledge_results": search_result.results,
            "knowledge_search_meta": {
                "kb_count": search_result.kb_count,
                "searched_kb_count": search_result.searched_kb_count,
                "result_count": len(search_result.results),
                "duration_ms": search_result.duration_ms,
            },
        }
