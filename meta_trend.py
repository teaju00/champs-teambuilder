# -*- coding: utf-8 -*-
"""메타 트렌드 분석 — 다월 usage 비교.

사용률 파일(pick_rank)의 월별 변동을 비교해 "이번 시즌 뜨는/지는 포켓몬" 을 찾는다.
같은 레귀레이션(reg_mb / reg_m1) 내에서 월별로 비교한다.

사용:
  python meta_trend.py                        # 현행 레귀(M-B) 싱글 순위 변동
  python meta_trend.py --rising               # 상승 Top 10
  python meta_trend.py --falling              # 하락 Top 10
  python meta_trend.py --pokemon 한카리아스    # 특정 포켓몬 세팅 변화
  python meta_trend.py --regulation m1        # 구 레귀(M1)
  python meta_trend.py --format doubles       # 더블
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from i18n import L, validate_lang

DATA_DIR = "data/pkmnchamps"
LANG = "ko"


def load_usage(path: str) -> dict:
    """usage 파일 -> {key(한글명+폼): row}."""
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    out = {}
    for r in rows:
        key = (r.get("pokemon_name_ko") or "", r.get("region_form") or "")
        out[key] = r
    return out


def month_of(path: str) -> str:
    """usage 파일명 -> 'YYYY-MM'."""
    m = re.search(r"(\d{4}-\d{2})", path)
    return m.group(1) if m else os.path.basename(path)


def find_files(regulation: str, fmt: str) -> list[str]:
    """해당 레귀·포맷의 usage 파일을 월순 정렬."""
    if regulation == "mb":
        pattern = os.path.join(DATA_DIR, "usage_reg_mb_*_%s.json" % fmt)
    elif regulation == "m1":
        pattern = os.path.join(DATA_DIR, "usage_reg_m1_*_%s.json" % fmt)
    else:
        pattern = os.path.join(DATA_DIR, "usage_showdown-*regulation_ma_*_%s.json" % fmt)
    files = sorted(f for f in glob.glob(pattern) if "index" not in f)
    return files


def cmd_trend(regulation: str, fmt: str, top: int, mode: str) -> None:
    files = find_files(regulation, fmt)
    if len(files) < 2:
        print("비교할 월별 파일이 부족합니다 (%d개). 최소 2개월 필요." % len(files))
        print("대상:", [os.path.basename(f) for f in files])
        return

    # 첫 달과 마지막 달 비교
    first = load_usage(files[0])
    last = load_usage(files[-1])
    m0, m1 = month_of(files[0]), month_of(files[-1])

    changes = []
    for key, r_last in last.items():
        r_first = first.get(key)
        rank_first = r_first["pick_rank"] if r_first else None
        rank_last = r_last["pick_rank"]
        total = len(last)
        # rank_first None = 이번에 새로 진입. 작을수록 좋으니 "상승" 으로 취급
        changes.append((key, rank_first, rank_last, total))

    # 변화량 계산 (순위 상승 = 음수, 하락 = 양수)
    def delta(c):
        key, rf, rl, _ = c
        if rf is None:
            return -rl  # 새 진입: 큰 상승
        if rl is None:
            return rf   # 빠짐
        return rl - rf  # 순위 하락 = 양수

    title_map = {"all": L(LANG, "rank_change"), "rising": L(LANG, "rising_top"),
                 "falling": L(LANG, "falling_top")}
    print("=== %s: %s [%s] %s → %s ===" %
          (L(LANG, "meta_trend"), "%s/%s" % (regulation.upper(), fmt), title_map[mode], m0, m1))
    print()

    if mode == "rising":
        changes.sort(key=delta)
        sel = changes[:top]
        print("**%s %d** (%s):" % (L(LANG, "rising_top"), len(sel), L(LANG, "delta_neg")))
    elif mode == "falling":
        changes.sort(key=delta, reverse=True)
        sel = changes[:top]
        print("**%s %d** (%s):" % (L(LANG, "falling_top"), len(sel), L(LANG, "delta_pos")))
    else:
        # 변화 절댓값 큰 순
        changes.sort(key=lambda c: abs(delta(c)), reverse=True)
        sel = changes[:top]
        print("**%s %d**:" % (L(LANG, "rank_change"), len(sel)))

    for key, rf, rl, total in sel:
        name, form = key
        label = name + (" (%s)" % form if form else "")
        d = delta((key, rf, rl, total))
        rf_s = "%d" % rf if rf else "新"
        rl_s = "%d" % rl if rl else "빠짐"
        arrow = "▲" if d < 0 else ("▼" if d > 0 else "=")
        print("  %-18s %s위 → %s위  %s%d" % (label, rf_s, rl_s, arrow, abs(d) if d else 0))


def cmd_pokemon(name: str, regulation: str, fmt: str) -> None:
    files = find_files(regulation, fmt)
    if not files:
        print("파일 없음")
        return
    print("=== %s 월별 변화 [%s/%s] ===" % (name, regulation.upper(), fmt))
    print()
    for f in files:
        rows = load_usage(f)
        hits = [(k, r) for k, r in rows.items() if name in k[0]]
        m = month_of(f)
        if not hits:
            print("  %s: 데이터 없음" % m)
            continue
        for (pname, form), r in sorted(hits, key=lambda x: x[1]["pick_rank"]):
            label = pname + (" (%s)" % form if form else "")
            total = len(rows)
            print("  %s  %-18s  #%-4d / %d" % (m, label, r["pick_rank"], total))
            # 상위 기술/도구/성격
            nat = [n["name"] for n in (r.get("natures") or [])[:2] if (n.get("usage") or 0) > 0]
            moves = [mv["name"] for mv in (r.get("moves") or [])[:4] if (mv.get("usage") or 0) > 0]
            if nat:
                print("         성격: %s" % ", ".join(nat))
            if moves:
                print("         기술: %s" % ", ".join(moves))


def main() -> None:
    ap = argparse.ArgumentParser(description="메타 트렌드 분석")
    ap.add_argument("--regulation", default="mb", choices=["mb", "m1", "ma"],
                    help="레귤레이션 (mb=현행 M-B, m1=이전, ma=Showdown M-A)")
    ap.add_argument("--format", default="singles", choices=["singles", "doubles"])
    ap.add_argument("--lang", default="ko", choices=["ko", "en", "ja"], help="출력 언어")
    ap.add_argument("--rising", action="store_true", help="순위 상승 Top")
    ap.add_argument("--falling", action="store_true", help="순위 하락 Top")
    ap.add_argument("--pokemon", metavar="이름", help="특정 포켓몬 월별 변화")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()

    global LANG
    LANG = validate_lang(a.lang)

    if a.pokemon:
        cmd_pokemon(a.pokemon, a.regulation, a.format)
    elif a.rising:
        cmd_trend(a.regulation, a.format, a.top, "rising")
    elif a.falling:
        cmd_trend(a.regulation, a.format, a.top, "falling")
    else:
        cmd_trend(a.regulation, a.format, a.top, "all")


if __name__ == "__main__":
    main()
