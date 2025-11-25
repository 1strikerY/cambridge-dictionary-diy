import os
from .config import load_ignore_config

def get_cfg(*keys: str) -> str:
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    cfg = load_ignore_config()
    for k in keys:
        v = cfg.get(k)
        if v:
            return v
    return ""

