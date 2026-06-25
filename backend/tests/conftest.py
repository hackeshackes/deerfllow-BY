"""Test configuration for the backend test suite.

Sets up sys.path and pre-mocks modules that would cause circular import
issues when unit-testing lightweight config/registry code in isolation.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Make 'app' and 'deerflow' importable from any working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# Live/e2e tests require running infrastructure (Redis, langgraph dev server)
# and hang indefinitely without it. Excluded from default test runs; run
# manually when infrastructure is available. Paths are relative to this
# conftest.py's directory (tests/).
collect_ignore = [
    "test_client_e2e.py",
    "test_client_live.py",
    "test_create_deerflow_agent_live.py",
]

# Break the circular import chain that exists in production code:
#   deerflow.subagents.__init__
#     -> .executor (SubagentExecutor, SubagentResult)
#       -> deerflow.agents.thread_state
#         -> deerflow.agents.__init__
#           -> lead_agent.agent
#             -> subagent_limit_middleware
#               -> deerflow.subagents.executor  <-- circular!
#
# By injecting a mock for deerflow.subagents.executor *before* any test module
# triggers the import, __init__.py's "from .executor import ..." succeeds
# immediately without running the real executor module.
_executor_mock = MagicMock()
_executor_mock.SubagentExecutor = MagicMock
_executor_mock.SubagentResult = MagicMock
_executor_mock.SubagentStatus = MagicMock
_executor_mock.MAX_CONCURRENT_SUBAGENTS = 3
_executor_mock.get_background_task_result = MagicMock()

sys.modules["deerflow.subagents.executor"] = _executor_mock

# Stub the missing voice_config module so app.gateway.app can be imported by
# tests that use TestClient(create_app()). Production code expects this
# module to live at backend/app/gateway/data/voice_config.py but the file is
# absent from this commit (pre-existing repo state). Until the missing module
# is added, this stub lets downstream tests collect and run.
_voice_config_mock = MagicMock()
_voice_config_mock.get_voice_config = MagicMock(return_value={})
_voice_config_mock.upsert_voice_config = MagicMock(return_value={})

_data_pkg = sys.modules.get("app.gateway.data")
if _data_pkg is None:
    import types

    _data_pkg = types.ModuleType("app.gateway.data")
    sys.modules["app.gateway.data"] = _data_pkg
_data_pkg.voice_config = _voice_config_mock  # type: ignore[attr-defined]
sys.modules["app.gateway.data.voice_config"] = _voice_config_mock


import pytest


@pytest.fixture(autouse=True)
def identity_env(monkeypatch):
    """Set required env vars for identity subsystem tests."""
    monkeypatch.setenv("MICX_SECRET_ENCRYPTION_KEY", "test-key-must-be-at-least-32-bytes-long!")
    # Force config singleton to re-evaluate
    from app.gateway.identity import config as cfg_mod
    cfg_mod.get_identity_config.cache_clear()
    yield
    cfg_mod.get_identity_config.cache_clear()
