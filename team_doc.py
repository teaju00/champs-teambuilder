# -*- coding: utf-8 -*-
"""팀 문서 자동 생성기.

팀 JSON -> 팀/<이름>.md 를 만든다. 데이터 기반으로 채울 수 있는 섹션(구성표,
실수치, 기술 채용률, 약점 분석, 속도 정렬)은 자동 생성하고, 전략·운영법 등
사람이 써야 할 섹션은 <!-- TEAM_DOC: ... --> 마커로 남겨둔다.

사용:
  python team_doc.py 팀/보유_트릭룸.json            # 신규 생성 (덮어쓰기)
  python team_doc.py 팀/보유_트릭룸.json --update     # 기존 MD의 수동 섹션 보존, 데이터만 갱신

마커로 묶인 영역은 --update 시 보존된다:
  <!-- TEAM_DOC:manual start --> ... <!-- TEAM_DOC:manual end -->
처음 생성하면 이 마커 안에 빈 템플릿(## 시너지 / ## 선발 가이드 / ## 운영법)이 들어간다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from battle_rules import (
    real_stat, sp_spread_valid, team_defensive_profile, type_multiplier,
    TYPE_KO, nature_up_down,
)
from i18n import L, type_names, type_name, stat_name, validate_lang

DATASET = "champs_singles.json"
LANG = "ko"


def _p_name(p: dict) -> str:
    """데이터셋 엔트리에서 현재 언어 포켓몬명."""
    if not p:
        return "?"
    if LANG == "en":
        return p.get("pokemon_en") or p.get("pokemon_ko", "?")
    if LANG == "ja":
        return p.get("pokemon_ja") or p.get("pokemon_ko", "?")
    return p.get("pokemon_ko", "?")

# 스탯 표시 순서
STAT_ORDER = ["hp", "atk", "def", "spa", "spd", "spe"]
# 데이터셋 base_stats 키 -> 우리 내부 키
BASE_KEY = {"hp": "hp", "attack": "atk", "defense": "def",
            "special-attack": "spa", "special-defense": "spd", "speed": "spe"}


def nature_mod(stat: str, nature_ko: str | None) -> float:
    """battle_rules.nature_up_down 의 alias (기존 호출 호환)."""
    return nature_up_down(stat, nature_ko)


def load_dataset(path: str = DATASET) -> dict[str, dict]:
    """한글명 -> 데이터셋 엔트리."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for p in json.load(f).get("pokemon", []):
            out[p["pokemon_ko"]] = p
    return out


def real_stats_row(base_stats: dict, sp: dict, nature_ko: str | None) -> dict[str, int]:
    """종족값 + SP + 성격 -> 실수치 dict (키 STAT_ORDER)."""
    out = {}
    for k in STAT_ORDER:
        bk = next((b for b, v in BASE_KEY.items() if v == k), k)
        base = base_stats.get(bk, base_stats.get(k, 0))
        spv = sp.get(k, 0)
        out[k] = real_stat(base, spv, is_hp=(k == "hp"), nature=nature_mod(k, nature_ko))
    return out


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(lines)


def gen_composition(team: list[dict], ds: dict[str, dict]) -> str:
    """팀 구성 표."""
    headers = ["#", "포켓몬", "순위", "타입", "역할", "도구", "성격", "특성"]
    rows = []
    for i, slot in enumerate(team, 1):
        name = slot.get("name", "?")
        p = ds.get(name, {})
        disp = _p_name(p) if p else name
        rank = p.get("pick_rank")
        rank_s = "%d위" % rank if rank else "-"
        types = "/".join(type_names(LANG, p.get("types", [])))
        role = slot.get("role", "")
        item = slot.get("item", "")
        nature = slot.get("nature", "")
        ability = slot.get("ability", "")
        rows.append([i, disp, rank_s, types, role, item, nature, ability])
    return md_table(headers, rows)


