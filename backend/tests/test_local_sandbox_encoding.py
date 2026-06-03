import asyncio
import builtins
from types import SimpleNamespace
from unittest.mock import AsyncMock

import deerflow.sandbox.local.local_sandbox as local_sandbox
from deerflow.sandbox.local.local_sandbox import LocalSandbox


def _open(base, file, mode="r", *args, **kwargs):
    if "b" in mode:
        return base(file, mode, *args, **kwargs)
    return base(file, mode, *args, encoding=kwargs.pop("encoding", "gbk"), **kwargs)


def test_read_file_uses_utf8_on_windows_locale(tmp_path, monkeypatch):
    path = tmp_path / "utf8.txt"
    text = "\u201cutf8\u201d"
    path.write_text(text, encoding="utf-8")
    base = builtins.open

    monkeypatch.setattr(local_sandbox, "open", lambda file, mode="r", *args, **kwargs: _open(base, file, mode, *args, **kwargs), raising=False)

    assert LocalSandbox("t").read_file(str(path)) == text


def test_write_file_uses_utf8_on_windows_locale(tmp_path, monkeypatch):
    path = tmp_path / "utf8.txt"
    text = "emoji \U0001f600"
    base = builtins.open

    monkeypatch.setattr(local_sandbox, "open", lambda file, mode="r", *args, **kwargs: _open(base, file, mode, *args, **kwargs), raising=False)

    LocalSandbox("t").write_file(str(path), text)

    assert path.read_text(encoding="utf-8") == text


def test_get_shell_prefers_posix_shell_from_path_before_windows_fallback(monkeypatch):
    monkeypatch.setattr(local_sandbox.os, "name", "nt")
    monkeypatch.setattr(LocalSandbox, "_find_first_available_shell", lambda candidates: r"C:\Program Files\Git\bin\sh.exe" if candidates == ("/bin/zsh", "/bin/bash", "/bin/sh", "sh") else None)

    assert LocalSandbox._get_shell() == r"C:\Program Files\Git\bin\sh.exe"


def test_get_shell_uses_powershell_fallback_on_windows(monkeypatch):
    calls: list[tuple[str, ...]] = []

    def fake_find(candidates: tuple[str, ...]) -> str | None:
        calls.append(candidates)
        if candidates == ("/bin/zsh", "/bin/bash", "/bin/sh", "sh"):
            return None
        return r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

    monkeypatch.setattr(local_sandbox.os, "name", "nt")
    monkeypatch.setattr(local_sandbox.os, "environ", {"SystemRoot": r"C:\Windows"})
    monkeypatch.setattr(LocalSandbox, "_find_first_available_shell", fake_find)

    assert LocalSandbox._get_shell() == r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    assert calls[1] == (
        "pwsh",
        "pwsh.exe",
        "powershell",
        "powershell.exe",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "cmd.exe",
    )


def test_get_shell_uses_cmd_as_last_windows_fallback(monkeypatch):
    def fake_find(candidates: tuple[str, ...]) -> str | None:
        if candidates == ("/bin/zsh", "/bin/bash", "/bin/sh", "sh"):
            return None
        return r"C:\Windows\System32\cmd.exe"

    monkeypatch.setattr(local_sandbox.os, "name", "nt")
    monkeypatch.setattr(local_sandbox.os, "environ", {"SystemRoot": r"C:\Windows"})
    monkeypatch.setattr(LocalSandbox, "_find_first_available_shell", fake_find)

    assert LocalSandbox._get_shell() == r"C:\Windows\System32\cmd.exe"


def _patch_async_subprocess_exec(monkeypatch, captured: list[tuple[tuple, dict]], stdout: bytes = b"ok", stderr: bytes = b"", returncode: int = 0) -> None:
    """Patch asyncio.create_subprocess_exec to capture the call args and return a fake proc."""

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured.append((args, kwargs))
        proc = SimpleNamespace()
        proc.communicate = AsyncMock(return_value=(stdout, stderr))
        proc.returncode = returncode
        proc.kill = lambda: None
        proc.wait = AsyncMock(return_value=None)
        return proc

    monkeypatch.setattr(local_sandbox.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)


def test_execute_command_uses_powershell_command_mode_on_windows(monkeypatch):
    captured: list[tuple[tuple, dict]] = []

    monkeypatch.setattr(local_sandbox.os, "name", "nt")
    monkeypatch.setattr(LocalSandbox, "_get_shell", staticmethod(lambda: r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"))
    _patch_async_subprocess_exec(monkeypatch, captured)

    output = asyncio.run(LocalSandbox("t").execute_command("Write-Output hello"))

    assert output == "ok"
    assert captured == [
        (
            (
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                "-NoProfile",
                "-Command",
                "Write-Output hello",
            ),
            {
                "stdout": local_sandbox.asyncio.subprocess.PIPE,
                "stderr": local_sandbox.asyncio.subprocess.PIPE,
            },
        )
    ]


def test_execute_command_uses_posix_shell_command_mode_on_windows(monkeypatch):
    captured: list[tuple[tuple, dict]] = []

    monkeypatch.setattr(local_sandbox.os, "name", "nt")
    monkeypatch.setattr(LocalSandbox, "_get_shell", staticmethod(lambda: r"C:\Program Files\Git\bin\sh.exe"))
    _patch_async_subprocess_exec(monkeypatch, captured)

    output = asyncio.run(LocalSandbox("t").execute_command("echo hello"))

    assert output == "ok"
    assert captured == [
        (
            (r"C:\Program Files\Git\bin\sh.exe", "-c", "echo hello"),
            {
                "stdout": local_sandbox.asyncio.subprocess.PIPE,
                "stderr": local_sandbox.asyncio.subprocess.PIPE,
            },
        )
    ]


def test_execute_command_uses_cmd_command_mode_on_windows(monkeypatch):
    captured: list[tuple[tuple, dict]] = []

    monkeypatch.setattr(local_sandbox.os, "name", "nt")
    monkeypatch.setattr(LocalSandbox, "_get_shell", staticmethod(lambda: r"C:\Windows\System32\cmd.exe"))
    _patch_async_subprocess_exec(monkeypatch, captured)

    output = asyncio.run(LocalSandbox("t").execute_command("echo hello"))

    assert output == "ok"
    assert captured == [
        (
            (r"C:\Windows\System32\cmd.exe", "/c", "echo hello"),
            {
                "stdout": local_sandbox.asyncio.subprocess.PIPE,
                "stderr": local_sandbox.asyncio.subprocess.PIPE,
            },
        )
    ]
