from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import re
import time
import hashlib
import bcrypt
import secrets
import requests
from .utils_cfg import get_cfg
from .utils_jwt import create_token, decode_token
from .repo_auth import upsert_user, get_user_by_email, insert_code, verify_code, insert_auth_event, insert_page_visit, add_favorite, remove_favorite, check_favorite, list_favorites

router = APIRouter()

class SendCodeBody(BaseModel):
    email: str

class VerifyCodeBody(BaseModel):
    email: str
    code: str

class RegisterBody(BaseModel):
    email: str
    password: str
    name: str | None = None
    code: str

class LoginBody(BaseModel):
    email: str
    password: str

class FavoriteBody(BaseModel):
    language: str
    word: str

def _valid_email(e: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", e))

@router.post("/auth/send_code")
def send_code_api(body: SendCodeBody, request: Request):
    email = body.email.strip().lower()
    if not _valid_email(email):
        return JSONResponse(status_code=400, content={"error": "invalid email"})
    code = f"{secrets.randbelow(1000000):06d}"
    expires = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 600))
    ok = insert_code(email, code, expires)
    from .emailer import send_code as _send
    sent = _send(email, code)
    # 开发模式下返回验证码用于调试（生产不要开启）
    dev = get_cfg("DEV_RETURN_CODE") == "1"
    payload = {"ok": ok, "sent": sent}
    if dev and ok and not sent:
        payload["dev_code"] = code
    try:
        insert_page_visit(path="/auth/send_code", method="POST", email=email, provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="register", action_content=email)
    except Exception:
        pass
    return JSONResponse(status_code=200, content=payload)

@router.post("/auth/verify_code")
def verify_code_api(body: VerifyCodeBody, request: Request):
    email = body.email.strip().lower()
    code = body.code.strip()
    ok = verify_code(email, code)
    if not ok:
        return JSONResponse(status_code=400, content={"error": "invalid code"})
    try:
        insert_page_visit(path="/auth/verify_code", method="POST", email=email, provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="register", action_content=email)
    except Exception:
        pass
    return JSONResponse(status_code=200, content={"verified": True})

