# -*- coding: utf-8 -*-
"""
포켓몬 챔피언스 AI용 지식베이스 생성기.

all_doubles.json (실제 사용 데이터) + 캐시(PokeAPI 효과) + battle_rules(공식 규칙)
을 결합해, AI 가 팀 빌딩에 바로 쓸 수 있는 청크 단위 지식베이스를 만든다.

출력 구조 (knowledge_base/):
  rules.md               - 챔피언스 공식 규칙 + 타입상성 (전역 컨텍스트)
  type_chart.md          - 타입 상성 표
  pokemon/<id>.md        - 포켓몬별 1문서 (234개)
  index.json             - 메타데이터 인덱스 (RAG 검색/임베딩용)
  summary.md             - 메타 요약 (자주 쓰이는 기술/아이템/특성 랭킹)

왜 이 구조인가:
  - LLM 컨텍스트에 포켓몬 전체를 한번에 넣기엔 너무 큼 -> 포켓몬별 문서로 분할.
  - RAG 시스템은 index.json 의 임베딩/키워드로 관련 포켓몬만 검색해 주입.
  - 규칙은 모든 팀빌딩에 공통이므로 별도 문서로 항상 포함.

실행:
  python kb_builder.py --data all_doubles.json --out knowledge_base
"""

import argparse
import json
import os
from collections import Counter

from battle_rules import (
    CHAMPIONS_RULES, MEGA_EVOLUTION, STATUS_CONDITIONS, MOVE_CHANGES,
    TYPE_KO, TYPE_CHART, STAT_LABEL_KO, DAMAGE_CLASS_KO,
    type_multiplier, describe_type_effectiveness, labelize_types,
    labelize_base_stats,
)
from data_hints import move_role_hint, item_role_hint, ability_role_hint


