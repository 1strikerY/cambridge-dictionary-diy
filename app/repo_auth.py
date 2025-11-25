import requests
from typing import Optional, Dict, Any
from .utils_cfg import get_cfg

def _rest_base() -> Optional[str]:
    url = get_cfg("SUPABASE_URL", "xxxSUPABASE_URL")
    key = get_cfg("SUPABASE_KEY", "xxxSUPABASE_KEY")
    if not url or not key:
        try:
            print("SUPABASE_REST_BASE_MISSING", {"url": bool(url), "key": bool(key)})
        except Exception:
            pass
        return None
    return url.rstrip("/") + "/rest/v1"

def _headers() -> Dict[str, str]:
    key = get_cfg("SUPABASE_KEY", "xxxSUPABASE_KEY")
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

def upsert_user(email: str, password_hash: Optional[str], name: Optional[str], provider: str, avatar_url: Optional[str], email_verified: bool) -> bool:
    base = _rest_base()
    if not base:
        return False
    payload = {
        "email": email,
        "password_hash": password_hash or "",
        "provider": provider,
        "name": name or "",
        "avatar_url": avatar_url or "",
        "email_verified": email_verified,
    }
    r = requests.post(base + "/users", headers=_headers(), params={"on_conflict": "email"}, json=payload, timeout=10)
    return r.status_code in (200, 201, 204)

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    base = _rest_base()
    if not base:
        return None
    r = requests.get(base + "/users", headers=_headers(), params={"email": f"eq.{email}", "select": "id,email,password_hash,provider,name,avatar_url,email_verified"}, timeout=10)
    if r.status_code != 200:
        return None
    rows = r.json()
    if not rows:
        return None
    return rows[0]

def insert_code(email: str, code: str, expires_at: str) -> bool:
    base = _rest_base()
    if not base:
        return False
    payload = {"email": email, "code": code, "expires_at": expires_at, "used": False}
    r = requests.post(base + "/email_verification_codes", headers=_headers(), json=payload, timeout=10)
    return r.status_code in (200, 201)

def verify_code(email: str, code: str) -> bool:
    base = _rest_base()
    if not base:
        return False
    params = {"email": f"eq.{email}", "code": f"eq.{code}", "used": "eq.false"}
    r = requests.get(base + "/email_verification_codes", headers=_headers(), params=params, timeout=10)
    if r.status_code != 200:
        return False
    rows = r.json()
    if not rows:
        return False
    item = rows[-1]
    rid = item.get("id")
    if not rid:
        return False
    ru = requests.patch(base + "/email_verification_codes", headers=_headers(), params={"id": f"eq.{rid}"}, json={"used": True}, timeout=10)
    return ru.status_code in (200, 204)

def insert_auth_event(email: str, event_type: str, success: bool, provider: str | None = None, detail: str | None = None, ip: str | None = None, user_agent: str | None = None) -> bool:
    base = _rest_base()
    if not base:
        return False
    payload = {
        "email": email,
        "event_type": event_type,
        "success": success,
        "provider": provider or "",
        "detail": detail or "",
        "ip": ip or "",
        "user_agent": user_agent or "",
    }
    try:
        print("AUTH_EVENT_REQ", {"payload": payload})
        r = requests.post(base + "/auth_events", headers=_headers(), json=payload, timeout=10)
        ok = r.status_code in (200, 201)
        if not ok:
            try:
                print("AUTH_EVENT_RESP", {"status": r.status_code, "text": r.text})
            except Exception:
                pass
        return ok
    except Exception as e:
        try:
            print("AUTH_EVENT_ERR", {"error": str(e)})
        except Exception:
            pass
        return False

