# -*- coding: utf-8 -*-
"""팀 평가 스코어 (0~100).

validate_team 의 Warn 을 정량 점수로 승격. 항목별 점수를 매겨 팀의 강점·약점을
한눈에 보여준다. 점수는 절대적 기준이 아니라 팀 설계 의도(트릭룸/스톨/고속 등)와
얼마나 일관되는지를 평가한다.

사용:
  python team_score.py 팀/보유_트릭룸.json
  python team_score.py 팀/보유_트릭룸.json --format doubles

평가 항목 (합 100):
  방어 커버리지  35  — 약점 중복/4배 약점 페널티, 내성 보너스
  속도 컨트롤    20  — 트릭룸 팀=저속 정렬, 일반=속도 분포·선공기
  시너지         20  — 타입 보완, 메가 슬롯, 페어 구조
  아키타입 일관   15  — 성격/SP 가 역할에 부합 (validate_team check_archetype 재사용)
  화력/내구 밸런스 10  — 공격 투자 vs 방어 투자 균형
"""

from __future__ import annotations

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from battle_rules import type_multiplier, TYPE_KO, real_stat, nature_up_down
from i18n import L, type_name, validate_lang

DATASET = "champs_singles.json"
STAT_ORDER = ["hp", "atk", "def", "spa", "spd", "spe"]
BASE_KEY = {"hp": "hp", "attack": "atk", "defense": "def",
            "special-attack": "spa", "special-defense": "spd", "speed": "spe"}
LANG = "ko"


def _p_name(p: dict) -> str:
    """데이터셋 엔트리에서 현재 언어 포켓몬명."""
    if LANG == "en":
        return p.get("pokemon_en") or p.get("pokemon_ko", "?")
    if LANG == "ja":
        return p.get("pokemon_ja") or p.get("pokemon_ko", "?")
    return p.get("pokemon_ko", "?")


def nature_mod(stat: str, nature_ko: str | None) -> float:
    return nature_up_down(stat, nature_ko)


def load_dataset(path: str = DATASET) -> dict[str, dict]:
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for p in json.load(f).get("pokemon", []):
            out[p["pokemon_ko"]] = p
    return out


def speed_of(slot: dict, p: dict) -> int:
    base = p.get("base_stats", {}).get("speed", 0)
    sp = slot.get("sp", {}).get("spe", 0)
    return real_stat(base, sp, nature=nature_mod("spe", slot.get("nature")))


# ---------------------------------------------------------------------------
# 항목별 채점
# ---------------------------------------------------------------------------
def score_defense(team: list[dict], ds: dict[str, dict]) -> tuple[float, list[str]]:
    """방어 커버리지 (35점 만점)."""
    pts = 35.0
    notes = []
    types_list = []
    for slot in team:
        p = ds.get(slot.get("name", ""), {})
        if p.get("types"):
            types_list.append(tuple(p["types"]))

    if not types_list:
        return 0.0, ["타입 데이터 없음"]

    # 약점 중복: 같은 타입에 약한 팀원이 많을수록 페널티
    for atk in TYPE_KO:
        exposed = sum(1 for ts in types_list if type_multiplier(atk, *ts) >= 2.0)
        quad = sum(1 for ts in types_list if type_multiplier(atk, *ts) >= 4.0)
        if exposed >= 3:
            pts -= 3.0 * (exposed - 2)
            notes.append("%s 약점 %d마리 겹침 (-%.0f)" % (TYPE_KO[atk], exposed, 3.0 * (exposed - 2)))
        if quad:
            pts -= 4.0 * quad
            notes.append("%s 4배 약점 %d마리 (-%.0f)" % (TYPE_KO[atk], quad, 4.0 * quad))

    # 내성 보너스: 여러 팀원이 같은 타입을 반감/무효화하면 보너스
    for atk in TYPE_KO:
        resist = sum(1 for ts in types_list if 0 < type_multiplier(atk, *ts) < 1.0)
        if resist >= 3:
            pts += 1.5
            notes.append("%s %d마리가 내성 (+1.5)" % (TYPE_KO[atk], resist))

    return max(0.0, min(35.0, pts)), notes