# ---------------------------------------------------------------------------
# 포켓몬별 문서 생성
# ---------------------------------------------------------------------------
def build_pokemon_doc(p: dict) -> tuple[str, str]:
    """포켓몬 1마리 -> (문서 id, markdown 본문)."""
    sid = p["showdown_id"]
    name_ko = p.get("pokemon_ko") or p["pokemon_en"]
    name_en = p["pokemon_en"]
    types = p.get("types", [])
    types_ko = labelize_types(types)
    bs = labelize_base_stats(p.get("base_stats", {}))
    usage = p.get("usage", {})

    lines = []
    # 헤더 — AI 가 빠르게 식별/검색 가능한 메타정보
    header = f"# {name_ko} ({name_en})"
    if types_ko:
        header += f" [{'/'.join(types_ko)}]"
    lines.append(header)
    meta_bits = [f"showdown_id: `{sid}`", f"포켓도감: #{p.get('pokedex_id','?')}"]
    if p.get("genus_ko"):
        meta_bits.append(f"분류: {p['genus_ko']}")
    # 사용률 순위 — 비주류 판단의 근거라 문서 맨 위에 둔다
    if p.get("pick_rank"):
        meta_bits.append(f"**사용률 {p['pick_rank']}위 / {p.get('usage_total','?')}**")
    elif p.get("legal"):
        meta_bits.append("**사용률 데이터 없음 (미개척)**")
    if p.get("form"):
        meta_bits.append(f"폼: `{p['form']}`")
    if p.get("legal") is False:
        meta_bits.append("⚠️ **현 레귤레이션 불법**")
    lines.append("> " + " | ".join(meta_bits))
    lines.append("")

    # 기본 정보
    if bs:
        lines.append("## 종족값")
        lines.append("| " + " | ".join(bs.keys()) + " |")
        lines.append("|" + "|".join(["---"] * len(bs)) + "|")
        lines.append("| " + " | ".join(str(v) for v in bs.values()) + " |")
        lines.append("")
    # 종족값 합
    if p.get("base_stats"):
        total = sum(p["base_stats"].values())
        lines.append(f"종족값 합계: **{total}**")
        lines.append("")

    # 특성
    abilities = usage.get("abilities", []) or p.get("abilities", [])
    if abilities:
        lines.append("## 특성")
        for a in abilities:
            ko = a.get("name_ko") or a.get("name_en", "?")
            hint = ability_role_hint(a.get("name_en", ""), a.get("detail"))
            tag = " (숨겨)" if a.get("is_hidden") else ""
            pct = a.get("percentage")
            line = f"- **{ko}**{tag}"
            if pct:
                line += f" (사용률 {pct})"
            if hint:
                line += f" — {hint}"
            lines.append(line)
        lines.append("")

    # 주요 지닌도구
    items = usage.get("held_items", [])
    if items:
        lines.append("## 주요 지닌도구 (사용률 순)")
        for it in items:
            ko = it.get("name_ko") or it.get("name_en", "?")
            pct = it.get("percentage", "")
            hint = item_role_hint(it.get("name_en", ""), it.get("detail"))
            line = f"- **{ko}** ({pct})"
            if hint:
                line += f" — {hint}"
            lines.append(line)
        lines.append("")

    # 주요 기술
    moves = usage.get("moves", [])
    if moves:
        lines.append("## 주요 기술 (사용률 순)")
        for m in moves:
            ko = m.get("name_ko") or m.get("name_en", "?")
            pct = m.get("percentage", "")
            detail = (m.get("detail") or {}).get("move_detail", {})
            attrs = []
            if detail.get("위력"):
                attrs.append(f"위력 {detail['위력']}")
            t = detail.get("타입")
            if t:
                attrs.append(TYPE_KO.get(t, t))
            dc = detail.get("분류")
            if dc:
                attrs.append(DAMAGE_CLASS_KO.get(dc, dc))
            if detail.get("명중률") and detail.get("명중률") != 100:
                attrs.append(f"명중 {detail['명중률']}")
            # 선공도/범위는 추측이 아니라 실데이터라 하드코딩 힌트보다 정확하다
            prio = detail.get("선공도")
            if isinstance(prio, int) and prio != 0:
                attrs.append(f"선공도 {prio:+d}")
            hint = move_role_hint(m.get("name_en", ""), detail, types)
            line = f"- **{ko}** ({pct})"
            if attrs:
                line += " [" + "/".join(attrs) + "]"
            if hint:
                line += f" — {hint}"
            sub = []
            if detail.get("효과"):
                sub.append(f"효과: {detail['효과']}")
            extra = []
            rng = detail.get("범위")
            if rng and rng != "상대 1마리":
                extra.append(f"범위: {rng}")
            if detail.get("플래그"):
                extra.append("속성: " + "·".join(detail["플래그"]))
            for k in ("풀죽음률", "흡수/반동", "연속타"):
                if detail.get(k):
                    extra.append(f"{k}: {detail[k]}")
            if extra:
                sub.append(" / ".join(extra))
            for s in sub:
                line += f"\n  - {s}"
            lines.append(line)
        lines.append("")

    # 메가진화 (있으면) — 종족값이 통째로 바뀌므로 팀빌딩에 결정적
    megas = p.get("megas") or []
    if megas:
        lines.append("## 메가진화")
        for mg in megas:
            mtypes = "/".join(labelize_types(mg.get("types") or []))
            ms = mg.get("base_stats") or {}
            delta = (mg.get("base_total") or 0) - (sum(p.get("base_stats", {}).values()) or 0)
            lines.append(f"- **{mg.get('name_ko')}** [{mtypes}] "
                         f"종족합 {mg.get('base_total')} ({delta:+d})")
            if ms:
                bs2 = labelize_base_stats(ms)
                lines.append("  - " + " / ".join(f"{k} {v}" for k, v in bs2.items()))
            for ab in mg.get("abilities") or []:
                eff = ab.get("effect")
                lines.append(f"  - 특성: **{ab.get('name_ko')}**"
                             + (f" — {eff}" if eff else ""))
        lines.append("")

    # 자주 같이 쓰이는 팀원
    teammates = usage.get("teammates", [])
    if teammates:
        lines.append("## 자주 같이 쓰이는 팀원")
        tm_strs = []
        for tm in teammates[:8]:
            ko = tm.get("name_ko") or tm.get("name_en", "?")
            tm_strs.append(ko)
        lines.append(", ".join(tm_strs))
        lines.append("")

    # 성격 / 노력치
    natures = usage.get("natures", [])
    if natures:
        lines.append("## 자주 쓰이는 성격")
        for n in natures[:3]:
            ko = n.get("name_ko") or n.get("name_en", "?")
            pct = n.get("percentage", "")
            sud = n.get("stat_up_down") or {}
            up = sud.get("up")
            down = sud.get("down")
            extra = f" ({up}↑/{down}↓)" if up and down else ""
            lines.append(f"- {ko} ({pct}){extra}")
        lines.append("")

    evs = usage.get("ev_spreads", [])
    if evs:
        lines.append("## 대표 노력치 배분")
        order = ["hp_points", "attack_points", "defense_points",
                 "sp_atk_points", "sp_def_points", "speed_points"]
        ko_order = ["HP", "공격", "방어", "특공", "특방", "스피드"]
        for ev in evs[:3]:
            pts = ev.get("ev_points", {})
            spread = "/".join(
                f"{ko_order[i]} {pts.get(f, 0)}"
                for i, f in enumerate(order) if pts.get(f)
            )
            pct = ev.get("percentage", "")
            lines.append(f"- {spread} ({pct})")
        lines.append("")

    # 약점/내성 (AI 가 시너지 판단에 사용)
    if types:
        lines.append("## 방어 타입 상성 (받는 데미지)")
        weak, resist, immune = [], [], []
        for atk in TYPE_KO:
            mult = type_multiplier(atk, *types)
            if mult >= 2.0:
                weak.append((TYPE_KO[atk], mult))
            elif 0 < mult < 1.0:
                resist.append((TYPE_KO[atk], mult))
            elif mult == 0.0:
                immune.append(TYPE_KO[atk])
        if weak:
            weak.sort(key=lambda x: -x[1])
            lines.append("- **약점**: " + ", ".join(
                f"{n}(x{m:g})" for n, m in weak))
        if resist:
            resist.sort(key=lambda x: x[1])
            lines.append("- **반감**: " + ", ".join(
                f"{n}(x{m:g})" for n, m in resist))
        if immune:
            lines.append("- **무효**: " + ", ".join(immune))
        lines.append("")

    # 도감 설명 (풍미용)
    if p.get("flavor_text_ko"):
        lines.append("## 도감 설명")
        lines.append(p["flavor_text_ko"])
        lines.append("")

    return sid, "\n".join(lines)


