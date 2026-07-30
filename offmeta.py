# -*- coding: utf-8 -*-
"""비주류(오프메타) 포켓몬 발굴 CLI.

pkmnchamps 의 pick_rank(전체 사용률 순위)를 기준으로,
"순위는 낮지만 종족값·상성상 쓸 만한" 포켓몬을 찾는다.

데이터: data/pkmnchamps/  (pkmnchamps_source.py 로 생성)
  usage_<regulation>_<month>_<format>.json  — pick_rank, 기술/도구/특성/성격/EV 사용률
  pokemon.json                              — 종족값, 타입, regulationMA/MB

주의: usage 에는 같은 pokemon_id 가 폼별로 여러 번 나온다(로토무 6폼 등).
      따라서 키는 (pokemon_id, region_form, mega_form) 이다.

사용 예:
  python offmeta.py --list --min-rank 100          # 100위 밖 중 종족값 순
  python offmeta.py --list --min-rank 80 --type 물
  python offmeta.py --unused                      # 합법인데 사용률 0
  python offmeta.py --rank 화강돌                  # 특정 포켓몬 순위/세팅
  python offmeta.py --compare 한카리아스 화강돌      # 순위 비교
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Windows 기본 콘솔은 cp949 라서 '—' 같은 문자에서 죽고 한글도 깨진다. UTF-8 로 고정.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from i18n import L, type_names, validate_lang, TYPE_NAME

DATA_DIR = "data/pkmnchamps"
DEFAULT_USAGE_SINGLES = "usage_reg_mb_2026-07_singles.json"
DEFAULT_USAGE_DOUBLES = "usage_reg_mb_2026-07_doubles.json"
DEFAULT_USAGE = DEFAULT_USAGE_SINGLES
LANG = "ko"

KO_TYPE = {v: k for k, v in TYPE_NAME["ko"].items()}


def load(name: str):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


class Meta:
    def __init__(self, usage_file: str = DEFAULT_USAGE):
        self.usage = load(usage_file)
        self.pokemon = load("pokemon.json")
        self.moves = load("moves.json")
        self.items = load("items.json")
        self.abilities = load("abilities.json")
        self.by_id = {p["id"]: p for p in self.pokemon}
        self.usage_file = usage_file
        # 폼 포함 키
        self.ranked = {}
        for r in self.usage:
            key = (r["pokemon_id"], r.get("region_form") or "", r.get("mega_form") or "")
            self.ranked[key] = r

    # -- helpers ----------------------------------------------------------
    def types_disp(self, p: dict) -> str:
        return "/".join(type_names(LANG, p.get("types") or []))

    def bst(self, p: dict) -> int:
        return sum((p.get("stats") or {}).values())

    def label(self, r: dict) -> str:
        """현재 언어의 포켓몬명 + 폼 접미사. 영/일은 pokemon.json 에서 보완."""
        name = r["pokemon_name_ko"]
        if LANG in ("en", "ja"):
            p = self.by_id.get(r["pokemon_id"]) or {}
            key = "nameEn" if LANG == "en" else "nameJa"
            name = p.get(key) or name
        extra = [x for x in (r.get("region_form"), r.get("mega_form")) if x]
        return "%s%s" % (name, " (%s)" % "/".join(extra) if extra else "")

    def top(self, r: dict, field: str, db: dict, n: int = 4) -> str:
        rows = [x for x in (r.get(field) or []) if (x.get("usage") or 0) > 0][:n]
        out = []
        for x in rows:
            ko = (db.get(x["name"]) or {}).get("nameKo", x["name"])
            out.append("%s %.0f%%" % (ko, x["usage"]))
        return ", ".join(out) if out else "-"

    # -- commands ---------------------------------------------------------
    def cmd_list(self, min_rank: int, min_bst: int, type_ko: str | None, limit: int) -> None:
        want = KO_TYPE.get(type_ko) if type_ko else None
        rows = []
        for (pid, rf, mf), r in self.ranked.items():
            if r["pick_rank"] < min_rank:
                continue
            p = self.by_id.get(pid)
            if not p or not p.get("regulationMB"):
                continue
            b = self.bst(p)
            if b < min_bst:
                continue
            if want and want not in (p.get("types") or []):
                continue
            rows.append((b, r, p))
        rows.sort(key=lambda x: -x[0])
        print("=== %s (%s) ===" % (L(LANG, "offmeta_candidates"), self.usage_file))
        print("조건: %d위 밖 / 종족합 %d 이상%s / M-B 합법  ->  %d마리\n"
              % (min_rank, min_bst, " / %s타입" % type_ko if type_ko else "", len(rows)))
        for b, r, p in rows[:limit]:
            st = p["stats"]
            print("#%-4d %-16s %-14s 종족합%-4d  (HP%d 공%d 방%d 특공%d 특방%d 속%d)"
                  % (r["pick_rank"], self.label(r), self.types_disp(p), b,
                     st["hp"], st["atk"], st["def"], st["spa"], st["spd"], st["spe"]))
            print("      특성: %s" % self.top(r, "abilities", self.abilities, 2))
            print("      기술: %s" % self.top(r, "moves", self.moves, 5))
            print("      도구: %s" % self.top(r, "items", self.items, 3))

    def cmd_unused(self) -> None:
        used = {pid for pid, _, _ in self.ranked}
        rows = [p for p in self.pokemon if p.get("regulationMB") and p["id"] not in used]
        rows.sort(key=lambda p: -self.bst(p))
        print("=== %s — %d마리 ===" % (L(LANG, "legal_unused"), len(rows)))
        for p in rows:
            st = p["stats"]
            print("  #%04d %-12s %-14s 종족합%-4d (HP%d 공%d 방%d 특공%d 특방%d 속%d)"
                  % (p["id"], p["nameKo"], self.types_disp(p), self.bst(p),
                     st["hp"], st["atk"], st["def"], st["spa"], st["spd"], st["spe"]))

    def cmd_rank(self, name: str) -> None:
        hits = [(k, r) for k, r in self.ranked.items() if name in r["pokemon_name_ko"]]
        if not hits:
            print("'%s' 사용률 데이터에 없음." % name)
            legal = [p for p in self.pokemon if name in p["nameKo"]]
            for p in legal:
                print("  참고: %s M-B합법=%s M-A합법=%s 종족합%d"
                      % (p["nameKo"], p.get("regulationMB"), p.get("regulationMA"), self.bst(p)))
            return
        total = len(self.ranked)
        for (pid, rf, mf), r in sorted(hits, key=lambda x: x[1]["pick_rank"]):
            p = self.by_id.get(pid) or {}
            st = p.get("stats") or {}
            pct = 100.0 * r["pick_rank"] / total
            print("=== %s ===" % self.label(r))
            print("  사용률 순위: %d / %d  (상위 %.0f%%)" % (r["pick_rank"], total, pct))
            print("  타입: %s | 종족합 %d (HP%s 공%s 방%s 특공%s 특방%s 속%s)"
                  % (self.types_disp(p), self.bst(p), st.get("hp"), st.get("atk"),
                     st.get("def"), st.get("spa"), st.get("spd"), st.get("spe")))
            print("  M-B 합법: %s" % p.get("regulationMB"))
            print("  특성: %s" % self.top(r, "abilities", self.abilities, 3))
            print("  기술: %s" % self.top(r, "moves", self.moves, 8))
            print("  도구: %s" % self.top(r, "items", self.items, 5))
            nat = [x for x in (r.get("natures") or []) if (x.get("usage") or 0) > 0][:3]
            print("  성격: %s" % ", ".join("%s %.0f%%" % (x["name"], x["usage"]) for x in nat))
            sp = (r.get("spreads") or [])[:3]
            for x in sp:
                s = x["sps"]
                print("  EV: %d/%d/%d/%d/%d/%d (합%d) %.1f%%"
                      % (s["hp"], s["atk"], s["def"], s["spa"], s["spd"], s["spe"],
                         sum(s.values()), x["usage"]))
            tm = [t["name_ko"] for t in (r.get("teammates") or [])[:8]]
            print("  자주 같이 쓰임: %s" % (", ".join(tm) or "-"))

    def cmd_compare(self, names: list[str]) -> None:
        total = len(self.ranked)
        print("=== 사용률 비교 (%d마리 중) ===" % total)
        for n in names:
            hits = [r for r in self.ranked.values() if n in r["pokemon_name_ko"]]
            if not hits:
                print("  %-14s 데이터 없음" % n)
                continue
            r = min(hits, key=lambda x: x["pick_rank"])
            p = self.by_id.get(r["pokemon_id"]) or {}
            print("  %-16s #%-4d  %-14s 종족합%d"
                  % (self.label(r), r["pick_rank"], self.types_disp(p), self.bst(p)))


def main() -> None:
    ap = argparse.ArgumentParser(description="비주류 포켓몬 발굴")
    ap.add_argument("--usage", default=None, help="사용률 파일명 (생략 시 --format 기준 자동)")
    ap.add_argument("--format", default="singles", choices=["singles", "doubles"],
                    help="싱글(기본) / 더블")
    ap.add_argument("--lang", default="ko", choices=["ko", "en", "ja"], help="출력 언어")
    ap.add_argument("--list", action="store_true", help="비주류 후보 목록")
    ap.add_argument("--unused", action="store_true", help="합법이지만 사용률 데이터 없음")
    ap.add_argument("--rank", metavar="이름", help="특정 포켓몬 순위/세팅")
    ap.add_argument("--compare", nargs="+", metavar="이름", help="여러 마리 순위 비교")
    ap.add_argument("--min-rank", type=int, default=100)
    ap.add_argument("--min-bst", type=int, default=480)
    ap.add_argument("--type", dest="type_ko", help="타입 필터 (한글)")
    ap.add_argument("--limit", type=int, default=25)
    a = ap.parse_args()

    global LANG
    LANG = validate_lang(a.lang)

    usage = a.usage or (DEFAULT_USAGE_DOUBLES if a.format == "doubles" else DEFAULT_USAGE_SINGLES)
    m = Meta(usage)
    if a.rank:
        m.cmd_rank(a.rank)
    elif a.compare:
        m.cmd_compare(a.compare)
    elif a.unused:
        m.cmd_unused()
    else:
        m.cmd_list(a.min_rank, a.min_bst, a.type_ko, a.limit)


if __name__ == "__main__":
    main()
