# -*- coding: utf-8 -*-
"""팀 규칙 자동 검사기.

추천을 내놓기 전에 이걸 통과시킨다. 수동으로 확인하다 보면
합법성·SP 합계·도구 중복 같은 건 반드시 놓친다.

검사 항목:
  1. 현 레귤레이션 합법 여부          (KB index 의 legal 플래그)
  2. 종족 조항 — 같은 종 2마리 금지
  3. 지닌도구 중복 금지
  4. SP 배분 — 스탯당 0~32, 합계 최대 66
  5. 메가 — 전투 중 1회이므로 메가스톤 보유는 여러 마리여도 되지만 경고
  6. 팀 크기 — 싱글 6등록 (선발은 3)
  7. (참고) 사용률 순위 — 비주류 여부 표시

팀 파일 형식 (JSON):
  [
    {"name": "화강돌", "item": "자뭉열매", "nature": "무사태평",
     "sp": {"hp": 32, "atk": 0, "def": 32, "spa": 0, "spd": 2, "spe": 0},
     "moves": ["트릭룸", "도깨비불", "폴터가이스트", "아픔나누기"]},
    ...
  ]
sp / item / moves 는 생략 가능하며, 있는 것만 검사한다.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from battle_rules import SP_STAT_MAX, SP_TOTAL_MAX, sp_spread_valid  # noqa: E402
from i18n import L, validate_lang  # noqa: E402

KB_INDEX = "knowledge_base/index.json"
DATASET = "champs_singles.json"
TEAM_SIZE = 6
BRING_SIZE = 3
LANG = "ko"


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.notes: list[str] = []

    def err(self, m): self.errors.append(m)
    def warn(self, m): self.warns.append(m)
    def note(self, m): self.notes.append(m)

    @property
    def ok(self) -> bool:
        return not self.errors

    def show(self) -> None:
        for m in self.errors:
            print("  [%s] %s" % (L(LANG, "fail"), m))
        for m in self.warns:
            print("  [%s] %s" % (L(LANG, "warn"), m))
        for m in self.notes:
            print("  [%s] %s" % (L(LANG, "note"), m))
        print()
        print("%s: %s (%s %d / %s %d)"
              % (L(LANG, "verdict"),
                 L(LANG, "pass") if self.ok else L(LANG, "fail"),
                 L(LANG, "fail"), len(self.errors), L(LANG, "warn"), len(self.warns)))


def load_index(path: str = KB_INDEX) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_movesets(dataset: str = DATASET) -> dict[str, set[str]]:
    """포켓몬(한글명) -> 쓸 수 있는 기술(한글명) 집합.

    단일 데이터셋(champs_*.json)의 `learnset` 필드를 쓴다. 이 필드는
    champs_dataset.py 가 원종 습득기 ∪ 모든 usage 파일에서 관측된 기술(폼별)을 합쳐서
    만든 것이므로, 과거에 data/pkmnchamps 를 직접 훑던 것과 동일한 결과를 낸다.

    pokemon.json 의 `moves`(습득기 목록)만 믿으면 안 된다 — 몽얌나 치유소원(습득기엔
    없는데 사용률 94.1%)이나 켄타로스 팔데아 화염종 도깨비불(폼 기술이라 원종 데이터에
    누락) 같은 경우가 있다. learnset 은 습득기 ∪ 관측 기술이라 이를 모두 잡는다.
    """
    out: dict[str, set[str]] = {}
    if not os.path.exists(dataset):
        return out
    with open(dataset, encoding="utf-8") as f:
        ds = json.load(f)
    for p in ds.get("pokemon", []):
        ko = p.get("pokemon_ko")
        if ko:
            out[ko] = set(p.get("learnset") or [])
        # usage 에 등장한 기술도 보강 (learnset 과 중복되어 무해)
        for m in (p.get("usage", {}).get("moves") or []):
            if ko and m.get("name_ko"):
                out.setdefault(ko, set()).add(m["name_ko"])
    return out


def load_meta_sets(dataset: str = "champs_singles.json") -> dict[str, dict]:
    """포켓몬(한글명) -> 메타 1위 성격/SP 스프레드.

    기술 채용률만 보고 세트를 짜면 아키타입을 착각한다. 예를 들어 만마드의
    울부짖기 67% 는 '방어형 장판 스톨' 세팅의 수치라서, 공격형으로 짜면 무의미하다.
    그래서 지정한 SP 방향이 메타 1위 스프레드와 어긋나면 경고한다.
    """
    out: dict[str, dict] = {}
    if not os.path.exists(dataset):
        return out
    with open(dataset, encoding="utf-8") as f:
        ds = json.load(f)
    for p in ds.get("pokemon", []):
        u = p.get("usage", {})
        nats = u.get("natures") or []
        sps = u.get("ev_spreads") or []
        if not (nats or sps):
            continue
        top = (sps[0].get("ev_points") or {}) if sps else {}
        out[p["pokemon_ko"]] = {
            "nature": nats[0]["name_ko"] if nats else None,
            "nature_pct": nats[0]["percentage"] if nats else "",
            "spread": top,
            "spread_pct": sps[0].get("percentage", "") if sps else "",
        }
    return out


def check_archetype(name: str, slot: dict, meta: dict) -> list[str]:
    """지정 SP 가 메타 1위 스프레드와 아키타입이 다르면 경고 문자열을 만든다."""
    sp = slot.get("sp")
    if not sp or not meta:
        return []
    top = meta.get("spread") or {}
    if not top:
        return []
    m_atk = (top.get("attack_points", 0) or 0) + (top.get("sp_atk_points", 0) or 0)
    m_spe = top.get("speed_points", 0) or 0
    my_atk = sp.get("atk", 0) + sp.get("spa", 0)
    my_spe = sp.get("spe", 0)
    fmt = "%d/%d/%d/%d/%d/%d" % (
        top.get("hp_points", 0), top.get("attack_points", 0), top.get("defense_points", 0),
        top.get("sp_atk_points", 0), top.get("sp_def_points", 0), top.get("speed_points", 0))
    msgs = []
    if my_atk >= 16 and m_atk == 0:
        msgs.append("%s — 공격에 %d 투자했는데 메타 1위 스프레드는 %s (%s, 공격 투자 0 = 방어형). "
                    "기술 채용률이 방어형 세팅에서 나온 값일 수 있으니 확인할 것"
                    % (name, my_atk, fmt, meta.get("spread_pct", "")))
    if m_spe >= 16 and my_spe == 0:
        msgs.append("%s — 메타 1위 스프레드가 %s (스피드 투자형). 저속 세팅은 의도적 이탈인지 확인"
                    % (name, fmt))
    return msgs


def load_legal_items(dataset: str = "champs_singles.json") -> set[str]:
    """실제로 쓰이는 도구 이름 집합.

    items.json 의 regulationMB 플래그는 못 믿는다. 생명의구슬은 플래그가 False 인데
    따라큐가 86.6% 채용 중이다(포켓몬 쪽 데스판·모르페코와 같은 문제).
    그래서 '현재 사용률에 등장하는 도구' 를 합법으로 본다.
    """
    if not os.path.exists(dataset):
        return set()
    with open(dataset, encoding="utf-8") as f:
        ds = json.load(f)
    out = set()
    for p in ds.get("pokemon", []):
        for it in p.get("usage", {}).get("held_items", []) or []:
            if it.get("name_ko"):
                out.add(it["name_ko"])
    return out


def find_mon(index: dict, name: str) -> dict | None:
    for e in index["pokemon"]:
        if e.get("name_ko") == name or e.get("showdown_id") == name:
            return e
    # 부분 일치 폴백 (폼 이름 등)
    for e in index["pokemon"]:
        if name in (e.get("name_ko") or ""):
            return e
    return None


def _disp_name(name: str, index: dict) -> str:
    """한국어 name -> 현재 언어 표시명. 매칭 안 되면 name 그대로."""
    if LANG == "ko":
        return name
    for e in index["pokemon"]:
        if e.get("name_ko") == name:
            if LANG == "en":
                return e.get("name_en") or name
            if LANG == "ja":
                return e.get("name_ja") or e.get("name_ko") or name
    return name


def validate(team: list[dict], index: dict,
             legal_items: set[str] | None = None,
             movesets: dict[str, set[str]] | None = None,
             meta_sets: dict[str, dict] | None = None) -> Report:
    r = Report()
    legal_items = legal_items or set()
    movesets = movesets or {}
    meta_sets = meta_sets or {}

    if len(team) != TEAM_SIZE:
        r.warn("등록 %d마리 — 싱글 규정은 %d마리 등록 → %d마리 선발"
               % (len(team), TEAM_SIZE, BRING_SIZE))

    seen_species: dict[str, str] = {}
    seen_items: dict[str, str] = {}
    stone_holders: list[str] = []

    for slot in team:
        name = slot.get("name") or "?"
        e = find_mon(index, name)
        dn = _disp_name(name, index)   # 표시용 (현재 언어)

        # 1) 존재 + 합법
        if e is None:
            r.err("%s — 지식베이스에 없음 (이름 오타이거나 미수록)" % dn)
            continue
        if e.get("legal") is False:
            r.err("%s — 현 레귤레이션(M-B) 불법" % dn)
        if e.get("pick_rank"):
            r.note("%s — 사용률 %d위/%s" % (dn, e["pick_rank"], e.get("usage_total", "?")))
        else:
            r.note("%s — 사용률 데이터 없음 (완전 비주류)" % dn)

        # 2) 종족 조항: 같은 도감번호면 폼이 달라도 같은 종
        key = str(e.get("pokedex_id"))
        if key in seen_species:
            r.err("종족 조항 위반: %s 와 %s 는 같은 종(#%s)" % (seen_species[key], dn, key))
        else:
            seen_species[key] = dn

        # 3) 도구 중복
        item = slot.get("item")
        if item:
            if item in seen_items:
                r.err("도구 중복: '%s' 를 %s 와 %s 가 같이 지님"
                      % (item, seen_items[item], dn))
            else:
                seen_items[item] = dn
            if legal_items and item not in legal_items:
                r.warn("%s 의 도구 '%s' — 현재 사용률 데이터에 없음 "
                       "(이름 오타이거나 아무도 안 쓰는 도구)" % (dn, item))
            if "나이트" in item or item.lower().endswith("ite"):
                stone_holders.append(dn)

        # 3.5) 기술 습득 가능 여부
        pool = movesets.get(name) or movesets.get(e.get("name_ko") or "")
        moves = slot.get("moves") or []
        if pool and moves:
            unknown = [m for m in moves if m not in pool]
            if unknown:
                r.err("%s — 습득 불가하거나 이름이 틀린 기술: %s"
                      % (dn, ", ".join(unknown)))
        if len(moves) > 4:
            r.err("%s — 기술 %d개 (최대 4개)" % (dn, len(moves)))

        # 4) SP
        sp = slot.get("sp")
        if sp:
            ok, msg = sp_spread_valid(sp)
            if not ok:
                r.err("%s SP 위반: %s (스탯당 0~%d, 합 %d)"
                      % (dn, msg, SP_STAT_MAX, SP_TOTAL_MAX))
            else:
                total = sum(sp.values())
                if total < SP_TOTAL_MAX:
                    r.warn("%s SP %d/%d — %d 포인트 남음"
                           % (dn, total, SP_TOTAL_MAX, SP_TOTAL_MAX - total))

        # 아키타입 불일치 — 채용률을 엉뚱한 세팅에서 가져왔을 신호
        for m in check_archetype(dn, slot, meta_sets.get(name) or {}):
            r.warn(m)

        # 메가스톤 소지자가 실제로 메가 가능한 종인지
        if item and e.get("mega") is None and ("나이트" in (item or "")):
            r.warn("%s — 메가스톤을 들었는데 KB 에 메가 정보 없음 (%s)" % (dn, item))

    # 5) 메가
    if len(stone_holders) > 1:
        r.warn("메가스톤 보유 %d마리 (%s) — 전투 중 메가진화는 1회뿐이라 "
               "선발 3마리 안에 2개 이상 넣으면 1개는 놀게 된다"
               % (len(stone_holders), ", ".join(stone_holders)))

    return r


def main() -> None:
    ap = argparse.ArgumentParser(description="팀 규칙 검사")
    ap.add_argument("team", help="팀 JSON 파일 경로")
    ap.add_argument("--index", default=KB_INDEX)
    ap.add_argument("--format", default="singles", choices=["singles", "doubles"],
                    help="싱글(기본, 6등록→3선발) / 더블(6등록→4선발)")
    ap.add_argument("--lang", default="ko", choices=["ko", "en", "ja"], help="출력 언어")
    a = ap.parse_args()

    global LANG, BRING_SIZE
    LANG = validate_lang(a.lang)

    if not os.path.exists(a.team):
        print("파일 없음: %s" % a.team)
        raise SystemExit(2)
    with open(a.team, encoding="utf-8") as f:
        team = json.load(f)
    if isinstance(team, dict):
        team = team.get("team") or team.get("pokemon") or []

    # 포맷에 따라 데이터셋·선발 수 선택
    dataset = "champs_%s.json" % a.format
    if a.format == "doubles":
        BRING_SIZE = 4

    index = load_index(a.index)
    print("=== %s: %s (%d) [%s] ===" % (L(LANG, "team_check"), a.team, len(team), a.format))
    r = validate(team, index, load_legal_items(dataset), load_movesets(dataset),
                 load_meta_sets(dataset))
    r.show()
    raise SystemExit(0 if r.ok else 1)


if __name__ == "__main__":
    main()