# ---------------------------------------------------------------------------
# 규칙 문서 생성
# ---------------------------------------------------------------------------
def build_rules_doc() -> str:
    lines = []
    lines.append("# 포켓몬 챔피언스 (Pokémon Champions) 배틀 규칙")
    lines.append("")
    lines.append("> 본 문서는 공식/권위 소스(champions.pokemon.com, Serebii, IGN, "
                 "VictoryRoad)에서 인용한 **챔피언스 실제 규칙**입니다. "
                 "메인라인 포켓몬과 다릅니다.")
    lines.append("")

    R = CHAMPIONS_RULES
    lines.append("## 게임 개요")
    lines.append(f"- {R['게임']}")
    lines.append(f"- 플랫폼: {R['플랫폼']}")
    lines.append(f"- 데이터 기준: {R['데이터_기준']}")
    lines.append("")

    lines.append("## 배틀 모드")
    for k, v in R["배틀_모드"].items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    lines.append("## 배틀 포맷")
    for k, v in R["배틀_포맷"].items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    lines.append("## 팀 구성 규칙 (공통)")
    for r in R["팀구성_규칙_공통"]:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("## 팀 구성 규칙 (Doubles / 공식 VGC)")
    for r in R["팀구성_규칙_Doubles"]:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("## 팀 구성 규칙 (Singles)")
    for r in R["팀구성_규칙_Singles"]:
        lines.append(f"- {r}")
    lines.append("")

    lines.append("## 육성 시스템 (IV/EV/VP)")
    for k, v in R["육성_시스템"].items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    # 메가진화
    M = MEGA_EVOLUTION
    lines.append("## 메가진화 (핵심 메커니즘)")
    lines.append(f"- {M['개요']}")
    lines.append("- **조건**:")
    for c in M["조건"]:
        lines.append(f"  - {c}")
    lines.append("- **효과**:")
    for e in M["효과"]:
        lines.append(f"  - {e}")
    lines.append("- **참고**:")
    for e in M["예외_및_참고"]:
        lines.append(f"  - {e}")
    lines.append("")

    # 상태이상
    lines.append("## 상태이상 변화 (시리즈와 다른 수치)")
    for key, info in STATUS_CONDITIONS.items():
        lines.append(f"- **{key}**:")
        for k, v in info.items():
            if k == "내용":
                lines.append(f"  - {v}")
            else:
                lines.append(f"  - {k}: {v}")
    lines.append("")

    # 기술 변화
    lines.append("## 주요 기술 변화")
    for k, v in MOVE_CHANGES.items():
        if isinstance(v, dict):
            lines.append(f"- **{k}**: {v.get('변경','')} — {v.get('의미','')}")
        else:
            lines.append(f"- {v}")
    lines.append("")

    return "\n".join(lines)


