# -*- coding: utf-8 -*-
"""
지식베이스 검색 헬퍼 (대화 추천 시 빠른 조회용).

ZCode 가 AGENTS.md 절차대로 팀 추천할 때, 이 스크립트로
포켓몬/타입/조건으로 빠르게 검색한다. Bash 로 직접 실행:

  python kb_search.py 한카리아스            # 포켓몬 상세
  python kb_search.py --type 드래곤          # 타입별 목록
  python kb_search.py --teammates 한카리아스  # 자주 같이 쓰이는 짝
  python kb_search.py --strong                # 종족값 상위 10
  python kb_search.py --team 한카리아스 리자몽  # 팀 약점 분석

출력은 간결하게. 상세가 필요하면 pokemon/<id>.md 를 직접 읽는다.
"""

import argparse
import json
import os
import re
import sys

# Windows 기본 콘솔은 cp949 라서 한글이 깨지고 '—' 같은 문자에선 죽는다. UTF-8 로 고정.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import sys

from battle_rules import (
    type_multiplier, describe_type_effectiveness, labelize_types,
    team_defensive_profile,
)
from i18n import L, type_names, type_name, validate_lang

KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
LANG = "ko"   # main() 에서 --lang 로 덮어씀


def _p_name(entry: dict) -> str:
    """현재 언어의 포켓몬 이름."""
    if LANG == "en":
        return entry.get("name_en") or entry.get("pokemon_en") or entry.get("name_ko", "?")
    if LANG == "ja":
        return entry.get("name_ja") or entry.get("pokemon_ja") or entry.get("name_ko", "?")
    return entry.get("name_ko") or entry.get("pokemon_ko", "?")


def _list_field(entry: dict, base: str) -> list:
    """top_moves/top_items/abilities 를 현재 언어로. _en/_ja 접미사 우선, 없으면 base."""
    if LANG == "en":
        v = entry.get(base + "_en")
        if v:
            return v
    elif LANG == "ja":
        v = entry.get(base + "_ja")
        if v:
            return [x for x in v if x]  # name_ja 결손 항목 제거
    return entry.get(base, [])


def _types(entry: dict) -> list[str]:
    """현재 언어의 타입명 리스트. index 의 types(영문코드)를 i18n 변환."""
    codes = entry.get("types") or []
    if not codes:
        return entry.get("types_ko") or []
    return type_names(LANG, codes)


def _load_index():
    with open(os.path.join(KB_DIR, "index.json"), encoding="utf-8") as f:
        return json.load(f)


def _find_entry(idx, query):
    """한국어명/영문명/일본어명/showdown_id 로 포켓몬 찾기."""
    q = query.strip().lower()
    for p in idx["pokemon"]:
        if (p.get("name_ko") == query or
                p.get("name_en", "").lower() == q or
                p.get("name_ja") == query or
                p.get("showdown_id") == q):
            return p
    # 부분 매칭
    for p in idx["pokemon"]:
        if (q in (p.get("name_ko") or "").lower()
                or q in (p.get("name_en") or "").lower()
                or q in (p.get("name_ja") or "")):
            return p
    return None


def _read_teammates(showdown_id):
    path = os.path.join(KB_DIR, "pokemon", f"{showdown_id}.md")
    if not os.path.exists(path):
        return []
    doc = open(path, encoding="utf-8").read()
    m = re.search(r"## 자주 같이 쓰이는 팀원\n(.+?)(?=\n##|\Z)", doc, re.S)
    if not m:
        return []
    return [s.strip() for s in re.split(r"[,·]", m.group(1)) if s.strip()]


def show_pokemon(idx, query):
    e = _find_entry(idx, query)
    if not e:
        print(L(LANG, "no_result") % query)
        return
    print("### %s (%s) [%s]" % (_p_name(e), e.get("name_en", ""),
                                 "/".join(_types(e))))
    print("%s: %s | %s: %s | %s: #%s" % (
        L(LANG, "showdown_id"), e["showdown_id"],
        L(LANG, "bst"), e.get("base_total"),
        L(LANG, "dex"), e.get("pokedex_id")))
    print("%s: %s" % (L(LANG, "top_moves"), ", ".join(_list_field(e, "top_moves"))))
    print("%s: %s" % (L(LANG, "top_items"), ", ".join(_list_field(e, "top_items"))))
    print("%s: %s" % (L(LANG, "abilities"), ", ".join(_list_field(e, "abilities"))))
    print("%s: knowledge_base/%s" % (L(LANG, "detail"), e["doc_path"]))