def gen_detail(team: list[dict], ds: dict[str, dict]) -> str:
    """포켓몬별 상세 (종족값/SP/실수치 표 + 기술 채용률)."""
    parts = []
    for i, slot in enumerate(team, 1):
        name = slot.get("name", "?")
        role = slot.get("role", "")
        p = ds.get(name, {})
        disp = _p_name(p) if p else name
        base_stats = p.get("base_stats", {})
        sp = slot.get("sp", {})
        nature = slot.get("nature")
        real = real_stats_row(base_stats, sp, nature)
        title = "### %d. %s" % (i, disp)
        if role:
            title += " — %s" % role
        parts.append(title)
        parts.append("")
        # 종족값 / SP / 실수치 표
        headers = [""] + [stat_name(LANG, k) for k in STAT_ORDER]
        rows = [
            [L(LANG, "base_stats")] + [base_stats.get(next((b for b, v in BASE_KEY.items() if v == k), k),
                                        base_stats.get(k, "-")) for k in STAT_ORDER],
            ["SP"] + [sp.get(k, 0) for k in STAT_ORDER],
            [L(LANG, "real_stats")] + [real[k] for k in STAT_ORDER],
        ]
        parts.append(md_table(headers, rows))
        parts.append("")
        # 기술 채용률 (데이터셋 usage.moves)
        moves = slot.get("moves", [])
        if moves:
            usage_moves = {m["name_ko"]: m.get("percentage", "")
                           for m in p.get("usage", {}).get("moves", [])}
            line = "**기술**: " + " / ".join(
                "%s(%s)" % (m, usage_moves.get(m, "")) if usage_moves.get(m) else m
                for m in moves)
            parts.append(line)
            parts.append("")
        # 약점 (개별)
        types = p.get("types", [])
        if types:
            weak = [t for t in TYPE_KO if type_multiplier(t, *types) >= 2.0]
            resist = [TYPE_KO[t] for t in TYPE_KO if 0 < type_multiplier(t, *types) < 1.0]
            immune = [type_name(LANG, t) for t in TYPE_KO if type_multiplier(t, *types) == 0]
            bits = []
            if weak:
                bits.append(L(LANG, "weak") + " " + "/".join(type_name(LANG, t) for t in
                            sorted(weak, key=lambda x: -type_multiplier(x, *types))))
            if immune:
                bits.append(L(LANG, "immune") + " " + "/".join(immune))
            if bits:
                parts.append("**" + disp + "** — " + " · ".join(bits))
                parts.append("")
    return "\n".join(parts)


def gen_speed(team: list[dict], ds: dict[str, dict]) -> str:
    """속도 정렬 (트릭룸 컨셉 파악용). 메가 시 메가 스피드도 표시."""
    rows = []
    for slot in team:
        name = slot.get("name", "?")
        p = ds.get(name, {})
        disp = _p_name(p) if p else name
        sp = slot.get("sp", {})
        nature = slot.get("nature")
        base_spd = p.get("base_stats", {}).get("speed", 0)
        spd = real_stat(base_spd, sp.get("spe", 0), nature=nature_mod("spe", nature))
        rows.append((spd, disp))
        # 메가 스피드
        for mg in p.get("megas", []):
            mspd = mg.get("base_stats", {}).get("speed", 0)
            mreal = real_stat(mspd, sp.get("spe", 0), nature=nature_mod("spe", nature))
            if mreal != spd:
                rows.append((mreal, "메가" + disp))
    rows.sort()
    lines = ["## " + L(LANG, "speed_order"), ""]
    lines.append("```")
    for spd, name in rows:
        lines.append("%4d  %s" % (spd, name))
    lines.append("```")
    return "\n".join(lines)


def gen_weakness(team: list[dict], ds: dict[str, dict]) -> str:
    """팀 전체 약점 분석 (team_defensive_profile)."""
    types_list = []
    names = []
    for slot in team:
        p = ds.get(slot.get("name", ""), {})
        if p.get("types"):
            types_list.append(tuple(p["types"]))
            names.append(_p_name(p) if p else slot["name"])
    if not types_list:
        return ""
    profile = team_defensive_profile(types_list)
    lines = ["## " + L(LANG, "team_weakness"), ""]
    lines.append(L(LANG, "members") + ": " + ", ".join(names))
    lines.append("")
    weak = profile.get("약점_겹침", [])
    if weak:
        lines.append("**%s**:" % L(LANG, "weak_overlap"))
        for w in weak:
            lines.append("- %s: %d마리 노출" % (w["타입"], w["노출_팀원수"]))
    safe = profile.get("안전한_타입", [])
    if safe:
        lines.append("")
        lines.append("**두드러진 약점 없는 타입**: " + ", ".join(safe[:10]))
    return "\n".join(lines)