def build_type_chart_doc() -> str:
    """타입 상성 표 (공격춧ㄹ). AI 가 빠르게 참조 가능."""
    lines = []
    lines.append("# 타입 상성표 (공격 → 수비 배율)")
    lines.append("")
    lines.append("x2 = 효과 굉장 / x0.5 = 별로 / x0 = 무효. (시리즈 공통, 챔피언스도 동일)")
    lines.append("")

    # 공격 타입별 효과 목록 형태
    for atk in TYPE_KO:
        targets = []
        for defend, mult in TYPE_CHART.get(atk, {}).items():
            if mult != 1.0:
                targets.append((defend, mult))
        if not targets:
            continue
        targets.sort(key=lambda x: -x[1])
        parts = []
        for defend, mult in targets:
            tag = describe_type_effectiveness(mult).split("(")[0].strip()
            parts.append(f"{TYPE_KO[defend]}({mult:g}, {tag})")
        lines.append(f"- **{TYPE_KO[atk]}**({atk}): " + ", ".join(parts))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 메타 요약 문서 (자주 쓰이는 것들 랭킹)
# ---------------------------------------------------------------------------
def build_summary_doc(dataset: dict) -> str:
    lines = []
    lines.append("# 포켓몬 챔피언스 메타 요약 (실제 사용 데이터 기반)")
    lines.append("")
    lines.append(f"대상 포켓몬 수: {len(dataset.get('pokemon', []))}마리")
    lines.append("")

    moves = Counter()
    items = Counter()
    abilities = Counter()
    natures = Counter()
    for p in dataset.get("pokemon", []):
        u = p.get("usage", {})
        for x in u.get("moves", []):
            if x.get("name_en"):
                moves[x["name_en"]] += 1
        for x in u.get("held_items", []):
            if x.get("name_en"):
                items[x["name_en"]] += 1
        for x in u.get("abilities", []):
            if x.get("name_en"):
                abilities[x["name_en"]] += 1
        for x in u.get("natures", []):
            if x.get("name_en"):
                natures[x["name_en"]] += 1

    def top(title, counter, n=15):
        lines.append(f"## {title} (사용 포켓몬 수 기준)")
        for name, cnt in counter.most_common(n):
            lines.append(f"- {name}: {cnt}마리")
        lines.append("")

    top("자주 쓰이는 기술", moves)
    top("자주 쓰이는 지닌도구", items)
    top("자주 쓰이는 특성", abilities)
    top("자주 쓰이는 성격", natures)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 인덱스 (RAG/임베딩용 메타데이터)
