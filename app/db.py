from typing import Optional, Any
from .config import load_ignore_config


def get_supabase_client() -> Optional[Any]:
    cfg = load_ignore_config()
    url = cfg.get("SUPABASE_URL")
    key = cfg.get("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
    except Exception:
        return None
    try:
        client = create_client(url, key)
        return client
    except Exception:
        return None
