"""Patched ChatOpenAI adapter for MiniMax reasoning output.

MiniMax's OpenAI-compatible chat completions API can return structured
``reasoning_details`` when ``extra_body.reasoning_split=true`` is enabled.
``langchain_openai.ChatOpenAI`` currently ignores that field, so DeerFlow's
frontend never receives reasoning content in the shape it expects.

This adapter preserves ``reasoning_split`` in the request payload and maps the
provider-specific reasoning field into ``additional_kwargs.reasoning_content``,
which DeerFlow already understands.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import (
    _convert_delta_to_message_chunk,
    _create_usage_metadata,
)

_THINK_TAG_RE = re.compile(r"<think>\s*(.*?)\s*</think>", re.DOTALL)
_INVOKE_TAG_RE = re.compile(r"<invoke\s+name=\"(?P<name>[^\"]+)\"\s*>(?P<body>[\s\S]*?)</invoke>", re.IGNORECASE)
_PARAMETER_TAG_RE = re.compile(r"<parameter\s+name=\"(?P<name>[^\"]+)\"\s*>(?P<value>[\s\S]*?)</parameter>", re.IGNORECASE)


def _extract_reasoning_text(
    reasoning_details: Any,
    *,
    strip_parts: bool = True,
) -> str | None:
    if not isinstance(reasoning_details, list):
        return None

    parts: list[str] = []
    for item in reasoning_details:
        if not isinstance(item, Mapping):
            continue
        text = item.get("text")
        if isinstance(text, str):
            normalized = text.strip() if strip_parts else text
            if normalized.strip():
                parts.append(normalized)

    return "\n\n".join(parts) if parts else None


def _strip_inline_think_tags(content: str) -> tuple[str, str | None]:
    reasoning_parts: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        reasoning = match.group(1).strip()
        if reasoning:
            reasoning_parts.append(reasoning)
        return ""

    cleaned = _THINK_TAG_RE.sub(_replace, content).strip()
    reasoning = "\n\n".join(reasoning_parts) if reasoning_parts else None
    return cleaned, reasoning


def _merge_reasoning(*values: str | None) -> str | None:
    merged: list[str] = []
    for value in values:
        if not value:
            continue
        normalized = value.strip()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return "\n\n".join(merged) if merged else None


def _normalize_tool_arg_name(tool_name: str, arg_name: str) -> str:
    normalized = arg_name.strip()
    if tool_name == "read_file" and normalized == "image_path":
        return "file_path"
    return normalized


def _extract_invoke_tool_calls(content: str | None) -> tuple[str | None, list[dict[str, Any]]]:
    if not isinstance(content, str) or "<invoke" not in content:
        return content, []

    tool_calls: list[dict[str, Any]] = []

    def _replace(match: re.Match[str]) -> str:
        body = match.group("body") or ""
        tool_name = (match.group("name") or "").strip()
        args: dict[str, Any] = {}
        for param_match in _PARAMETER_TAG_RE.finditer(body):
            param_name = _normalize_tool_arg_name(tool_name, param_match.group("name") or "")
            param_value = (param_match.group("value") or "").strip()
            if param_name:
                args[param_name] = param_value
        if tool_name:
            tool_calls.append(
                {
                    "name": tool_name,
                    "args": args,
                    "id": f"invoke_{len(tool_calls) + 1}",
                    "type": "tool_call",
                }
            )
        return ""

    cleaned = _INVOKE_TAG_RE.sub(_replace, content).strip()
    return cleaned, tool_calls


def _with_reasoning_content(
    message: AIMessage | AIMessageChunk,
    reasoning: str | None,
    *,
    preserve_whitespace: bool = False,
):
    if not reasoning:
        return message

    additional_kwargs = dict(message.additional_kwargs)
    if preserve_whitespace:
        existing = additional_kwargs.get("reasoning_content")
        additional_kwargs["reasoning_content"] = f"{existing}{reasoning}" if isinstance(existing, str) else reasoning
    else:
        additional_kwargs["reasoning_content"] = _merge_reasoning(
            additional_kwargs.get("reasoning_content"),
            reasoning,
        )
    return message.model_copy(update={"additional_kwargs": additional_kwargs})


class PatchedChatMiniMax(ChatOpenAI):
    """ChatOpenAI adapter that preserves MiniMax reasoning output."""

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        extra_body = payload.get("extra_body")
        if isinstance(extra_body, dict):
            payload["extra_body"] = {
                **extra_body,
                "reasoning_split": True,
            }
        else:
            payload["extra_body"] = {"reasoning_split": True}
        return payload

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        if chunk.get("type") == "content.delta":
            return None

        token_usage = chunk.get("usage")
        choices = chunk.get("choices", []) or chunk.get("chunk", {}).get("choices", [])
        usage_metadata = _create_usage_metadata(token_usage, chunk.get("service_tier")) if token_usage else None

        if len(choices) == 0:
            generation_chunk = ChatGenerationChunk(
                message=default_chunk_class(content="", usage_metadata=usage_metadata),
                generation_info=base_generation_info,
            )
            if self.output_version == "v1":
                generation_chunk.message.content = []
                generation_chunk.message.response_metadata["output_version"] = "v1"
            return generation_chunk

        choice = choices[0]
        delta = choice.get("delta")
        if delta is None:
            return None

        message_chunk = _convert_delta_to_message_chunk(delta, default_chunk_class)
        generation_info = {**base_generation_info} if base_generation_info else {}

        if finish_reason := choice.get("finish_reason"):
            generation_info["finish_reason"] = finish_reason
            if model_name := chunk.get("model"):
                generation_info["model_name"] = model_name
            if system_fingerprint := chunk.get("system_fingerprint"):
                generation_info["system_fingerprint"] = system_fingerprint
            if service_tier := chunk.get("service_tier"):
                generation_info["service_tier"] = service_tier

        logprobs = choice.get("logprobs")
        if logprobs:
            generation_info["logprobs"] = logprobs

        reasoning = _extract_reasoning_text(
            delta.get("reasoning_details"),
            strip_parts=False,
        )
        if isinstance(message_chunk, AIMessageChunk):
            if usage_metadata:
                message_chunk.usage_metadata = usage_metadata
            if reasoning:
                message_chunk = _with_reasoning_content(
                    message_chunk,
                    reasoning,
                    preserve_whitespace=True,
                )

        message_chunk.response_metadata["model_provider"] = "openai"
        return ChatGenerationChunk(
            message=message_chunk,
            generation_info=generation_info or None,
        )

    def _create_chat_result(
        self,
        response: dict | Any,
        generation_info: dict | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        response_dict = response if isinstance(response, dict) else response.model_dump()
        choices = response_dict.get("choices", [])

        generations: list[ChatGeneration] = []
        for index, generation in enumerate(result.generations):
            choice = choices[index] if index < len(choices) else {}
            message = generation.message
            if isinstance(message, AIMessage):
                content = message.content if isinstance(message.content, str) else None
                cleaned_content = content
                inline_reasoning = None
                xml_tool_calls: list[dict[str, Any]] = []
                if isinstance(content, str):
                    cleaned_content, inline_reasoning = _strip_inline_think_tags(content)
                    cleaned_content, xml_tool_calls = _extract_invoke_tool_calls(cleaned_content)

                choice_message = choice.get("message", {}) if isinstance(choice, Mapping) else {}
                split_reasoning = _extract_reasoning_text(choice_message.get("reasoning_details"))
                merged_reasoning = _merge_reasoning(split_reasoning, inline_reasoning)

                updated_message = message
                if cleaned_content is not None and cleaned_content != message.content:
                    updated_message = updated_message.model_copy(update={"content": cleaned_content})
                if xml_tool_calls and not updated_message.tool_calls:
                    updated_message = updated_message.model_copy(update={"tool_calls": xml_tool_calls})
                if merged_reasoning:
                    updated_message = _with_reasoning_content(updated_message, merged_reasoning)

                generation = ChatGeneration(
                    message=updated_message,
                    generation_info=generation.generation_info,
                )

            generations.append(generation)

        return ChatResult(generations=generations, llm_output=result.llm_output)