# ---------------------------------------------------------------------------
def build_index(dataset: dict) -> dict:
    entries = []
    for p in dataset.get("pokemon", []):
        moves = p.get("usage", {}).get("moves", [])
        items = p.get("usage", {}).get("held_items", [])
        abils = p.get("usage", {}).get("abilities", [])
        entry = {
            "showdown_id": p["showdown_id"],
            "name_ko": p.get("pokemon_ko"),
            "name_en": p["pokemon_en"],
            "name_ja": p.get("pokemon_ja"),
            "pokedex_id": p.get("pokedex_id"),
            "types": p.get("types", []),
            "types_ko": labelize_types(p.get("types", [])),
            "base_total": sum(p.get("base_stats", {}).values()) if p.get("base_stats") else None,
            "doc_path": f"pokemon/{p['showdown_id']}.md",
            # 한국어 (기존 호환)
            "top_moves": [m.get("name_ko") for m in moves[:4]],
            "top_items": [i.get("name_ko") for i in items[:3]],
            "abilities": [a.get("name_ko") for a in abils[:2]],
            # 다언어
            "top_moves_en": [m.get("name_en") for m in moves[:4]],
            "top_moves_ja": [m.get("name_ja") for m in moves[:4]],
            "top_items_en": [i.get("name_en") for i in items[:3]],
            "top_items_ja": [i.get("name_ja") for i in items[:3]],
            "abilities_en": [a.get("name_en") for a in abils[:2]],
            "abilities_ja": [a.get("name_ja") for a in abils[:2]],
        }
        # 기존 필드는 그대로 두고 추가만 한다 (kb_search / team_builder 호환 유지)
        for k in ("pick_rank", "usage_total", "legal", "regulation_mb", "form"):
            if k in p:
                entry[k] = p[k]
        if p.get("megas"):
            entry["mega"] = [m.get("name_ko") for m in p["megas"]]
        entries.append(entry)

    # 검색 편의를 위해 여러 키로 정렬된 뷰도 제공
    by_name_ko = sorted(entries, key=lambda e: (e.get("name_ko") or ""))
    by_base = sorted(entries, key=lambda e: -(e["base_total"] or 0))

    return {
        "description": "포켓몬 챔피언스 AI 지식베이스 인덱스 (RAG/임베딩용)",
        "count": len(entries),
        "documents": {
            "rules": "rules.md",
            "type_chart": "type_chart.md",
            "summary": "summary.md",
        },
        "pokemon": entries,
        "by_name_ko": [e["showdown_id"] for e in by_name_ko],
        "by_base_total_desc": [e["showdown_id"] for e in by_base],
    }


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def build_kb(data_path: str, out_dir: str):
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    pkm_dir = os.path.join(out_dir, "pokemon")
    os.makedirs(pkm_dir, exist_ok=True)

    # 1) 규칙 문서
    rules = build_rules_doc()
    with open(os.path.join(out_dir, "rules.md"), "w", encoding="utf-8") as f:
        f.write(rules)
    print(f"[OK] rules.md ({len(rules)} 글자)")

    # 2) 타입 상성표
    tc = build_type_chart_doc()
    with open(os.path.join(out_dir, "type_chart.md"), "w", encoding="utf-8") as f:
        f.write(tc)
    print(f"[OK] type_chart.md")

    # 3) 포켓몬별 문서
    n = 0
    for p in dataset.get("pokemon", []):
        sid, doc = build_pokemon_doc(p)
        with open(os.path.join(pkm_dir, f"{sid}.md"), "w", encoding="utf-8") as f:
            f.write(doc)
        n += 1
    print(f"[OK] pokemon/*.md ({n} 마리)")

    # 4) 메타 요약
    summary = build_summary_doc(dataset)
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"[OK] summary.md")

    # 5) 인덱스
    index = build_index(dataset)
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"[OK] index.json ({index['count']} 항목)")

    print(f"\n완료 -> {out_dir}/")


def main():
    ap = argparse.ArgumentParser(description="포켓몬 챔피언스 AI 지식베이스 생성")
    ap.add_argument("--data", default="all_singles.json")
    ap.add_argument("--out", default="knowledge_base")
    args = ap.parse_args()
    build_kb(args.data, args.out)


if __name__ == "__main__":
    main()
