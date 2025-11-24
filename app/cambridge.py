from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .cache import TTLCache


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


@dataclass
class Example:
    id: int
    text: str
    translation: str


@dataclass
class Definition:
    id: int
    pos: str
    source: str
    text: str
    translation: str
    level: str
    example: List[Example]


@dataclass
class Pronunciation:
    pos: str
    lang: str
    url: str
    pron: str


class CambridgeClient:
    def __init__(self, timeout: int = 10, cache_ttl: int = 1800):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.timeout = timeout
        self.cache = TTLCache(ttl_seconds=cache_ttl)

    def _language_mapping(self, slug_language: str) -> tuple[str, str]:
        nation = "us"
        if slug_language == "en":
            language = "english"
        elif slug_language == "uk":
            language = "english"
            nation = "uk"
        elif slug_language == "en-tw":
            language = "english-chinese-traditional"
        elif slug_language == "en-cn":
            language = "english-chinese-simplified"
        elif slug_language == "cn-en":
            language = "chinese-simplified-english"
            nation = ""
        else:
            raise ValueError("Unsupported language")
        return language, nation

    def _build_url(self, language: str, nation: str, entry: str) -> str:
        from urllib.parse import quote
        safe_entry = quote(entry.strip(), safe="-._~")
        base = "https://dictionary.cambridge.org"
        if nation:
            path = f"/{nation}/dictionary/{language}/{safe_entry}"
        else:
            path = f"/dictionary/{language}/{safe_entry}"
        return base + path

    def _fetch(self, url: str) -> Optional[str]:
        key = self.cache.make_key(url)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        try:
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code != 200:
                try:
                    print("FETCH_STATUS", r.status_code, r.url)
                except Exception:
                    pass
                return None
            self.cache.set(key, r.text)
            return r.text
        except requests.RequestException:
            return None

    def _parse_entry(self, html: str, source_hint: Optional[str] = None) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        siteurl = "https://dictionary.cambridge.org"

        word_el = soup.select_one(".hw.dhw")
        word = word_el.get_text(strip=True) if word_el else ""

        pos_elements = soup.select(".pos.dpos")
        pos = list(dict.fromkeys([el.get_text(strip=True) for el in pos_elements]))

        pronunciation: List[Pronunciation] = []
        for header in soup.select(".pos-header.dpos-h"):
            pos_node = header.select_one(".dpos-g")
            p = pos_node.get_text(strip=True) if pos_node else ""
            for node in header.select(".dpron-i"):
                lang = (node.select_one(".region.dreg") or {}).get_text(strip=True) if node.select_one(".region.dreg") else ""
                audio_src_el = node.select_one("audio source")
                audio_src = audio_src_el["src"].strip() if audio_src_el and audio_src_el.has_attr("src") else ""
                pron_text_el = node.select_one(".pron.dpron")
                pron_text = pron_text_el.get_text(strip=True) if pron_text_el else ""
                if audio_src or pron_text:
                    pronunciation.append(
                        Pronunciation(pos=p, lang=lang, url=(siteurl + audio_src) if audio_src else "", pron=pron_text)
                    )

        definitions: List[Definition] = []
        blocks = soup.select(".def-block.ddef_block")
        for i, block in enumerate(blocks):
            entry_el = block.find_parent(class_="entry-body__el")
            pos_text = ""
            if entry_el:
                pos_el = entry_el.select_one(".pos.dpos")
                pos_text = pos_el.get_text(strip=True) if pos_el else ""
            dict_el = block.find_parent(class_="dictionary")
            source = dict_el.get("data-id", "") if dict_el else ""
            text_el = block.select_one(".def.ddef_d.db")
            text = text_el.get_text(" ", strip=True) if text_el else ""
            trans_el = block.select_one(".def-body.ddef_b > span.trans.dtrans")
            translation = trans_el.get_text(" ", strip=True) if trans_el else ""
            level = ""
            level_candidates = [
                el.get_text(strip=True)
                for el in block.select(".epp-xref, .cefr, .dxref")
            ]
            for lv in level_candidates:
                if lv in {"A1", "A2", "B1", "B2", "C1", "C2"}:
                    level = lv
                    break
            if not level:
                raw = block.get_text(" ", strip=True)
                for lv in ("A1", "A2", "B1", "B2", "C1", "C2"):
                    if f" {lv} " in f" {raw} ":
                        level = lv
                        break

            examples: List[Example] = []
            for j, ex in enumerate(block.select(".def-body.ddef_b > .examp.dexamp")):
                eg_el = ex.select_one(".eg.deg")
                eg = eg_el.get_text(" ", strip=True) if eg_el else ""
                tr_el = ex.select_one(".trans.dtrans")
                tr = tr_el.get_text(" ", strip=True) if tr_el else ""
                examples.append(Example(id=j, text=eg, translation=tr))

            definitions.append(
                Definition(
                    id=i,
                    pos=pos_text,
                    source=source if source else (source_hint or ""),
                    text=text,
                    translation=translation,
                    level=level,
                    example=examples,
                )
            )

        # Fallbacks for Chinese→English pages where structure differs
        if not word:
            try:
                # title like "你好 in English - Cambridge Dictionary"
                title_txt = soup.title.get_text(strip=True) if soup.title else ""
                if " in English" in title_txt:
                    word = title_txt.split(" in English")[0]
            except Exception:
                pass
        if not word:
            word = source_hint or ""

        if not blocks:
            try:
                dict_el = soup.select_one(".dictionary")
                source = dict_el.get("data-id", "") if dict_el else (source_hint or "")
            except Exception:
                source = source_hint or ""
            defs = soup.select(".def.ddef_d")
            for i, def_el in enumerate(defs):
                text = def_el.get_text(" ", strip=True)
                trans_el = def_el.find_next("span", class_="trans dtrans")
                translation = trans_el.get_text(" ", strip=True) if trans_el else ""
                definitions.append(
                    Definition(id=i, pos="", source=source, text=text, translation=translation, level="", example=[])
                )

        if not pronunciation:
            for pnode in soup.select(".dpron"):
                pron_text = pnode.get_text(strip=True)
                par = pnode.parent
                reg_el = par.select_one(".region.dreg") if par else None
                lang = reg_el.get_text(strip=True) if reg_el else ""
                audio_src_el = par.select_one("audio source") if par else None
                audio_src = audio_src_el.get("src", "").strip() if audio_src_el and audio_src_el.has_attr("src") else ""
                if pron_text or audio_src:
                    pronunciation.append(
                        Pronunciation(pos="", lang=lang, url=("https://dictionary.cambridge.org" + audio_src) if audio_src else "", pron=pron_text)
                    )

        return {
            "word": word,
            "pos": pos,
            "pronunciation": [p.__dict__ for p in pronunciation],
            "definition": [
                {
                    "id": d.id,
                    "pos": d.pos,
                    "source": d.source,
                    "text": d.text,
                    "translation": d.translation,
                    "level": d.level,
                    "example": [e.__dict__ for e in d.example],
                }
                for d in definitions
            ],
        }

    def fetch_verbs(self, entry: str) -> List[Dict[str, Any]]:
        wiki = f"https://simple.wiktionary.org/wiki/{entry}"
        key = self.cache.make_key(wiki)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        html = self._fetch(wiki)
        if not html:
            self.cache.set(key, [])
            return []
        soup = BeautifulSoup(html, "html.parser")
        verbs: List[Dict[str, Any]] = []
        cells = soup.select(".inflection-table tr td")
        for cell in cells:
            cell_text = cell.get_text("\n", strip=True)
            if not cell_text:
                continue
            p = cell.find("p")
            if p:
                parts = [x.strip() for x in p.get_text("\n").split("\n") if x.strip()]
                if len(parts) >= 2:
                    verbs.append({"id": len(verbs), "type": parts[0], "text": parts[1]})
                else:
                    html_content = p.decode_contents()
                    if "<br" in html_content:
                        split = html_content.split("<br")
                        if len(split) >= 2:
                            type_txt = BeautifulSoup(split[0], "html.parser").get_text(strip=True)
                            text_txt = BeautifulSoup(split[1], "html.parser").get_text(strip=True)
                            if type_txt and text_txt:
                                verbs.append({"id": len(verbs), "type": type_txt, "text": text_txt})
        self.cache.set(key, verbs)
        return verbs

    def get_entry(self, slug_language: str, entry: str) -> Optional[Dict[str, Any]]:
        try:
            print("GET_ENTRY_LANG", slug_language)
        except Exception:
            pass
        if slug_language == "cn-en":
            try:
                print("CN_EN_AGGREGATE", entry)
            except Exception:
                pass
            agg = self._get_cn_en_aggregate(entry)
            if not agg:
                return None
            agg["verbs"] = []
            return agg
        language, nation = self._language_mapping(slug_language)
        url = self._build_url(language, nation, entry)
        html = self._fetch(url)
        if not html:
            return None
        parsed = self._parse_entry(html, source_hint=slug_language)
        if not parsed:
            return None
        parsed["verbs"] = self.fetch_verbs(entry)
        return parsed

    def _get_cn_en_aggregate(self, entry: str) -> Optional[Dict[str, Any]]:
        language, nation = self._language_mapping("cn-en")
        url = self._build_url(language, nation, entry)
        html = self._fetch(url)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if "/dictionary/english-chinese-simplified/" in href:
                links.append(href)
        if not links:
            return None
        siteurl = "https://dictionary.cambridge.org"
        pos_set: List[str] = []
        prons: List[Dict[str, Any]] = []
        defs: List[Dict[str, Any]] = []
        order: List[str] = []
        for href in links[:12]:
            sub_url = siteurl + href
            sub_html = self._fetch(sub_url)
            if not sub_html:
                continue
            parsed = self._parse_entry(sub_html, source_hint="en-cn")
            if not parsed:
                continue
            lemma = parsed.get("word", "")
            for p in parsed.get("pos", []):
                if p not in pos_set:
                    pos_set.append(p)
            for p in parsed.get("pronunciation", []):
                prons.append({
                    "pos": p.get("pos", ""),
                    "lang": p.get("lang", ""),
                    "url": p.get("url", ""),
                    "pron": p.get("pron", ""),
                    "lemma": lemma,
                })
            for d in parsed.get("definition", []):
                nd = {
                    "id": d.get("id", 0),
                    "pos": d.get("pos", ""),
                    "source": d.get("source", ""),
                    "text": d.get("text", ""),
                    "translation": d.get("translation", ""),
                    "level": d.get("level", ""),
                    "example": d.get("example", []),
                    "lemma": lemma,
                }
                defs.append(nd)
            if lemma and lemma not in order:
                order.append(lemma)
        if not defs and not prons and not pos_set:
            return None
        return {
            "word": entry,
            "pos": pos_set,
            "pronunciation": prons,
            "definition": defs,
            "order": order,
        }