def list_by_type(idx, type_ko):
    # type_ko 는 한글 타입명. 모든 언어 입력을 허용하기 위해 index 의 types_ko 와 매칭.
    matches = [p for p in idx["pokemon"] if type_ko in (p.get("types_ko") or [])]
    matches.sort(key=lambda p: -(p.get("base_total") or 0))
    print("### %s — %s (%d)" % (type_ko, L(LANG, "type_list"), len(matches)))
    for p in matches[:20]:
        print("  %-12s [%s] %s %s | %s" % (
            _p_name(p), "/".join(_types(p)), L(LANG, "bst"), p.get("base_total"), p["doc_path"]))


def show_teammates(idx, query):
    e = _find_entry(idx, query)
    if not e:
        print(L(LANG, "no_result") % query)
        return
    tms = _read_teammates(e["showdown_id"])
    print("### " + L(LANG, "teammates_of") % _p_name(e))
    by_ko = {p["name_ko"]: p for p in idx["pokemon"]}
    for name in tms:
        p = by_ko.get(name)
        if p:
            print("  %-12s [%s] %s %s" % (
                _p_name(p), "/".join(_types(p)), L(LANG, "bst"), p.get("base_total")))
        else:
            print("  %-12s (-)" % name)


def show_strong(idx, n=10):
    ranked = sorted(idx["pokemon"], key=lambda p: -(p.get("base_total") or 0))
    print("### " + L(LANG, "bst_top") % n)
    for p in ranked[:n]:
        print("  %-12s [%s] %s %s" % (
            _p_name(p), "/".join(_types(p)), L(LANG, "bst"), p.get("base_total")))


def analyze_team(idx, queries):
    """여러 포켓몬의 타입 약점 분석."""
    types_list = []
    members = []
    for q in queries:
        e = _find_entry(idx, q)
        if e:
            types_list.append(tuple(e.get("types", [])))
            members.append(e)
    if not types_list:
        print(L(LANG, "no_result") % ", ".join(queries))
        return
    profile = team_defensive_profile(types_list)
    print("### " + L(LANG, "team_weakness"))
    print("%s: %s" % (L(LANG, "members"), ", ".join(_p_name(m) for m in members)))
    print(L(LANG, "weak_overlap") + ":")
    for w in profile.get("약점_겹침", [])[:8]:
        print("  %s: %d %s" % (
            type_name(LANG, _type_code(w["타입"])), w["노출_팀원수"], L(LANG, "members")))
    if profile.get("안전한_타입"):
        safe = [type_name(LANG, _type_code(t)) for t in profile["안전한_타입"][:6]]
        print("... " + ", ".join(safe))


# 한글 타입명 -> 영문 코드 (index 의 types_ko 역변환)
_TYPE_KO_TO_CODE = {"노말": "normal", "불꽃": "fire", "물": "water", "전기": "electric",
                    "풀": "grass", "얼음": "ice", "격투": "fighting", "독": "poison",
                    "땅": "ground", "비행": "flying", "에스퍼": "psychic", "벌레": "bug",
                    "바위": "rock", "고스트": "ghost", "드래곤": "dragon", "악": "dark",
                    "강철": "steel", "페어리": "fairy"}


def _type_code(ko_name: str) -> str:
    return _TYPE_KO_TO_CODE.get(ko_name, ko_name)


def main():
    ap = argparse.ArgumentParser(description="지식베이스 검색 (팀 추천 헬퍼)")
    ap.add_argument("query", nargs="?", help="포켓몬 이름 (한국어/영문/showdown_id)")
    ap.add_argument("--type", help="해당 타입 포켓몬 목록 (예: 드래곤)")
    ap.add_argument("--teammates", metavar="POKEMON", help="자주 같이 쓰이는 팀원")
    ap.add_argument("--strong", action="store_true", help="종족합 상위 10")
    ap.add_argument("--team", nargs="+", help="팀 약점 분석 (포켓몬 여러 개)")
    ap.add_argument("--lang", default="ko", choices=["ko", "en", "ja"],
                    help="출력 언어 (기본 ko)")
    args = ap.parse_args()

    global LANG
    LANG = validate_lang(args.lang)

    idx = _load_index()
    if args.type:
        list_by_type(idx, args.type)
    elif args.teammates:
        show_teammates(idx, args.teammates)
    elif args.strong:
        show_strong(idx)
    elif args.team:
        analyze_team(idx, args.team)
    elif args.query:
        show_pokemon(idx, args.query)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
