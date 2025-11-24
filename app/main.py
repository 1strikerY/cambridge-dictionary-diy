from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import os

from .cambridge import CambridgeClient
from .repo import get_entry_from_db, upsert_entry_with_senses


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = CambridgeClient()


@app.get("/", response_class=HTMLResponse)
def root() -> Response:
    here = os.path.dirname(os.path.abspath(__file__))
    tpl = os.path.join(here, "templates", "index.html")
    try:
        with open(tpl, "r", encoding="utf-8") as f:
            html = f.read()
        return HTMLResponse(content=html)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>cambridge dictionary api (python)</h1>")


@app.get("/api/dictionary/{language}/{entry}")
def dictionary(language: str, entry: str):
    try:
        norm_entry = entry.strip().lower()
        cached = get_entry_from_db(language, norm_entry)
        if cached is not None:
            return JSONResponse(status_code=200, content=cached)

        data = client.get_entry(language, norm_entry)
        if data is None:
            return JSONResponse(status_code=404, content={"error": "word not found"})
        try:
            upsert_entry_with_senses(language, norm_entry, data)
        except Exception:
            pass
        return JSONResponse(status_code=200, content=data)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Unsupported language"})
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