def gen_sp_check(team: list[dict]) -> str:
    """SP 배분 검증 요약."""
    lines = ["## " + L(LANG, "sp_alloc"), ""]
    all_ok = True
    for slot in team:
        sp = slot.get("sp")
        if not sp:
            continue
        ok, msg = sp_spread_valid(sp)
        if not ok:
            all_ok = False
        mark = "✓" if ok else "✗"
        lines.append("- %s %s — %s" % (mark, slot.get("name", "?"), msg))
    return "\n".join(lines)


# 수동 섹션 템플릿 (마커 안에 들어감)
MANUAL_TEMPLATE = """## 팀 시너지 & 전략
<!-- 왜 이 조합인지, 장판기/교체 타이밍/메가진화 포인트 -->

## 선발 가이드
<!-- 상대 불특정 시 기본 3마리 + 매치업별 교체 -->

## 운영법
<!-- 기본 흐름, 턴 운영, 잔실수 방지 -->

## 세팅 근거
<!-- 기술 채용률을 인용할 때 그 수치가 어느 아키타입에서 나왔는지 -->"""


def build_doc(team: list[dict], ds: dict[str, dict], team_name: str, fmt: str) -> str:
    lines = []
    lines.append("# %s — Pokémon Champions %s" % (team_name, fmt))
    lines.append("")
    lines.append("> %s: %s · 6 → %d" %
                 (L(LANG, "format"), fmt, 3 if fmt == "싱글" else 4))
    lines.append("> validate: `python validate_team.py 팀/%s.json`" % team_name)
    lines.append("> [%s.json](%s.json)" % (team_name, team_name))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## " + L(LANG, "team_config"))
    lines.append("")
    lines.append(gen_composition(team, ds))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## " + L(LANG, "detail_per_mon"))
    lines.append("")
    lines.append(gen_detail(team, ds))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(gen_speed(team, ds))
    lines.append("")
    lines.append(gen_weakness(team, ds))
    lines.append("")
    lines.append(gen_sp_check(team))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("<!-- TEAM_DOC:manual start -->")
    lines.append(MANUAL_TEMPLATE)
    lines.append("<!-- TEAM_DOC:manual end -->")
    lines.append("")
    return "\n".join(lines)


def update_doc(existing: str, team: list[dict], ds: dict[str, dict],
               team_name: str, fmt: str) -> str:
    """기존 MD의 수동 섹션(마커 안)을 보존하고 데이터 섹션만 갱신."""
    # 기존 수동 섹션 추출
    m = re.search(r"<!-- TEAM_DOC:manual start -->.*?<!-- TEAM_DOC:manual end -->",
                  existing, re.S)
    manual = m.group(0) if m else None
    new = build_doc(team, ds, team_name, fmt)
    if manual:
        new = re.sub(r"<!-- TEAM_DOC:manual start -->.*?<!-- TEAM_DOC:manual end -->",
                     manual, new, flags=re.S)
    return new


def main() -> None:
    ap = argparse.ArgumentParser(description="팀 문서 자동 생성")
    ap.add_argument("team", help="팀 JSON 파일 경로")
    ap.add_argument("--dataset", default=DATASET)
    ap.add_argument("--update", action="store_true",
                    help="기존 MD의 수동 섹션 보존, 데이터만 갱신")
    ap.add_argument("--format", default="singles", choices=["singles", "doubles"])
    ap.add_argument("--lang", default="ko", choices=["ko", "en", "ja"], help="출력 언어")
    a = ap.parse_args()

    global LANG
    LANG = validate_lang(a.lang)

    if not os.path.exists(a.team):
        print("파일 없음: %s" % a.team)
        raise SystemExit(2)
    with open(a.team, encoding="utf-8") as f:
        team = json.load(f)
    if isinstance(team, dict):
        team = team.get("team") or team.get("pokemon") or []

    ds = load_dataset(a.dataset)
    team_name = os.path.splitext(os.path.basename(a.team))[0]
    fmt = "싱글" if a.format == "singles" else "더블"

    out_path = os.path.splitext(a.team)[0] + ".md"
    if a.update and os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = f.read()
        doc = update_doc(existing, team, ds, team_name, fmt)
    else:
        doc = build_doc(team, ds, team_name, fmt)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print("[OK] %s 생성 (%d자)" % (out_path, len(doc)))


if __name__ == "__main__":
    main()
