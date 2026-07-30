# -*- coding: utf-8 -*-
"""pkmnchamps 가이드 i18n -> knowledge_base/guides/*.md 마크다운 생성.

가이드 본문(설명·수치)은 i18n 키맵에 있지만,
사이트에서 함께 보이는 "세터 포켓몬 / 대표 포켓몬" 목록은 i18n 이 아니라
포켓몬 DB 를 런타임에 필터해서 만든다. 그래서 그 부분은 여기서 직접 계산해 붙인다.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re

DATA_DIR = "data/pkmnchamps"
OUT_DIR = "knowledge_base/guides"

TYPE_KO = {
    "normal": "노말", "fire": "불꽃", "water": "물", "electric": "전기",
    "grass": "풀", "ice": "얼음", "fighting": "격투", "poison": "독",
    "ground": "땅", "flying": "비행", "psychic": "에스퍼", "bug": "벌레",
    "rock": "바위", "ghost": "고스트", "dragon": "드래곤", "dark": "악",
    "steel": "강철", "fairy": "페어리",
}

# 가이드 slug -> (제목 fallback, 카테고리)
CATEGORY = {
    "weather": "필드·날씨",
    "terrain": "필드·날씨",
    "ability": "포켓몬 요소",
    "type": "포켓몬 요소",
    "status": "배틀 계산",
    "stats": "배틀 계산",
    "accuracy": "배틀 계산",
}

# 날씨/필드 가이드에 붙일 세터 특성 (사이트가 계산해서 보여주는 부분)
WEATHER_SETTERS = {
    "sun": ["drought", "orichalcum-pulse"],
    "rain": ["drizzle", "primordial-sea"],
    "sand": ["sand-stream", "sand-spit"],
    "snow": ["snow-warning"],
}
TERRAIN_SETTERS = {
    "electric": ["electric-surge", "hadron-engine"],
    "grassy": ["grassy-surge"],
    "misty": ["misty-surge"],
    "psychic": ["psychic-surge"],
}


def load(name: str):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def group_keys(i18n: dict[str, str]) -> dict[str, dict]:
    """guide.<slug>.<rest> 를 slug 별로 모으고, rest 를 다시 섹션별로 묶는다."""
    out: dict[str, dict] = {}
    for k, v in i18n.items():
        parts = k.split(".")
        if len(parts) < 3:
            continue
        slug = parts[1]
        rest = parts[2:]
        g = out.setdefault(slug, {"page": {}, "sections": collections.OrderedDict()})
        if len(rest) == 1:
            g["page"][rest[0]] = v
        else:
            sec = g["sections"].setdefault(rest[0], collections.OrderedDict())
            sec[".".join(rest[1:])] = v
    return out


def _sorted_eff(sec: dict[str, str]) -> list[tuple[str, str]]:
    """eff1, eff2 ... 를 숫자 순서로. 그 외 키는 뒤에 알파벳 순."""
    def key(kv):
        k = kv[0]
        m = re.fullmatch(r"([a-zA-Z]+)(\d+)", k)
        if m:
            return (0, m.group(1), int(m.group(2)))
        return (1, k, 0)
    return sorted(sec.items(), key=key)


def setter_lines(ability_slugs: list[str], pokemon: list[dict],
                 abilities: dict[str, dict], reg_key: str = "regulationMB") -> list[str]:
    """해당 특성을 가진 합법 포켓몬을 찾아 한 줄씩."""
    lines = []
    for ab in ability_slugs:
        hit = [p["nameKo"] for p in pokemon
               if p.get(reg_key) and any(a.get("name") == ab for a in p.get("abilities") or [])]
        if not hit:
            continue
        ab_ko = (abilities.get(ab) or {}).get("nameKo", ab)
        lines.append("- **%s** (%s): %s" % (ab_ko, ab, ", ".join(sorted(hit))))
    return lines


def build_guide(slug: str, g: dict, pokemon: list[dict], abilities: dict) -> str:
    page = g["page"]
    title = page.get("pageTitle", slug)
    L = ["# %s" % title, ""]
    if CATEGORY.get(slug):
        L += ["> 분류: %s · 출처: pkmnchamps.com/guide/%s" % (CATEGORY[slug], slug), ""]
    if page.get("intro"):
        L += [page["intro"], ""]
    for k in ("duration", "clickHint"):
        if page.get(k):
            L += ["- %s" % page[k], ""]

    # 페이지 공통 라벨은 용어 사전처럼 남긴다 (AI 가 표현을 맞출 수 있게)
    labels = {k: v for k, v in page.items()
              if k not in ("pageTitle", "intro", "duration", "clickHint")}

    setters_map = WEATHER_SETTERS if slug == "weather" else (
        TERRAIN_SETTERS if slug == "terrain" else {})

    for sec_name, sec in g["sections"].items():
        # 타입 가이드는 섹션 이름이 i18n 에 없고 타입 슬러그라서 한글로 바꿔준다
        head = sec.get("name") or TYPE_KO.get(sec_name) or sec_name
        L.append("## %s" % head)
        L.append("")
        if sec.get("desc"):
            L += [sec["desc"], ""]
        body = [(k, v) for k, v in _sorted_eff(sec) if k not in ("name", "desc")]
        if body:
            for k, v in body:
                L.append("- %s" % v if re.fullmatch(r"[a-zA-Z]+\d*", k) else "- **%s**: %s" % (k, v))
            L.append("")
        if sec_name in setters_map:
            sl = setter_lines(setters_map[sec_name], pokemon, abilities)
            if sl:
                L.append("### 세터 (M-B 합법, 특성 보유)")
                L += sl + [""]

    if labels:
        L.append("## 화면 라벨 (용어)")
        L.append("")
        for k, v in sorted(labels.items()):
            L.append("- `%s` = %s" % (k, v))
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# 상태이상 가이드는 i18n 에 라벨만 있다 (본문은 사이트가 DB 로 계산해서 그림).
# 그래서 여기서 기술 DB + 도구 DB + battle_rules 로 직접 만든다.
# ---------------------------------------------------------------------------
MAIN_AILMENTS = ["독", "맹독", "화상", "마비", "잠듦", "얼음"]

# 면역 타입 — 시리즈 표준. 챔피언스에서 별도 변경 고지가 없어 그대로 본다.
AILMENT_IMMUNE = {
    "독": ["독", "강철"], "맹독": ["독", "강철"], "화상": ["불꽃"],
    "마비": ["전기"], "얼음": ["얼음"], "잠듦": [],
}
# battle_rules.STATUS_CONDITIONS 키 매칭
RULE_KEY = {
    "마비": "마비_Paralysis", "잠듦": "수면_Sleep", "얼음": "빙결_Freeze",
    "화상": "화상_Burn", "독": "독_Poison", "맹독": "독_Poison",
    "혼란": "혼란_Confusion",
}


def _inflicting_moves(moves: dict, ailment: str) -> list[dict]:
    out = []
    for slug, m in moves.items():
        if not m.get("available"):
            continue
        meta = m.get("meta") or {}
        if meta.get("ailmentKo") != ailment:
            continue
        out.append({
            "ko": m.get("nameKo", slug), "power": m.get("power"),
            "acc": m.get("accuracy"), "type": m.get("type"),
            "cls": m.get("damageClassKo"),
            "chance": meta.get("ailmentChance") or m.get("effectChance"),
        })
    # 확률 높은 순 -> 위력 순
    out.sort(key=lambda x: (-(x["chance"] or 0), -(x["power"] or 0)))
    return out


def _cure_items(items: dict) -> list[tuple[str, str]]:
    """'<상태이상>을/를 회복한다' 형태만 잡는다.

    단순 키워드 매칭이면 검은진흙("독타입의 포켓몬은 HP를 회복한다") 같은
    HP 회복 도구가 섞여 들어온다.
    """
    pat = re.compile(r"(모든 상태\s?이상|마비|화상|잠듦|얼음|독|혼란)(을|를)\s*(회복|치료)")
    out = []
    for v in items.values():
        eff = v.get("effectKo") or ""
        if pat.search(eff):
            out.append((v.get("nameKo"), eff))
    return sorted(set(out))


def build_status_guide(g: dict, moves: dict, items: dict) -> str:
    try:
        from battle_rules import STATUS_CONDITIONS
    except Exception:
        STATUS_CONDITIONS = {}

    page = g["page"]
    L = ["# %s" % page.get("pageTitle", "상태이상 가이드"), "",
         "> 분류: 배틀 계산 · 출처: pkmnchamps.com/guide/status "
         "(부여 기술·도구 목록은 기술/도구 DB 에서 계산)", ""]
    if page.get("intro"):
        L += [page["intro"], ""]

    by_ailment = {}
    for m in moves.values():
        if m.get("available"):
            a = (m.get("meta") or {}).get("ailmentKo")
            if a and a != "없음":
                by_ailment.setdefault(a, 0)
                by_ailment[a] += 1

    L += ["## 주 상태이상", ""]
    for a in MAIN_AILMENTS:
        rows = _inflicting_moves(moves, a)
        L.append("### %s" % a)
        L.append("")
        rk = RULE_KEY.get(a)
        info = STATUS_CONDITIONS.get(rk) if rk else None
        if info:
            L.append("**챔피언스 수치** (시리즈와 다를 수 있음)")
            for k, v in info.items():
                L.append("- %s: %s" % (k.replace("_", " "), v))
            L.append("")
        imm = AILMENT_IMMUNE.get(a)
        L.append("- 면역 타입: %s" % (", ".join(imm) if imm else "없음 (특성으로만 방어)"))
        L.append("- 부여 기술: %d개" % len(rows))
        L.append("")
        if rows:
            L.append("| 기술 | 위력 | 명중 | 분류 | 부여 확률 |")
            L.append("|---|---|---|---|---|")
            for r in rows[:14]:
                L.append("| %s | %s | %s | %s | %s |" % (
                    r["ko"], r["power"] or "-", r["acc"] or "-",
                    r["cls"] or "-", ("%d%%" % r["chance"]) if r["chance"] else "-"))
            L.append("")

    L += ["## 부 상태이상 (교체로 해제)", ""]
    if page.get("volatileNote.desc") or g["sections"].get("volatileNote"):
        note = (g["sections"].get("volatileNote") or {}).get("desc")
        if note:
            L += [note, ""]
    others = sorted((a for a in by_ailment if a not in MAIN_AILMENTS and a != "알 수 없음"),
                    key=lambda a: -by_ailment[a])
    for a in others:
        rows = _inflicting_moves(moves, a)
        names = ", ".join("%s(%s%%)" % (r["ko"], r["chance"]) if r["chance"] else r["ko"]
                          for r in rows[:8])
        L.append("- **%s** — 부여 기술 %d개: %s" % (a, len(rows), names))
    L.append("")

    ci = _cure_items(items)
    if ci:
        L += ["## 치료 도구", ""]
        for n, e in ci:
            L.append("- **%s** — %s" % (n, e))
        L.append("")

    labels = {k: v for k, v in page.items() if k not in ("pageTitle", "intro")}
    if labels:
        L += ["## 화면 라벨 (용어)", ""]
        L += ["- `%s` = %s" % (k, v) for k, v in sorted(labels.items())]
        L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="pkmnchamps 가이드 마크다운 생성")
    ap.add_argument("--out", default=OUT_DIR)
    a = ap.parse_args()

    i18n = load("guide_i18n.json")
    pokemon = load("pokemon.json")
    abilities = load("abilities.json")
    moves = load("moves.json")
    items = load("items.json")
    groups = group_keys(i18n)

    os.makedirs(a.out, exist_ok=True)
    index = []
    for slug, g in sorted(groups.items()):
        if slug == "list":  # 가이드 목록 페이지 라벨 — 문서 아님
            continue
        if slug == "status":
            md = build_status_guide(g, moves, items)
        else:
            md = build_guide(slug, g, pokemon, abilities)
        p = os.path.join(a.out, slug + ".md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(md)
        title = g["page"].get("pageTitle", slug)
        index.append({"slug": slug, "title": title,
                      "category": CATEGORY.get(slug, ""),
                      "path": "guides/%s.md" % slug,
                      "chars": len(md),
                      "sections": [s.get("name") or n for n, s in g["sections"].items()]})
        print("  [OK] %-10s %-22s %5d자  섹션 %d" % (
            slug, title, len(md), len(g["sections"])))

    with open(os.path.join(a.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"count": len(index), "guides": index}, f, ensure_ascii=False, indent=1)
    print("\n완료 -> %s (가이드 %d종)" % (a.out, len(index)))


if __name__ == "__main__":
    main()