def score_speed(team: list[dict], ds: dict[str, dict]) -> tuple[float, list[str]]:
    """속도 컨트롤 (20점 만점).

    트릭룸 팀(평균 속도 낮음 + 트릭룸 기술 보유)은 저속 정렬에 보너스.
    일반 팀은 속도 분포(너무 다 같으면 X) + 선공기 보유로 평가.
    """
    notes = []
    speeds = []
    has_trickroom = False
    has_priority = False
    priority_moves = {"불릿펀치", "속임수", "진공표범집", "신속", "얼음숟가락",
                      "물총기술", "그림자훔치기", "기합의끈", "광속권"}

    for slot in team:
        p = ds.get(slot.get("name", ""), {})
        speeds.append(speed_of(slot, p))
        moves = set(slot.get("moves", []))
        if "트릭룸" in moves:
            has_trickroom = True
        if moves & priority_moves:
            has_priority = True

    avg = sum(speeds) / len(speeds) if speeds else 0
    pts = 12.0  # 기본

    if has_trickroom:
        # 트릭룸 팀: 평균 속도가 낮을수록(역전 효율) 좋음
        if avg <= 70:
            pts += 8.0
            notes.append("트릭룸 팀 + 평균속도 %d (저속 정렬, +8)" % avg)
        else:
            pts += 4.0
            notes.append("트릭룸 보유지만 평균속도 %d 로 다소 빠름 (+4)" % avg)
    else:
        # 일반 팀: 속도 분포 + 선공기
        if has_priority:
            pts += 4.0
            notes.append("선공기 보유 (+4)")
        # 속도 분포 (넓을수록 다양한 매치업 대응)
        sp_range = max(speeds) - min(speeds) if speeds else 0
        if sp_range >= 80:
            pts += 4.0
            notes.append("속도 분산 %d (다양한 스피드대, +4)" % sp_range)
        elif sp_range <= 20:
            pts -= 2.0
            notes.append("속도가 전부 비슷 (%d~%d, -2)" % (min(speeds), max(speeds)))

    return max(0.0, min(20.0, pts)), notes


def score_synergy(team: list[dict], ds: dict[str, dict]) -> tuple[float, list[str]]:
    """시너지 (20점 만점). 타입 보완 + 메가 슬롯 + 페어 구조."""
    notes = []
    pts = 20.0

    # 종족 조항 위반 (같은 도감번호) 감지. pokedex_id 가 None(데이터 누락)이면 건너뛴다.
    seen_dex = {}
    for slot in team:
        p = ds.get(slot.get("name", ""), {})
        dex = p.get("pokedex_id")
        if dex is None:
            continue
        if dex in seen_dex:
            pts -= 5.0
            notes.append("종족 조항 위반 의심: %s/%s 같은 도감번호 (-5)" % (seen_dex[dex], _p_name(p)))
        else:
            seen_dex[dex] = slot["name"]

    # 메가스톤 다수 보유 페널티 (선발에 2개 이상은 비효율)
    stones = [s for s in team if "나이트" in (s.get("item") or "")]
    if len(stones) >= 3:
        pts -= 3.0
        notes.append("메가스톤 %d개 — 선발 3~4마리에 비효율 (-3)" % len(stones))

    # 도구 다양성 (같은 도구 반복은 구조 단조)
    items = [s.get("item") for s in team if s.get("item")]
    if items and len(set(items)) < len(items) - 1:
        pts -= 2.0
        notes.append("도구 중복 (-2)")

    # 타입 다양성 (같은 타입 조합 반복 회피). 타입이 있는 포켓몬만 센다.
    type_combos = []
    for slot in team:
        p = ds.get(slot.get("name", ""), {})
        if p.get("types"):
            type_combos.append(tuple(sorted(p["types"])))
    if len(type_combos) >= 2 and len(set(type_combos)) < len(type_combos) - 1:
        pts -= 3.0
        notes.append("같은 타입 조합 반복 (-3)")

    return max(0.0, min(20.0, pts)), notes


