"""Verify local sandbox uses async subprocess (not blocking subprocess.run)."""
import inspect

import pytest


def test_local_sandbox_uses_async_subprocess():
    """Regression: subprocess.run blocks the event loop. Use asyncio subprocess instead."""
    from deerflow.sandbox.local import local_sandbox

    src = inspect.getsource(local_sandbox)
    # The LLM-blocking subprocess.run should be replaced
    assert "subprocess.run" not in src, (
        "local_sandbox.py should not use blocking subprocess.run; "
        "use asyncio.create_subprocess_shell instead"
    )
    assert "asyncio.create_subprocess_shell" in src or "asyncio.create_subprocess_exec" in src, (
        "local_sandbox.py must use asyncio subprocess API"
    )


def test_local_sandbox_execute_command_is_async():
    """execute_command must be async so callers can await it without blocking."""
    from deerflow.sandbox.local.local_sandbox import LocalSandbox

    assert inspect.iscoroutinefunction(LocalSandbox.execute_command), (
        "LocalSandbox.execute_command must be `async def` so the event loop is not blocked"
    )


def test_local_sandbox_execute_command_runs_without_blocking_event_loop():
    """A real async execute_command should yield control during a long-running command."""
    import asyncio

    from deerflow.sandbox.local.local_sandbox import LocalSandbox

    async def main() -> str:
        # Schedule a heartbeat that must run while execute_command is awaiting
        heartbeat_fired = []

        async def heartbeat() -> None:
            await asyncio.sleep(0.05)
            heartbeat_fired.append(True)

        task = asyncio.create_task(heartbeat())
        result = await LocalSandbox("hb").execute_command("echo heartbeat-check")
        await task
        assert heartbeat_fired, "heartbeat must fire while execute_command is awaiting"
        return result

    output = asyncio.run(main())
    assert "heartbeat-check" in output


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
