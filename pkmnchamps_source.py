# -*- coding: utf-8 -*-
"""pkmnchamps.com 데이터 추출기.

배경:
  pkmnchamps.com 은 한국 포켓몬 챔피언스 커뮤니티 사이트다.
  championsbattledata.com + PokeAPI 조합보다 이 사이트가 우수한 이유:

    - 기술/특성/도구 설명이 **한국어 원문**으로 들어있다 (PokeAPI 는 item 한국어가 아예 없음)
    - 기술에 priority(선공도) / target(범위) / flags(접촉·펀치·소리·파동·춤) 가 있다
    - regulationMA / regulationMB 로 **레귤레이션 합법 여부**를 직접 알 수 있다
    - 포켓몬별 전체 습득기(moves) 목록이 있다 (사용률 상위 10개가 아니라 전체)
    - /api/champions-data 로 **pick_rank(전체 사용률 순위)** 를 준다 -> 비주류 발굴용

  데이터 위치:
    1) 한국어 DB 5종  -> Next.js 청크 안 JSON.parse('...') 블롭 (청크 해시는 배포마다 바뀜)
    2) 가이드 본문     -> i18n 청크 안 "guide.*" 플랫 키맵
    3) 사용률 통계     -> /api/champions-data?action=list&regulation=..&month=..&format=..

  주의: 두 요청 모두 **Referer 헤더가 없으면 403** 이다. UA 만으로는 안 통한다.
        그리고 .js 응답은 charset 을 안 주므로 requests 가 ISO-8859-1 로 디코드한다
        -> 반드시 r.content.decode("utf-8") 로 받아야 한글이 깨지지 않는다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import requests

BASE = "https://pkmnchamps.com"
CACHE_DIR = "cache/pkmnchamps"
DATA_DIR = "data/pkmnchamps"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    # Referer 필수. 없으면 403 Forbidden.
    "Referer": BASE + "/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 각 DB 를 식별하는 대표 키 (블롭 순서는 빌드마다 바뀔 수 있으므로 내용으로 판별)
DB_PROBES = {
    "moves": "absorb",
    "items": "potion",
    "abilities": "adaptability",
}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch_text(s: requests.Session, path: str, referer: str | None = None) -> str:
    """UTF-8 을 강제해서 텍스트를 받는다 (.js 는 charset 을 안 알려줌)."""
    url = path if path.startswith("http") else BASE + path
    h = {"Referer": referer} if referer else {}
    r = s.get(url, headers=h, timeout=90)
    r.raise_for_status()
    return r.content.decode("utf-8", errors="replace")


def fetch_chunk(s: requests.Session, path: str) -> str:
    """청크를 받되 로컬 캐시를 먼저 본다 (해시가 파일명이라 안전하게 캐시 가능)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    fname = os.path.join(CACHE_DIR, path.rsplit("/", 1)[-1])
    if os.path.exists(fname):
        with open(fname, encoding="utf-8") as f:
            return f.read()
    body = fetch_text(s, path, referer=BASE + "/guide")
    with open(fname, "w", encoding="utf-8") as f:
        f.write(body)
    return body


# ---------------------------------------------------------------------------
# JS 문자열 리터럴 해석
# ---------------------------------------------------------------------------

