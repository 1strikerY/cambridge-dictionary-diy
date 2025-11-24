from typing import Optional, Dict, Any, List
import logging
import requests

import os
from .db import get_supabase_client
from .config import load_ignore_config

logger = logging.getLogger("repo")


def _map_languages(language_slug: str) -> tuple[str, Optional[str]]:
    src = "en"
    if language_slug == "en-cn":
        return src, "zh-cn"
    if language_slug == "en-tw":
        return src, "zh-tw"
    return src, None


def get_entry_from_db(language_slug: str, entry: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    if client is None:
        cfg = load_ignore_config()
        base = os.environ.get("SUPABASE_URL") or cfg.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY") or cfg.get("SUPABASE_KEY") or cfg.get("SUPABASE_KEY")
        if not base or not key:
            return None
        try:
            headers = {
                "apikey": key,
                "Authorization": f"Bearer {key}",
            }
            rest = f"{base.rstrip('/')}/rest/v1"
            q1 = {
                "language_slug": f"eq.{language_slug}",
                "entry": f"eq.{entry}",
                "select": "id,word,pos,pronunciation,verbs",
                "limit": "1",
            }
            r1 = requests.get(f"{rest}/dictionary_entries", headers=headers, params=q1, timeout=10)
            if r1.status_code != 200:
                try:
                    print("HTTP_DB_HEAD_STATUS", r1.status_code, r1.text[:120])
                except Exception:
                    pass
                return None
            rows = r1.json()
            try:
                print("HTTP_DB_HEAD_ROWS", len(rows))
            except Exception:
                pass
            if not rows:
                return None
            entry_row = rows[0]
            entry_id = entry_row["id"]
            q2 = {
                "entry_id": f"eq.{entry_id}",
                "select": "pos,source,original_content,translated_result,level,examples",
            }
            r2 = requests.get(f"{rest}/dictionary_senses", headers=headers, params=q2, timeout=10)
            if r2.status_code != 200:
                try:
                    print("HTTP_DB_SENSES_STATUS", r2.status_code, r2.text[:120])
                except Exception:
                    pass
                senses = []
            else:
                senses = r2.json()
            try:
                print("HTTP_DB_SENSES_ROWS", len(senses))
            except Exception:
                pass
            definitions: List[Dict[str, Any]] = []
            for i, s in enumerate(senses):
                definitions.append(
                    {
                        "id": i,
                        "pos": s.get("pos") or "",
                        "source": s.get("source") or "",
                        "text": s.get("original_content") or "",
                        "translation": s.get("translated_result") or "",
                        "level": s.get("level") or "",
                        "example": s.get("examples") or [],
                    }
                )
            return {
                "word": entry_row.get("word") or "",
                "pos": entry_row.get("pos") or [],
                "pronunciation": entry_row.get("pronunciation") or [],
                "definition": definitions,
                "verbs": entry_row.get("verbs") or [],
            }
        except Exception as e:
            try:
                print("HTTP_DB_EXCEPTION", str(e))
            except Exception:
                pass
            return None
    try:
        head = (
            client.table("dictionary_entries")
            .select("id, word, pos, pronunciation, verbs")
            .eq("language_slug", language_slug)
            .eq("entry", entry)
            .limit(1)
            .execute()
        )
        rows = getattr(head, "data", [])
        try:
            logger.info("DB_HEAD_ROWS=%s", len(rows))
        except Exception:
            pass
        try:
            print("DB_HEAD_ROWS", len(rows))
        except Exception:
            pass
        if not rows:
            return None
        entry_row = rows[0]
        entry_id = entry_row["id"]
        senses_res = (
            client.table("dictionary_senses")
            .select("pos, source, original_content, translated_result, level, examples")
            .eq("entry_id", entry_id)
            .order("id")
            .execute()
        )
        senses = getattr(senses_res, "data", [])
        try:
            logger.info("DB_SENSES_ROWS=%s", len(senses))
        except Exception:
            pass
        try:
            print("DB_SENSES_ROWS", len(senses))
        except Exception:
            pass
        definitions: List[Dict[str, Any]] = []
        for i, s in enumerate(senses):
            definitions.append(
                {
                    "id": i,
                    "pos": s.get("pos") or "",
                    "source": s.get("source") or "",
                    "text": s.get("original_content") or "",
                    "translation": s.get("translated_result") or "",
                    "level": s.get("level") or "",
                    "example": s.get("examples") or [],
                }
            )
        return {
            "word": entry_row.get("word") or "",
            "pos": entry_row.get("pos") or [],
            "pronunciation": entry_row.get("pronunciation") or [],
            "definition": definitions,
            "verbs": entry_row.get("verbs") or [],
        }
    except Exception:
        return None


def upsert_entry_with_senses(language_slug: str, entry: str, data: Dict[str, Any]) -> None:
    client = get_supabase_client()
    if client is None:
        cfg = load_ignore_config()
        base = os.environ.get("SUPABASE_URL") or cfg.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY") or cfg.get("SUPABASE_KEY") or cfg.get("SUPABASE_KEY")
        if not base or not key:
            return
        try:
            src_lang, tgt_lang = _map_languages(language_slug)
            head_payload = {
                "language_slug": language_slug,
                "source_language": src_lang,
                "target_language": tgt_lang,
                "entry": entry,
                "word": data.get("word") or entry,
                "pos": data.get("pos") or [],
                "pronunciation": data.get("pronunciation") or [],
                "verbs": data.get("verbs") or [],
                "data": data,
            }
            headers = {
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            }
            rest = f"{base.rstrip('/')}/rest/v1"
            r = requests.post(
                f"{rest}/dictionary_entries",
                headers=headers,
                params={"on_conflict": "language_slug,entry", "select": "id"},
                json=head_payload,
                timeout=10,
            )
            if r.status_code not in (200, 201):
                try:
                    print("HTTP_UPSERT_HEAD_STATUS", r.status_code, r.text[:160])
                except Exception:
                    pass
                # Fallback unconditionally: remove raw data and retry upsert once
                try:
                    hp = dict(head_payload)
                    hp.pop("data", None)
                    # Use return=minimal to avoid representation errors when schema cache complains
                    headers_min = dict(headers)
                    headers_min["Prefer"] = "resolution=merge-duplicates,return=minimal"
                    r_fallback = requests.post(
                        f"{rest}/dictionary_entries",
                        headers=headers_min,
                        params={"on_conflict": "language_slug,entry"},
                        json=hp,
                        timeout=10,
                    )
                    if r_fallback.status_code not in (200, 201, 204):
                        try:
                            print(
                                "HTTP_UPSERT_HEAD_FALLBACK_STATUS",
                                r_fallback.status_code,
                                r_fallback.text[:160],
                            )
                        except Exception:
                            pass
                        return
                    # Fetch id via GET
                    q_get = {
                        "language_slug": f"eq.{language_slug}",
                        "entry": f"eq.{entry}",
                        "select": "id",
                        "limit": "1",
                    }
                    r_get = requests.get(f"{rest}/dictionary_entries", headers=headers, params=q_get, timeout=10)
                    if r_get.status_code != 200:
                        try:
                            print("HTTP_UPSERT_HEAD_GET_STATUS", r_get.status_code, r_get.text[:160])
                        except Exception:
                            pass
                        return
                    head_rows = r_get.json()
                    try:
                        print("HTTP_UPSERT_HEAD_ROWS", len(head_rows))
                    except Exception:
                        pass
                    if not head_rows:
                        return
                    entry_id = head_rows[0]["id"]
                    senses_payload: List[Dict[str, Any]] = []
                    for d in data.get("definition", []) or []:
                        senses_payload.append(
                            {
                                "entry_id": entry_id,
                                "pos": d.get("pos") or "",
                                "source": d.get("source") or "",
                                "original_content": d.get("text") or "",
                                "translated_result": d.get("translation") or "",
                                "level": d.get("level") or "",
                                "examples": d.get("example") or [],
                            }
                        )
                    if senses_payload:
                        r2 = requests.post(
                            f"{rest}/dictionary_senses",
                            headers=headers,
                            params={"on_conflict": "entry_id,pos,original_content"},
                            json=senses_payload,
                            timeout=10,
                        )
                        try:
                            print("HTTP_UPSERT_SENSES_STATUS", r2.status_code)
                        except Exception:
                            pass
                    return
                except Exception:
                    pass
                return
            head_rows = r.json()
            try:
                print("HTTP_UPSERT_HEAD_ROWS", len(head_rows))
            except Exception:
                pass
            if not head_rows:
                return
            entry_id = head_rows[0]["id"]
            senses_payload: List[Dict[str, Any]] = []
            for d in data.get("definition", []) or []:
                senses_payload.append(
                    {
                        "entry_id": entry_id,
                        "pos": d.get("pos") or "",
                        "source": d.get("source") or "",
                        "original_content": d.get("text") or "",
                        "translated_result": d.get("translation") or "",
                        "level": d.get("level") or "",
                        "examples": d.get("example") or [],
                    }
                )
            if senses_payload:
                r2 = requests.post(
                    f"{rest}/dictionary_senses",
                    headers=headers,
                    params={"on_conflict": "entry_id,pos,original_content"},
                    json=senses_payload,
                    timeout=10,
                )
                try:
                    print("HTTP_UPSERT_SENSES_STATUS", r2.status_code)
                except Exception:
                    pass
            return
        except Exception as e:
            try:
                print("HTTP_UPSERT_EXCEPTION", str(e))
            except Exception:
                pass
            return
    try:
        src_lang, tgt_lang = _map_languages(language_slug)
        head_payload = {
            "language_slug": language_slug,
            "source_language": src_lang,
            "target_language": tgt_lang,
            "entry": entry,
            "word": data.get("word") or entry,
            "pos": data.get("pos") or [],
            "pronunciation": data.get("pronunciation") or [],
            "verbs": data.get("verbs") or [],
            "data": data,
        }
        head_res = (
            client.table("dictionary_entries")
            .upsert(head_payload, on_conflict="language_slug,entry")
            .select("id")
            .execute()
        )
        head_rows = getattr(head_res, "data", [])
        try:
            logger.info("UPSERT_HEAD_ROWS=%s", len(head_rows))
        except Exception:
            pass
        try:
            print("UPSERT_HEAD_ROWS", len(head_rows))
        except Exception:
            pass
        if not head_rows:
            return
        entry_id = head_rows[0]["id"]

        senses_payload: List[Dict[str, Any]] = []
        for d in data.get("definition", []) or []:
            senses_payload.append(
                {
                    "entry_id": entry_id,
                    "pos": d.get("pos") or "",
                    "source": d.get("source") or "",
                    "original_content": d.get("text") or "",
                    "translated_result": d.get("translation") or "",
                    "level": d.get("level") or "",
                    "examples": d.get("example") or [],
                }
            )
        if senses_payload:
            res = client.table("dictionary_senses").upsert(
                senses_payload,
                on_conflict="entry_id,pos,original_content",
            ).execute()
            try:
                logger.info("UPSERT_SENSES_ROWS=%s", len(getattr(res, "data", []) or []))
            except Exception:
                pass
            try:
                print("UPSERT_SENSES_ROWS", len(getattr(res, "data", []) or []))
            except Exception:
                pass
    except Exception as e:
        try:
            logger.warning("SUPABASE_UPSERT_EXCEPTION=%s", str(e))
        except Exception:
            pass
        try:
            print("SUPABASE_UPSERT_EXCEPTION", str(e))
        except Exception:
            pass
        return