@router.post("/auth/register")
def register_api(body: RegisterBody, request: Request):
    email = body.email.strip().lower()
    if not _valid_email(email):
        insert_auth_event(email, "register", False, provider="email", detail="invalid email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        return JSONResponse(status_code=400, content={"error": "invalid email"})
    if not verify_code(email, body.code.strip()):
        insert_auth_event(email, "register", False, provider="email", detail="invalid code", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        return JSONResponse(status_code=400, content={"error": "invalid code"})
    salt = bcrypt.gensalt()
    ph = bcrypt.hashpw(body.password.encode("utf-8"), salt).decode("utf-8")
    ok = upsert_user(email, ph, body.name, "email", None, True)
    if not ok:
        insert_auth_event(email, "register", False, provider="email", detail="upsert failed", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        try:
            insert_page_visit(path="/auth/register", method="POST", email=email, provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="register", action_content=email)
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"error": "register failed"})
    sub_id = hashlib.sha256(email.encode()).hexdigest()
    token = create_token({"sub": sub_id, "email": email, "provider": "email"})
    insert_auth_event(email, "register", True, provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
    try:
        insert_page_visit(path="/auth/register", method="POST", email=email, user_id=sub_id, provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="register", action_content=email)
    except Exception:
        pass
    return JSONResponse(status_code=200, content={"token": token})

@router.post("/auth/login")
def login_api(body: LoginBody, request: Request):
    email = body.email.strip().lower()
    u = get_user_by_email(email)
    if not u:
        insert_auth_event(email, "login", False, provider="email", detail="user not found", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        try:
            insert_page_visit(path="/auth/login", method="POST", email=email, provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content=email)
        except Exception:
            pass
        return JSONResponse(status_code=404, content={"error": "user not found"})
    if u.get("provider") != "email":
        insert_auth_event(email, "login", False, provider=u.get("provider"), detail="wrong provider", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        try:
            insert_page_visit(path="/auth/login", method="POST", email=email, user_id=u.get("id"), provider=u.get("provider"), ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content=email)
        except Exception:
            pass
        return JSONResponse(status_code=400, content={"error": "use social login"})
    ph = u.get("password_hash") or ""
    try:
        ok = bcrypt.checkpw(body.password.encode("utf-8"), ph.encode("utf-8"))
    except Exception:
        ok = False
    if not ok:
        insert_auth_event(email, "login", False, provider="email", detail="wrong password", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        try:
            insert_page_visit(path="/auth/login", method="POST", email=email, user_id=u.get("id"), provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content=email)
        except Exception:
            pass
        return JSONResponse(status_code=400, content={"error": "wrong password"})
    token = create_token({"sub": u.get("id"), "email": email, "provider": "email"})
    insert_auth_event(email, "login", True, provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
    try:
        insert_page_visit(path="/auth/login", method="POST", email=email, user_id=u.get("id"), provider="email", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content=email)
    except Exception:
        pass
    return JSONResponse(status_code=200, content={"token": token})

@router.get("/auth/google/start")
def google_start():
    cid = get_cfg("GOOGLE_CLIENT_ID")
    redir = get_cfg("GOOGLE_REDIRECT_URI")
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(12)
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth?" 
        f"client_id={cid}&response_type=code&redirect_uri={redir}&scope=openid%20email%20profile&state={state}&nonce={nonce}"
    )
    return RedirectResponse(url)

@router.get("/auth/google/callback")
def google_callback(request: Request):
    code = request.query_params.get("code")
    cid = get_cfg("GOOGLE_CLIENT_ID")
    secret = get_cfg("GOOGLE_CLIENT_SECRET")
    redir = get_cfg("GOOGLE_REDIRECT_URI")
    data = {
        "code": code,
        "client_id": cid,
        "client_secret": secret,
        "redirect_uri": redir,
        "grant_type": "authorization_code",
    }
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=10)
    if r.status_code != 200:
        insert_auth_event("", "login", False, provider="google", detail="token exchange failed", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        try:
            insert_page_visit(path="/auth/google/callback", method="GET", provider="google", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content="")
        except Exception:
            pass
        return JSONResponse(status_code=400, content={"error": "oauth failed"})
    js = r.json()
    idt = js.get("id_token")
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as greq
        info = id_token.verify_oauth2_token(idt, greq.Request(), cid)
    except Exception:
        insert_auth_event("", "login", False, provider="google", detail="id_token invalid", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        try:
            insert_page_visit(path="/auth/google/callback", method="GET", provider="google", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content="")
        except Exception:
            pass
        return JSONResponse(status_code=400, content={"error": "id_token invalid"})
    email = (info.get("email") or "").lower()
    name = info.get("name") or ""
    avatar = info.get("picture") or ""
    ok = upsert_user(email, None, name, "google", avatar, True)
    if not ok:
        insert_auth_event(email, "login", False, provider="google", detail="upsert failed", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
        try:
            insert_page_visit(path="/auth/google/callback", method="GET", email=email, provider="google", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content=email)
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"error": "login failed"})
    token = create_token({"sub": info.get("sub"), "email": email, "provider": "google"})
    insert_auth_event(email, "login", True, provider="google", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"))
    try:
        insert_page_visit(path="/auth/google/callback", method="GET", email=email, user_id=info.get("sub"), provider="google", ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content=email)
    except Exception:
        pass
    return JSONResponse(status_code=200, content={"token": token})

@router.get("/me")
def me(request: Request):
    auth = request.headers.get("Authorization") or ""
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        data = decode_token(parts[1])
        if data:
            return JSONResponse(status_code=200, content={"user": {"email": data.get("email"), "provider": data.get("provider")}})
    return JSONResponse(status_code=401, content={"error": "unauthorized"})

def _auth_context(request: Request):
    auth = request.headers.get("Authorization") or ""
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        data = decode_token(parts[1])
        if data:
            return data
    tok = request.cookies.get("jwt_token") or ""
    if tok:
        data = decode_token(tok)
        if data:
            return data
    return None

@router.post("/favorite")
def add_fav(request: Request, body: FavoriteBody):
    data = _auth_context(request)
    if not data:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    user_id = data.get("sub")
    email = data.get("email") or ""
    provider = data.get("provider") or ""
    ok = add_favorite(user_id, email, provider, body.language.strip(), body.word.strip().lower())
    insert_page_visit(path="/favorite", method="POST", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="favorite", action_content=f"{body.language}:{body.word.strip().lower()}")
    if not ok:
        return JSONResponse(status_code=500, content={"error": "favorite failed"})
    return JSONResponse(status_code=200, content={"ok": True})

@router.delete("/favorite")
def del_fav(request: Request, body: FavoriteBody):
    data = _auth_context(request)
    if not data:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    user_id = data.get("sub")
    email = data.get("email") or ""
    provider = data.get("provider") or ""
    ok = remove_favorite(user_id, body.language.strip(), body.word.strip().lower())
    insert_page_visit(path="/favorite", method="DELETE", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="favorite", action_content=f"{body.language}:{body.word.strip().lower()}" )
    if not ok:
        return JSONResponse(status_code=500, content={"error": "unfavorite failed"})
    return JSONResponse(status_code=200, content={"ok": True})

@router.get("/favorite/status/{language}/{word}")
def fav_status(request: Request, language: str, word: str):
    data = _auth_context(request)
    if not data:
        return JSONResponse(status_code=200, content={"favorited": False})
    user_id = data.get("sub")
    ok = check_favorite(user_id, language.strip(), word.strip().lower())
    return JSONResponse(status_code=200, content={"favorited": ok})

@router.get("/favorites/list")
def fav_list(request: Request):
    data = _auth_context(request)
    if not data:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    user_id = data.get("sub")
    items = list_favorites(user_id)
    return JSONResponse(status_code=200, content={"items": items})