def unescape_js(lit: str) -> str:
    """JS 문자열 리터럴 '본문'(따옴표 제외)을 실제 문자열로 되돌린다."""
    out: list[str] = []
    i, n = 0, len(lit)
    simple = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
    while i < n:
        c = lit[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        nxt = lit[i + 1] if i + 1 < n else ""
        if nxt == "u":
            if i + 2 < n and lit[i + 2] == "{":  # \u{1F525}
                j = lit.index("}", i)
                out.append(chr(int(lit[i + 3:j], 16)))
                i = j + 1
            else:
                out.append(chr(int(lit[i + 2:i + 6], 16)))
                i += 6
        elif nxt == "x":
            out.append(chr(int(lit[i + 2:i + 4], 16)))
            i += 4
        elif nxt in simple:
            out.append(simple[nxt])
            i += 2
        else:
            out.append(nxt)
            i += 2
    return _join_surrogates(out)


def _join_surrogates(chars: list[str]) -> str:
    """이모지가 \\uD83D\\uDD25 처럼 서로게이트 페어로 들어오므로 하나로 합친다.
    합치지 않으면 UTF-8 로 저장할 때 'surrogates not allowed' 로 죽는다."""
    out: list[str] = []
    i, n = 0, len(chars)
    while i < n:
        c = chars[i]
        o = ord(c) if len(c) == 1 else 0
        if 0xD800 <= o <= 0xDBFF and i + 1 < n and len(chars[i + 1]) == 1:
            lo = ord(chars[i + 1])
            if 0xDC00 <= lo <= 0xDFFF:
                out.append(chr(0x10000 + ((o - 0xD800) << 10) + (lo - 0xDC00)))
                i += 2
                continue
        if 0xD800 <= o <= 0xDFFF:  # 짝 없는 서로게이트는 버린다
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _read_js_string(text: str, start: int) -> tuple[str, int] | None:
    """text[start] 가 따옴표면 그 문자열 리터럴을 읽어 (값, 다음위치) 반환."""
    q = text[start]
    if q not in ("'", '"'):
        return None
    i = start + 1
    buf: list[str] = []
    while i < len(text):
        c = text[i]
        if c == "\\":
            buf.append(text[i:i + 2])
            i += 2
            continue
        if c == q:
            return unescape_js("".join(buf)), i + 1
        buf.append(c)
        i += 1
    return None


# ---------------------------------------------------------------------------
# 1) 한국어 DB 추출
# ---------------------------------------------------------------------------

def discover_chunks(s: requests.Session, page: str = "/guide/weather") -> list[str]:
    html = fetch_text(s, page, referer=BASE + "/guide")
    return sorted(set(re.findall(r"/_next/static/chunks/[A-Za-z0-9%\[\]/_.-]+\.js", html)))


def extract_json_blobs(body: str) -> list[object]:
    """청크 안 JSON.parse('...') 블롭을 모두 파싱한다."""
    out = []
    for m in re.finditer(r"JSON\.parse\(", body):
        got = _read_js_string(body, m.end())
        if not got:
            continue
        raw, _ = got
        if len(raw) < 200:
            continue
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def extract_databases(s: requests.Session) -> dict[str, object]:
    """청크들을 훑어 한국어 DB 7종을 찾아낸다.

    pokemon.json 은 전국도감 1025마리(기본 폼만, 도감번호 1:1)다.
    메가/리전폼은 별도로 `pokemon_id -> [폼]` 맵으로 들어있고, 각 폼이
    자기 종족값/타입/특성/레귤레이션을 따로 갖는다. 폼을 놓치면 합법 풀을 잘못 센다.
    """
    found: dict[str, object] = {}
    for path in discover_chunks(s):
        body = fetch_chunk(s, path)
        if "JSON.parse(" not in body:
            continue
        for obj in extract_json_blobs(body):
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                if "regulationMB" in obj[0] and "stats" in obj[0]:
                    found["pokemon"] = obj
                elif {"up", "down", "nameKo"} <= set(obj[0]):
                    found["natures"] = obj
            elif isinstance(obj, dict) and obj:
                k0 = next(iter(obj))
                v0 = obj[k0]
                # 숫자키 + 리스트값 = 폼 맵. formSuffix 유무로 리전폼/메가를 가른다.
                if k0.isdigit() and isinstance(v0, list) and v0 and isinstance(v0[0], dict):
                    key = "forms" if "formSuffix" in v0[0] else "megas"
                    found[key] = obj
                    continue
                for name, probe in DB_PROBES.items():
                    if probe in obj and isinstance(obj[probe], dict) and "nameKo" in obj[probe]:
                        found[name] = obj
        if len(found) == 7:
            break
    return found


# ---------------------------------------------------------------------------
# 2) 가이드 i18n 추출
# ---------------------------------------------------------------------------

_HANGUL = re.compile(r"[가-힣]")
_KANA = re.compile(r"[぀-ヿ]")


def _locale_score(v: str) -> int:
    """한국어일 가능성 점수. ko/en/ja 세 로케일이 같은 청크에 있어서 골라내야 한다."""
    if _HANGUL.search(v):
        return 2
    if _KANA.search(v):
        return 0
    return 1  # ASCII/이모지/숫자 — 세 로케일에서 값이 같은 경우가 많다


def extract_guide_i18n(s: requests.Session) -> dict[str, str]:
    """i18n 청크의 "guide.*" 플랫 키맵을 뽑는다.

    청크에 ko/en/ja 가 모두 들어있고 뒤에 나온 로케일이 앞을 덮어쓴다.
    그래서 키별로 모든 후보를 모은 뒤 한글 점수가 가장 높은 값을 고른다.
    """
    for path in discover_chunks(s):
        body = fetch_chunk(s, path)
        if '"guide.' not in body:
            continue
        cands: dict[str, list[str]] = {}
        for m in re.finditer(r'"(guide\.[A-Za-z0-9_.\-]+)"\s*:\s*', body):
            got = _read_js_string(body, m.end())
            if got:
                cands.setdefault(m.group(1), []).append(got[0])
        if not cands:
            continue
        out: dict[str, str] = {}
        for k, vs in cands.items():
            out[k] = max(vs, key=_locale_score)
        return out
    return {}


# ---------------------------------------------------------------------------
# 3) 사용률 통계 API
# ---------------------------------------------------------------------------

def fetch_reg_months(s: requests.Session) -> list[dict]:
    txt = fetch_text(s, "/api/champions-data?action=regMonths", referer=BASE + "/stats")
    return json.loads(txt)


def fetch_usage(s: requests.Session, regulation: str, month: str, fmt: str) -> list[dict]:
    path = ("/api/champions-data?action=list&regulation=%s&month=%s&format=%s"
            % (regulation, month, fmt))
    return json.loads(fetch_text(s, path, referer=BASE + "/stats"))


# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------

def _dump(name: str, obj) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    p = os.path.join(DATA_DIR, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p


def cmd_extract(s: requests.Session) -> None:
    print("=== 한국어 DB 추출 ===")
    dbs = extract_databases(s)
    for k in ("pokemon", "megas", "forms", "moves", "items", "abilities", "natures"):
        if k not in dbs:
            print("  [!] %s 못 찾음" % k)
            continue
        obj = dbs[k]
        n = len(obj)
        extra = ""
        if k == "pokemon":
            mb = sum(1 for p in obj if p.get("regulationMB"))
            ma = sum(1 for p in obj if p.get("regulationMA"))
            extra = " (M-B 합법 %d / M-A 합법 %d)" % (mb, ma)
        elif k in ("megas", "forms"):
            flat = [f for v in obj.values() for f in v]
            n = len(flat)
            extra = " (%d종에 걸침, M-B 합법 %d)" % (
                len(obj), sum(1 for f in flat if f.get("regulationMB")))
        elif k == "moves":
            extra = " (available %d)" % sum(1 for v in obj.values() if v.get("available"))
        print("  [OK] %-10s %5d%s -> %s" % (k, n, extra, _dump(k + ".json", obj)))

    print("\n=== 가이드 i18n 추출 ===")
    g = extract_guide_i18n(s)
    slugs = sorted({k.split(".")[1] for k in g})
    print("  [OK] %d 키 / 가이드 %d종: %s" % (len(g), len(slugs), ", ".join(slugs)))
    print("       -> %s" % _dump("guide_i18n.json", g))


def cmd_usage(s: requests.Session, only_latest: bool) -> None:
    combos = fetch_reg_months(s)
    if only_latest:
        combos = combos[:2]
    print("=== 사용률 통계 (%d 조합) ===" % len(combos))
    index = []
    for c in combos:
        reg, month, fmt = c["regulation"], c["month"], c["battle_format"]
        try:
            rows = fetch_usage(s, reg, month, fmt)
        except Exception as e:
            print("  [!] %s %s %s -> %s" % (reg, month, fmt, e))
            continue
        name = "usage_%s_%s_%s.json" % (reg, month, fmt)
        _dump(name, rows)
        index.append({"regulation": reg, "month": month, "format": fmt,
                      "count": len(rows), "file": name})
        print("  [OK] %-32s %-8s %-8s %4d마리" % (reg, month, fmt, len(rows)))
        time.sleep(0.3)
    _dump("usage_index.json", index)


def main() -> None:
    ap = argparse.ArgumentParser(description="pkmnchamps.com 데이터 추출기")
    ap.add_argument("--extract", action="store_true", help="한국어 DB + 가이드 i18n 추출")
    ap.add_argument("--usage", action="store_true", help="사용률 통계 전체 조합 수집")
    ap.add_argument("--latest-only", action="store_true", help="사용률은 최신 조합만")
    ap.add_argument("--all", action="store_true", help="전부")
    a = ap.parse_args()
    if not (a.extract or a.usage or a.all):
        a.all = True

    s = _session()
    if a.extract or a.all:
        cmd_extract(s)
    if a.usage or a.all:
        print()
        cmd_usage(s, a.latest_only)


if __name__ == "__main__":
    sys.exit(main())
