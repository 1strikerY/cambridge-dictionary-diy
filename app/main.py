from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

from .cambridge import CambridgeClient
from .repo import get_entry_from_db, upsert_entry_with_senses
from .auth import router as auth_router
from .utils_jwt import decode_token
from .repo_auth import insert_page_visit, insert_user_action


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = CambridgeClient()

here = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(here, "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(auth_router)

def render_template(path: str) -> HTMLResponse:
    candidates = [
        os.path.join(here, 'templates', path),
        os.path.join(os.getcwd(), 'app', 'templates', path),
        os.path.join(os.path.dirname(here), 'templates', path),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return HTMLResponse(content=f.read())
            except Exception:
                continue
    return HTMLResponse(content='not found', status_code=404)

@app.get('/login')
def login_page(request: Request):
    try:
        auth = request.headers.get("Authorization") or ""
        parts = auth.split()
        email = None
        user_id = None
        provider = None
        if len(parts) == 2 and parts[0].lower() == "bearer":
            data = decode_token(parts[1])
            if data:
                email = data.get("email")
                user_id = data.get("sub")
                provider = data.get("provider")
        if not user_id:
            tok = request.cookies.get("jwt_token") or ""
            if tok:
                data = decode_token(tok)
                if data:
                    email = data.get("email")
                    user_id = data.get("sub")
                    provider = data.get("provider")
        insert_page_visit(path="/login", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="login", action_content="")
    except Exception:
        pass
    return render_template('auth_login.html')

@app.get('/signup')
def signup_page(request: Request):
    try:
        auth = request.headers.get("Authorization") or ""
        parts = auth.split()
        email = None
        user_id = None
        provider = None
        if len(parts) == 2 and parts[0].lower() == "bearer":
            data = decode_token(parts[1])
            if data:
                email = data.get("email")
                user_id = data.get("sub")
                provider = data.get("provider")
        if not user_id:
            tok = request.cookies.get("jwt_token") or ""
            if tok:
                data = decode_token(tok)
                if data:
                    email = data.get("email")
                    user_id = data.get("sub")
                    provider = data.get("provider")
        insert_page_visit(path="/signup", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="register", action_content="")
    except Exception:
        pass
    return render_template('auth_signup.html')


@app.get("/@vite/client")
def vite_client_stub():
    return HTMLResponse(content="", status_code=200)

@app.get("/%40vite/client")
def vite_client_stub_encoded():
    return HTMLResponse(content="", status_code=200)


@app.get('/favorites')
def favorites_page(request: Request):
    try:
        auth = request.headers.get("Authorization") or ""
        parts = auth.split()
        email = None
        user_id = None
        provider = None
        if len(parts) == 2 and parts[0].lower() == "bearer":
            data = decode_token(parts[1])
            if data:
                email = data.get("email")
                user_id = data.get("sub")
                provider = data.get("provider")
        if not user_id:
            tok = request.cookies.get("jwt_token") or ""
            if tok:
                data = decode_token(tok)
                if data:
                    email = data.get("email")
                    user_id = data.get("sub")
                    provider = data.get("provider")
        insert_page_visit(path="/favorites", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="other", action_content="")
    except Exception:
        pass
    return render_template('favorites.html')

@app.get("/", response_class=HTMLResponse)
def root(request: Request) -> Response:
    here = os.path.dirname(os.path.abspath(__file__))
    tpl = os.path.join(here, "templates", "index.html")
    try:
        with open(tpl, "r", encoding="utf-8") as f:
            html = f.read()
        try:
            auth = request.headers.get("Authorization") or ""
            parts = auth.split()
            email = None
            user_id = None
            provider = None
            if len(parts) == 2 and parts[0].lower() == "bearer":
                data = decode_token(parts[1])
                if data:
                    email = data.get("email")
                    user_id = data.get("sub")
                    provider = data.get("provider")
            if not user_id:
                tok = request.cookies.get("jwt_token") or ""
                if tok:
                    data = decode_token(tok)
                    if data:
                        email = data.get("email")
                        user_id = data.get("sub")
                        provider = data.get("provider")
            insert_page_visit(path="/", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type="other", action_content="")
        except Exception:
            pass
        return HTMLResponse(content=html)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>cambridge dictionary api (python)</h1>")


@app.get("/api/dictionary/{language}/{entry}")
def dictionary(request: Request, language: str, entry: str):
    try:
        try:
            print("REQ_LANGUAGE", language)
        except Exception:
            pass
        norm_entry = entry.strip().lower()
        cached = get_entry_from_db(language, norm_entry)
        if cached is not None:
            try:
                defs = cached.get("definition") if isinstance(cached, dict) else None
                if defs and len(defs) > 0:
                    if language != "cn-en":
                        try:
                            auth = request.headers.get("Authorization") or ""
                            parts = auth.split()
                            email = None
                            user_id = None
                            provider = None
                            if len(parts) == 2 and parts[0].lower() == "bearer":
                                data_jwt = decode_token(parts[1])
                                if data_jwt:
                                    email = data_jwt.get("email")
                                    user_id = data_jwt.get("sub")
                                    provider = data_jwt.get("provider")
                            if not user_id:
                                tok = request.cookies.get("jwt_token") or ""
                                if tok:
                                    data_jwt = decode_token(tok)
                                    if data_jwt:
                                        email = data_jwt.get("email")
                                        user_id = data_jwt.get("sub")
                                        provider = data_jwt.get("provider")
                            insert_page_visit(path=f"/api/dictionary/{language}/{norm_entry}", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type=f"translate({language})", action_content=norm_entry)
                        except Exception:
                            pass
                        return JSONResponse(status_code=200, content=cached)
                    # for cn-en, ensure definitions carry lemma; otherwise refetch
                    has_lemma = any(isinstance(d, dict) and d.get("lemma") for d in defs)
                    if has_lemma:
                        try:
                            auth = request.headers.get("Authorization") or ""
                            parts = auth.split()
                            email = None
                            user_id = None
                            provider = None
                            if len(parts) == 2 and parts[0].lower() == "bearer":
                                data_jwt = decode_token(parts[1])
                                if data_jwt:
                                    email = data_jwt.get("email")
                                    user_id = data_jwt.get("sub")
                                    provider = data_jwt.get("provider")
                            if not user_id:
                                tok = request.cookies.get("jwt_token") or ""
                                if tok:
                                    data_jwt = decode_token(tok)
                                    if data_jwt:
                                        email = data_jwt.get("email")
                                        user_id = data_jwt.get("sub")
                                        provider = data_jwt.get("provider")
                            insert_page_visit(path=f"/api/dictionary/{language}/{norm_entry}", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type=f"translate({language})", action_content=norm_entry)
                        except Exception:
                            pass
                        return JSONResponse(status_code=200, content=cached)
            except Exception:
                if language != "cn-en":
                    try:
                        auth = request.headers.get("Authorization") or ""
                        parts = auth.split()
                        email = None
                        user_id = None
                        provider = None
                        if len(parts) == 2 and parts[0].lower() == "bearer":
                            data_jwt = decode_token(parts[1])
                            if data_jwt:
                                email = data_jwt.get("email")
                                user_id = data_jwt.get("sub")
                                provider = data_jwt.get("provider")
                        if not user_id:
                            tok = request.cookies.get("jwt_token") or ""
                            if tok:
                                data_jwt = decode_token(tok)
                                if data_jwt:
                                    email = data_jwt.get("email")
                                    user_id = data_jwt.get("sub")
                                    provider = data_jwt.get("provider")
                        insert_page_visit(path=f"/api/dictionary/{language}/{norm_entry}", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type=f"translate({language})", action_content=norm_entry)
                    except Exception:
                        pass
                    return JSONResponse(status_code=200, content=cached)

        data = client.get_entry(language, norm_entry)
        if data is None:
            try:
                auth = request.headers.get("Authorization") or ""
                parts = auth.split()
                email = None
                user_id = None
                provider = None
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    data_jwt = decode_token(parts[1])
                    if data_jwt:
                        email = data_jwt.get("email")
                        user_id = data_jwt.get("sub")
                        provider = data_jwt.get("provider")
                if not user_id:
                    tok = request.cookies.get("jwt_token") or ""
                    if tok:
                        data_jwt = decode_token(tok)
                        if data_jwt:
                            email = data_jwt.get("email")
                            user_id = data_jwt.get("sub")
                            provider = data_jwt.get("provider")
                insert_page_visit(path=f"/api/dictionary/{language}/{norm_entry}", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type=f"translate({language})", action_content=norm_entry)
            except Exception:
                pass
            return JSONResponse(status_code=404, content={"error": "word not found"})
        try:
            upsert_entry_with_senses(language, norm_entry, data)
        except Exception:
            pass
        try:
            auth = request.headers.get("Authorization") or ""
            parts = auth.split()
            email = None
            user_id = None
            provider = None
            if len(parts) == 2 and parts[0].lower() == "bearer":
                data_jwt = decode_token(parts[1])
                if data_jwt:
                    email = data_jwt.get("email")
                    user_id = data_jwt.get("sub")
                    provider = data_jwt.get("provider")
            if not user_id:
                tok = request.cookies.get("jwt_token") or ""
                if tok:
                    data_jwt = decode_token(tok)
                    if data_jwt:
                        email = data_jwt.get("email")
                        user_id = data_jwt.get("sub")
                        provider = data_jwt.get("provider")
            insert_page_visit(path=f"/api/dictionary/{language}/{norm_entry}", method="GET", email=email, user_id=user_id, provider=provider, ip=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent"), action_type=f"translate({language})", action_content=norm_entry)
        except Exception:
            pass
        return JSONResponse(status_code=200, content=data)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Unsupported language"})
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
