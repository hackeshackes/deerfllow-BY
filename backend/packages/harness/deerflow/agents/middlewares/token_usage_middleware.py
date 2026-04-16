"""Middleware for recording LLM token usage to persistent storage."""

import logging
from typing import Any, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from deerflow.admin.token_usage import get_token_usage_store

logger = logging.getLogger(__name__)


class TokenUsageMiddleware(AgentMiddleware):
    """Records token usage from model response usage_metadata to file storage."""

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._record_usage(state, runtime)

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._record_usage(state, runtime)

    def _record_usage(self, state: AgentState, runtime: Runtime) -> None:
        messages = state.get("messages", [])
        if not messages:
            logger.debug("TokenUsageMiddleware: no messages in state")
            return None
        last = messages[-1]
        usage = getattr(last, "usage_metadata", None)
        if not usage:
            logger.debug("TokenUsageMiddleware: no usage_metadata on last message, type=%s", type(last).__name__)
            return None

        thread_id = None
        try:
            ctx = getattr(runtime, "context", None)
            if ctx and isinstance(ctx, dict):
                thread_id = ctx.get("thread_id")
        except Exception:
            pass

        metadata: dict[str, Any] = {}
        config = state.get("config")
        if isinstance(config, dict):
            metadata = config.get("metadata", {})

        user_id = metadata.get("user_id") or "unknown"
        model_name = metadata.get("model_name") or "unknown"
        run_id = metadata.get("run_id")

        logger.info(
            "TokenUsageMiddleware: recording usage user_id=%s model=%s input=%s output=%s total=%s",
            user_id,
            model_name,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            usage.get("total_tokens"),
        )

        try:
            store = get_token_usage_store()
            store.record(
                user_id=user_id,
                thread_id=thread_id,
                model_name=model_name,
                input_tokens=usage.get("input_tokens", 0) or 0,
                output_tokens=usage.get("output_tokens", 0) or 0,
                total_tokens=usage.get("total_tokens", 0) or 0,
                run_id=run_id,
            )
        except Exception as e:
            logger.warning("Failed to record token usage: %s", e)

        return None
