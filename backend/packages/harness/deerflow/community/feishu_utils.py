import json
import logging
from typing import Any

from deerflow.config import get_app_config

logger = logging.getLogger(__name__)


def _get_feishu_config() -> dict[str, Any] | None:
    config = get_app_config()
    channels = config.model_extra.get("channels", {}) if config.model_extra else {}
    feishu_cfg = channels.get("feishu", {}) if isinstance(channels, dict) else None
    return feishu_cfg if isinstance(feishu_cfg, dict) else None


def _get_feishu_client():
    feishu_cfg = _get_feishu_config()
    if feishu_cfg is None:
        logger.warning("[Feishu tools] feishu channel not configured in config.yaml")
        return None

    app_id = feishu_cfg.get("app_id", "")
    app_secret = feishu_cfg.get("app_secret", "")
    domain = feishu_cfg.get("domain", "https://open.feishu.cn")

    if not app_id or not app_secret:
        logger.warning("[Feishu tools] app_id or app_secret not configured")
        return None

    try:
        import lark_oapi as lark

        client = lark.Client.builder().app_id(app_id).app_secret(app_secret).domain(domain).build()
        return client
    except ImportError:
        logger.warning("[Feishu tools] lark-oapi not installed. Install with: uv add lark-oapi")
        return None
    except Exception as e:
        logger.error("[Feishu tools] failed to create client: %s", e)
        return None


def _check_feishu_enabled() -> bool:
    feishu_cfg = _get_feishu_config()
    if feishu_cfg is None:
        return False
    return feishu_cfg.get("enabled", False)


def _handle_response(response, error_msg_prefix: str = "API call failed") -> dict[str, Any]:
    if response is None:
        return {"error": "Feishu client not available. Check channel configuration."}
    if not hasattr(response, "success"):
        return {"error": f"{error_msg_prefix}: invalid response type"}
    if not response.success():
        return {
            "error": f"{error_msg_prefix}: code={getattr(response, 'code', '?')}, msg={getattr(response, 'msg', '?')}",
            "log_id": response.get_log_id() if hasattr(response, "get_log_id") else None,
        }
    return {"data": getattr(response, "data", None)}


def _error_response(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _ok_response(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=lambda v: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v)