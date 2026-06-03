"""Verify memory updater uses async model.ainvoke (not sync model.invoke)."""

import inspect


def test_memory_updater_calls_ainvoke_not_invoke():
    """Regression: ensure async event loop is not blocked by sync invoke."""
    from deerflow.agents.memory import updater

    # Inspect the source to confirm ainvoke (not invoke) is used in the LLM call site
    src = inspect.getsource(updater)
    # The LLM call line should use ainvoke
    assert "ainvoke" in src, "memory updater must use model.ainvoke for async safety"
    # It should NOT use the blocking invoke() at the LLM call site
    # (we allow invoke elsewhere, e.g. in helper utilities, but the LLM call itself must be async)
    llm_call_block = [line for line in src.split("\n") if "model.invoke(" in line]
    assert not llm_call_block, f"Found blocking model.invoke in memory updater: {llm_call_block}"