def score_archetype(team: list[dict], ds: dict[str, dict]) -> tuple[float, list[str]]:
    """아키타입 일관성 (15점 만점). validate_team check_archetype 로직 재사용."""
    notes = []
    pts = 15.0
    for slot in team:
        name = slot.get("name", "?")
        sp = slot.get("sp", {})
        p = ds.get(name, {})
        meta = {}
        for sp_row in p.get("usage", {}).get("ev_spreads", [])[:1]:
            meta = sp_row.get("ev_points", {})
        if not sp or not meta:
            continue
        m_atk = (meta.get("attack_points", 0) or 0) + (meta.get("sp_atk_points", 0) or 0)
        my_atk = sp.get("atk", 0) + sp.get("spa", 0)
        my_spe = sp.get("spe", 0)
        # 공격 투자했는데 메타는 방어형인 경우 → 의도적 이탈(경고만, 감점은 약하게)
        if my_atk >= 16 and m_atk == 0:
            pts -= 2.0
            notes.append("%s 공격 투자하지만 메타는 방어형 (-2, 의도적이면 OK)" % _p_name(p))
    return max(0.0, pts), notes


def score_balance(team: list[dict], ds: dict[str, dict]) -> tuple[float, list[str]]:
    """화력/내구 밸런스 (10점 만점). 물리/특수/내구 역할 분산."""
    notes = []
    attackers = 0
    tanks = 0
    for slot in team:
        sp = slot.get("sp", {})
        atk_inv = sp.get("atk", 0) + sp.get("spa", 0)
        def_inv = sp.get("def", 0) + sp.get("spd", 0) + sp.get("hp", 0)
        if atk_inv >= 20:
            attackers += 1
        if def_inv >= 30:
            tanks += 1
    pts = 10.0
    # 공격 역할만 있거나 방어 역할만 있으면 단조
    if attackers == len(team):
        pts -= 3.0
        notes.append("전원 공격 투자 — 내구 부족 (-3)")
    if tanks == len(team):
        pts -= 3.0
        notes.append("전원 방어 투자 — 화력 부족 (-3)")
    # 적절한 분산
    if 2 <= attackers <= 4 and 1 <= tanks <= 4:
        pts += 0
        notes.append("공격/내구 역할 분산 양호")
    return max(0.0, min(10.0, pts)), notes


def grade(total: float) -> str:
    if total >= 85:
        return "S"
    if total >= 70:
        return "A"
    if total >= 55:
        return "B"
    if total >= 40:
        return "C"
    return "D"


def main() -> None:
    ap = argparse.ArgumentParser(description="팀 평가 스코어")
    ap.add_argument("team", help="팀 JSON 파일 경로")
    ap.add_argument("--dataset", default=None,
                    help="데이터셋. 생략 시 --format 에 따라 자동")
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

    dataset = a.dataset or ("champs_%s.json" % a.format)
    ds = load_dataset(dataset)
    team_name = os.path.splitext(os.path.basename(a.team))[0]

    items = [
        ("defense_coverage", 35, score_defense(team, ds)),
        ("speed_control", 20, score_speed(team, ds)),
        ("synergy", 20, score_synergy(team, ds)),
        ("archetype", 15, score_archetype(team, ds)),
        ("firepower_durability", 10, score_balance(team, ds)),
    ]

    print("=== %s: %s [%s] ===" % (L(LANG, "team_eval"), team_name, a.format))
    print()
    total = 0
    for key, maxp, (pts, notes) in items:
        total += pts
        bar = "#" * int(pts / 2)
        print("  %-14s %5.1f / %2d  %s" % (L(LANG, key), pts, maxp, bar))
        for n in notes:
            print("              · %s" % n)
    print()
    print("  %s %.1f / 100  [%s]" % (L(LANG, "total_score"), total, grade(total)))


if __name__ == "__main__":
    main()