def insert_page_visit(path: str, method: str, email: str | None = None, user_id: str | None = None, provider: str | None = None, ip: str | None = None, user_agent: str | None = None, action_type: str | None = None, action_content: str | None = None) -> bool:
    base = _rest_base()
    if not base:
        return False
    payload = {
        "path": path,
        "method": method,
        "email": email or "",
        "provider": provider or "",
        "ip": ip or "",
        "user_agent": user_agent or "",
    }
    if user_id is not None:
        payload["user_id"] = user_id
    if action_type is not None:
        payload["action_type"] = action_type
    if action_content is not None:
        payload["action_content"] = action_content
    try:
        print("PAGE_VISIT_REQ", {"payload": payload})
        r = requests.post(base + "/page_visits", headers=_headers(), json=payload, timeout=10)
        ok = r.status_code in (200, 201)
        if not ok:
            try:
                print("PAGE_VISIT_RESP", {"status": r.status_code, "text": r.text})
            except Exception:
                pass
        return ok
    except Exception as e:
        try:
            print("PAGE_VISIT_ERR", {"error": str(e)})
        except Exception:
            pass
        return False

def insert_user_action(email: str | None = None, user_id: str | None = None, provider: str | None = None, action_type: str = "", action: str = "", target: str | None = None, sub_type: str | None = None, success: bool | None = None, detail: str | None = None, ip: str | None = None, user_agent: str | None = None, meta: Dict[str, Any] | None = None) -> bool:
    base = _rest_base()
    if not base:
        return False

# Favorites storage via Supabase REST
def add_favorite(user_id: str, email: str, provider: str, language: str, word: str) -> bool:
    base = _rest_base()
    if not base:
        return False
    payload = {"user_id": user_id, "email": email, "provider": provider, "language": language, "word": word}
    try:
        r = requests.post(base + "/favorites", headers=_headers(), params={"on_conflict": "user_id,language,word"}, json=payload, timeout=10)
        return r.status_code in (200, 201, 204)
    except Exception:
        return False

def remove_favorite(user_id: str, language: str, word: str) -> bool:
    base = _rest_base()
    if not base:
        return False
    try:
        r = requests.delete(base + "/favorites", headers=_headers(), params={"user_id": f"eq.{user_id}", "language": f"eq.{language}", "word": f"eq.{word}"}, timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False

def check_favorite(user_id: str, language: str, word: str) -> bool:
    base = _rest_base()
    if not base:
        return False
    try:
        r = requests.get(base + "/favorites", headers=_headers(), params={"user_id": f"eq.{user_id}", "language": f"eq.{language}", "word": f"eq.{word}", "select": "id"}, timeout=10)
        if r.status_code != 200:
            return False
        rows = r.json() or []
        return len(rows) > 0
    except Exception:
        return False

def list_favorites(user_id: str) -> list[Dict[str, Any]]:
    base = _rest_base()
    if not base:
        return []
    try:
        r = requests.get(base + "/favorites", headers=_headers(), params={"user_id": f"eq.{user_id}", "order": "created_at.asc"}, timeout=10)
        if r.status_code != 200:
            return []
        return r.json() or []
    except Exception:
        return []
    payload: Dict[str, Any] = {
        "email": (email or ""),
        "provider": (provider or ""),
        "action_type": action_type,
        "action": action,
        "target": (target or ""),
        "sub_type": (sub_type or ""),
        "detail": (detail or ""),
        "ip": (ip or ""),
        "user_agent": (user_agent or ""),
    }
    if user_id is not None:
        payload["user_id"] = user_id
    if success is not None:
        payload["success"] = success
    if meta is not None:
        payload["meta"] = meta
    try:
        print("USER_ACTION_REQ", {"payload": payload})
        r = requests.post(base + "/user_actions", headers=_headers(), json=payload, timeout=10)
        ok = r.status_code in (200, 201)
        if not ok:
            try:
                print("USER_ACTION_RESP", {"status": r.status_code, "text": r.text})
            except Exception:
                pass
        return ok
    except Exception as e:
        try:
            print("USER_ACTION_ERR", {"error": str(e)})
        except Exception:
            pass
        return False
