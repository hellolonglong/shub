# 文件名: tools/telnet_bridge/config.py
"""Load bridge_config.json with defaults and validation.

Fields:
- bind_addr: bridge listen address, default "0.0.0.0"
- target_host: shub address, default "127.0.0.1"
- offset: bridge_port = shub_port + offset when not specified
- AutoTrans: load mappings at startup when true
- mappings: string array, "shub" or "shub:bridge"
"""

import json
import os

DEFAULT_CONFIG = {
    "bind_addr": "0.0.0.0",
    "target_host": "127.0.0.1",
    "offset": 1000,
    "AutoTrans": False,
    "mappings": [],
}


def _validate(cfg):
    try:
        cfg["offset"] = int(cfg["offset"])
    except (TypeError, ValueError):
        cfg["offset"] = DEFAULT_CONFIG["offset"]
    if not (1 <= cfg["offset"] <= 65535):
        cfg["offset"] = DEFAULT_CONFIG["offset"]

    for key in ("bind_addr", "target_host"):
        if not isinstance(cfg.get(key), str) or not cfg[key]:
            cfg[key] = DEFAULT_CONFIG[key]

    if not isinstance(cfg.get("AutoTrans"), bool):
        cfg["AutoTrans"] = DEFAULT_CONFIG["AutoTrans"]

    if not isinstance(cfg.get("mappings"), list):
        cfg["mappings"] = []
    else:
        cfg["mappings"] = [m for m in cfg["mappings"] if isinstance(m, str)]

    return cfg


def load_config(path):
    """Return (cfg, error_or_None)."""
    if not path or not os.path.exists(path):
        return dict(DEFAULT_CONFIG), None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeError) as e:
        return dict(DEFAULT_CONFIG), f"cannot read {path}: {e}"

    if not isinstance(data, dict):
        return dict(DEFAULT_CONFIG), f"{path} must contain a JSON object"

    cfg = dict(DEFAULT_CONFIG)
    for k in cfg:
        if k in data:
            cfg[k] = data[k]
    return _validate(cfg), None