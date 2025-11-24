import os
from typing import Optional, Any
from .config import load_ignore_config


def get_supabase_client() -> Optional[Any]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        cfg = load_ignore_config()
        url = url or cfg.get("SUPABASE_URL") or cfg.get("SUPABASE_URL")
        key = key or cfg.get("SUPABASE_KEY") or cfg.get("SUPABASE_KEY")
    try:
        print("SB_URL_PRESENT", bool(url), "SB_KEY_PRESENT", bool(key))
    except Exception:
        pass
    if not url or not key:
        try:
            print("SB_CFG_MISSING")
        except Exception:
            pass
        return None
    try:
        from supabase import create_client
    except Exception:
        try:
            print("SB_IMPORT_FAIL")
        except Exception:
            pass
        return None
    try:
        client = create_client(url, key)
        try:
            print("SB_CLIENT_OK", bool(client))
        except Exception:
            pass
        return client
    except Exception as e:
        try:
            print("SB_CLIENT_ERROR", str(e))
        except Exception:
            pass
        return None
