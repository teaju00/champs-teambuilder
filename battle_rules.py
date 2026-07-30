# -*- coding: utf-8 -*-
"""
포켓몬 챔피언스 (Pokémon Champions) 공식 배틀 규칙 + 한국어 지식베이스.

*** 본 파일의 규칙은 공식/권위 소스에서 인용한 챔피언스 실제 규칙입니다 ***
  - 공식: champions.pokemon.com/en-us/gameplay
  - Serebii: serebii.net/pokemonchampions/  (상태이상, 메가진화 등)
  - IGN: ign.com/wikis/pokemon-champions/Biggest_Changes_Explained  (변경점)
  - VictoryRoad: victoryroad.pro/champions-regulations/  (Regulation Set)

*** 주의: 챔피언스는 메인라인 포켓몬과 다른 별개 게임입니다 ***
  - 아이템 풀, 상태이상 수치, IV/EV 시스템, PP 등이 모두 다름.
  - 따라서 일반 포켓몬 배틀 지식을 그대로 적용하면 틀립니다.
  - 특정 기술/아이템/특성의 "왜 좋은가" 힌트는 정적 추측이 아니라
    kb_builder.py 가 실제 사용 데이터 기반으로 동적으로 생성합니다.

타입 상성만은 시리즈 공통이므로 그대로 사용합니다.
"""

# ---------------------------------------------------------------------------
# 1) 게임 개요 + 경쟁 규칙 (공식 소스 인용)
#    ※ Regulation Set M-B 기준 (2026-06-17 ~ 2026-09-02, 2026 월드 대회 포맷)
# ---------------------------------------------------------------------------
CHAMPIONS_RULES = {
    "게임": "포켓몬 챔피언스 (Pokémon Champions) — 2025년 공개된 배틀 중심 스핀오프",
    "플랫폼": "Nintendo Switch / 모바일",
    "데이터_기준": "Regulation Set M-B (2026-06-17 ~ 2026-09-02). 월드 챔피언십 공식 포맷.",

    "배틀_모드": {
        "Ranked": "랭크배틀. 전 세계 플레이어와 대전, 결과에 따라 랭크 변동. 시즌제.",
        "Casual": "캐주얼 배틀. 가볍게 즐기는 모드.",
        "Private": "프라이빗 배틀. 친구와 커스텀 대전.",
    },

    "배틀_포맷": {
        # victoryroad.pro 기준: 공식 VGC 포맷은 Doubles. Singles 도 지원하나 비경쟁.
        "Doubles": (
            "더블배틀 (공식 VGC 포맷). 6마리를 등록해 4마리를 선발한다. "
            "한쪽 4마리가 모두 쓰러지면 패배. 팀 시너지와 행동순서(속도)가 핵심."
        ),
        "Singles": (
            "싱글배틀. 6마리를 등록해 3마리를 선발한다 (사용자 확인). "
            "1대1 교대전 — 선발한 3마리가 모두 쓰러지면 패배."
        ),
    },

    "팀구성_규칙_공통": [
        "종족 조항(Species Clause): 같은 종의 포켓몬을 2마리 이상 편성할 수 없다.",
        "지닌도구 중복 금지: 같은 도구를 2마리 이상 지닐 수 없다.",
        "레벨 자동 조정: 레벨 50 기준으로 자동 스케일링 (50 초과/미만 모두 50으로).",
        "포켓몬 출처: 게임 내 획득, 포켓몬 HOME 연동, 공식 이벤트 배포만 사용 가능.",
        "출전 포켓몬은 Regulation Set 에 따라 결정됨. "
        "M-B 는 M-A 대비 22마리 추가 + 16개 새 메가진화 허용.",
    ],
    "팀구성_규칙_Doubles": [
        "공식 더블(VGC): 6마리 등록 -> 4마리 선발. 한쪽 4마리 전멸시 패배.",
    ],
    "팀구성_규칙_Singles": [
        "싱글배틀: 6마리 등록 -> 3마리 선발. 선발 3마리 전멸시 패배.",
        "선발 전 상대 6마리를 확인할 수 있으므로, 등록 6마리는 "
        "'매치업별로 골라 쓰는 카드 묶음'으로 설계해야 한다 "
        "(같은 역할 2마리를 넣어 상성 좋은 쪽만 선발하는 식).",
        "3마리만 나가므로 역할 중복은 손실이 크다. 단, 서로 선발되지 않는 "
        "'페어' 관계라면 약점이 겹쳐도 문제없다.",
        "스텔스록·압정뿌리기 같은 장판기는 상대가 3마리뿐이라 "
        "더블/6마리전보다 가치가 낮다. 즉발 화력·강제교대기가 상대적으로 유효.",
    ],

    # IV/EV/SP — pkmnchamps.com/guide/stats 공식 계산식 + 사용자 확인 + 사용률 데이터 검증
    "육성_시스템": {
        "IV": "모든 포켓몬이 개체값(IV) 31 고정으로 지급됨. "
              "보틀캡/교배/반복포획 불필요. **IV 를 낮출 수 없으므로** "
              "트릭룸용 스피드 IV 0 같은 전략은 불가 — 감속은 성격과 SP 0 으로만 한다.",
        "SP(노력치)": (
            "SP 는 슬라이더로 자유롭게 조정한다. "
            "**스탯당 0~32, 전체 합산 최대 66 포인트.** "
            "1 SP = 실수치 1 상승 (레벨 50 기준). "
            "합이 66 이라 '32 + 32 + 2' 또는 '32 + 32'(2 미투자) 배분이 대부분이다."
        ),
        "성격": (
            "성격은 **변경 가능**하다 (사용자 확인). 즉 원하는 보정을 항상 맞출 수 있어, "
            "트릭룸 팀은 감속 성격(용감/냉정/무사태평/건방)을 자유롭게 채용한다."
        ),
        "실수치_공식_HP": "⌊(2×종족값 + 31 + SP×2) / 2⌋ + 60  (HP 는 성격 보정 없음)",
        "실수치_공식_그외": "⌊(⌊(2×종족값 + 31 + SP×2) / 2⌋ + 5) × 성격보정⌋  "
                       "(성격보정 = 1.1 / 1.0 / 0.9)",
        "VP": (
            "VP(Victory Points): 랭크배틀 결과로 획득, 포켓몬 영입/육성에 사용. "
            "직접 구매 불가 (pay-to-win 방지)."
        ),
    },
}


def real_stat(base: int, sp: int, is_hp: bool = False, nature: float = 1.0) -> int:
    """레벨 50 실수치. pkmnchamps 능력치 가이드의 공식 그대로.

    base   : 종족값
    sp     : 노력치 포인트 (스탯당 0~32, 팀 전체 합 66 제한은 호출측 책임)
    is_hp  : HP 는 성격 보정이 없고 +60 이 붙는다
    nature : 1.1(상승) / 1.0(무보정) / 0.9(하락)
    """
    core = (2 * base + 31 + sp * 2) // 2
    if is_hp:
        return core + 60
    return int((core + 5) * nature)


SP_TOTAL_MAX = 66   # 전체 합산 상한
SP_STAT_MAX = 32    # 스탯당 상한


def sp_spread_valid(spread: dict[str, int]) -> tuple[bool, str]:
    """SP 배분이 챔피언스 규칙에 맞는지 검사. spread 는 {hp,atk,def,spa,spd,spe}."""
    total = sum(spread.values())
    for k, v in spread.items():
        if v < 0 or v > SP_STAT_MAX:
            return False, "%s=%d — 스탯당 0~%d 범위를 벗어남" % (k, v, SP_STAT_MAX)
    if total > SP_TOTAL_MAX:
        return False, "합계 %d — 최대 %d 초과" % (total, SP_TOTAL_MAX)
    return True, "합계 %d/%d" % (total, SP_TOTAL_MAX)

# ---------------------------------------------------------------------------
# 2) 메가진화 (챔피언스 핵심 메커니즘)
# ---------------------------------------------------------------------------
MEGA_EVOLUTION = {
    "개요": (
        "메가진화는 포켓몬 챔피언스의 핵심(그리고 현재 유일한) 특수 배틀 메커니즘이다. "
        "전투 중 1회, 메가스톤을 지닌 포켓몬이 메가진화한다."
    ),
    "조건": [
        "해당 포켓몬이 자신의 메가스톤(예: 한카리아스나이트)을 지닌도구로 들고 있을 것.",
        "주인공이 '옴니링(Omni Ring)' 을 장착하고 있을 것 — 메가진화에 필요한 장치.",
        "메가진화 가능 종은 Regulation Set 에 따라 결정 (M-B: M-A 의 메가 + 16종 추가).",
    ],
    "효과": [
        "종족값이 대폭 상승 (총합 +100).",
        "일부 포켓몬은 타입이나 특성이 바뀜.",
        "전투 중 1회. 더블에서는 '누가 먼저 메가진화를 터뜨리느냐'가 흐름을 결정.",
    ],
    "예외_및_참고": [
        "현재(2026년) 메가진화만 플레이 가능. "
        "테라스탈, Z기술, 다이맥스는 향후 시즌에 추가 예정이라 공식 발표됨.",
        "래이츄의 메가스톤은 아직 미구현.",
        "포켓몬 전설의 Z-A 신규 메가진화는 아직 데뷔하지 않음.",
        "모든 출전 포켓몬은 진화가 완료된 최종진화형 (피카츄만 예외).",
    ],
}

# ---------------------------------------------------------------------------
# 3) 상태이상 변화 (Serebii statusconditions 인용 — 정확한 수치)
# ---------------------------------------------------------------------------
STATUS_CONDITIONS = {
    "마비_Paralysis": {
        "행동불가_확률": "12.5% (기존 25%에서 하향)",
        "스피드": "최대치의 50%로 감소 (기존과 동일)",
        "의미": "기존보다 행동불가 확률이 절반으로 줄어, 마비의 운뽀 요소가 크게 감소함.",
    },
    "수면_Sleep": {
        "최대_지속": "강제로 2턴째에 깸 (외부 수면).",
        "확률": "2턴째에 33.3% 확률로 깨고, 3턴째엔 100% 깸.",
        "잠자기Rest": "자력 수면(잠자기)은 최대 3턴째에 깸.",
        "의미": "수면이 강해짐 — 최대 2턴(외부)만으로 풀리므로 장기전에서 운용하기 어려움.",
    },
    "빙결_Freeze": {
        "최대_지속": "빙결 후 3턴째에 보장 해동.",
        "자연_해동": "행동 시도 매턴 25% 확률로 해동.",
        "의미": "빙결 최대 3턴으로 제한되어 하드카운터 요소 감소.",
    },
    "화상_Burn": {
        "내용": "챔피언스에서 별도 변경 안내 없음 — 시리즈 표준(매턴 최대 HP 1/16 데미지, 물리공격 반감)으로 추정.",
    },
    "독_Poison": {
        "내용": "별도 변경 안내 없음 — 시리즈 표준(매턴 최대 HP 1/8 데미지; 맹독은 누적)으로 추정.",
    },
    "혼란_Confusion": {
        "내용": "별도 변경 안내 없음.",
    },
}

# ---------------------------------------------------------------------------
# 4) 주요 기술 변화 (IGN 인용)
# ---------------------------------------------------------------------------
MOVE_CHANGES = {
    "보호_Protect": {
        "변경": "PP 가 16 -> 8 로 절반. 남용이 줄고 PP 관리가 중요해짐.",
        "의미": "더블의 기본기이지만 남발할 수 없게 됨.",
    },
    "속임수_FakeOut": {
        "변경": "데려온 첫턴 사용 후에는 기술 선택 자체가 불가(PP 스톨/속이다 회피 용도 폐지).",
        "의미": "첫턴 풀죽임 용도로만 쓰이고, 그 이후엔 사실상 봉인.",
    },
    "넘기기_KnockOff": {
        "변경": "어흥염(Incineroar)이 넘기기를 잃음.",
        "의미": "어흥염의 도구 탈취 역할이 약화.",
    },
    "PP_일괄": "기술 전반의 PP/위력/보조효과 확률이 종별로 미세 조정됨 "
                "(데이터에 있는 정확 수치는 ai_dataset 의 move_detail 참조).",
    "기술_분류_추가": "섀도크루/드래곤클로가 '베기(slicing)' 분류에 추가되는 등 일부 분류 조정.",
}

# ---------------------------------------------------------------------------
# 5) 아이템 풀 (데이터 기반 — kb_builder 가 실제 사용 데이터로 보강)
#    주의: 챔피언스 아이템 풀은 메인라인과 다름. IGN 의 'removed' 목록은
#    런치(Reg M-A) 시점이라 현재(M-B)와 안 맞을 수 있음.
#    -> 그래서 정적 힌트 대신 실제 데이터 기반 힌트를 사용한다.
# ---------------------------------------------------------------------------
# (이전 버전의 잘못된 ITEM_ROLE_HINTS / ABILITY_ROLE_HINTS / MOVE_ROLE_HINTS 는 제거됨.
#  챔피언스 실제 메커니즘에 맞는 힌트만 남기고, 나머지는 데이터 기반 생성에 맡김.)

# 일반 타입/분류 한국어 라벨 (시리즈 공통, 안전)
TYPE_KO = {
    "normal": "노말", "fire": "불꽃", "water": "물", "electric": "전기",
    "grass": "풀", "ice": "얼음", "fighting": "격투", "poison": "독",
    "ground": "땅", "flying": "비행", "psychic": "에스퍼", "bug": "벌레",
    "rock": "바위", "ghost": "고스트", "dragon": "드래곤", "dark": "악",
    "steel": "강철", "fairy": "페어리",
}

STAT_LABEL_KO = {
    "hp": "HP", "attack": "공격", "defense": "방어",
    "special-attack": "특수공격", "special-defense": "특수방어", "speed": "스피드",
}

DAMAGE_CLASS_KO = {"physical": "물리", "special": "특수", "status": "변화"}

# 성격 -> (상승 스탯, 하락 스탯). 무보정 성격은 (None, None).
# data/pkmnchamps/natures.json 의 25종 그대로. real_stat() 의 nature 매개변수
# (1.1/1.0/0.9)로 변환하려면 nature_up_down(stat, nature_ko) 를 쓴다.
NATURE_MOD = {
    "굳센": (None, None), "외로움": ("atk", "def"), "용감": ("atk", "spe"),
    "고집": ("atk", "spa"), "개구쟁이": ("atk", "spd"),
    "대담": ("def", "atk"), "온순": (None, None), "무사태평": ("def", "spe"),
    "장난꾸러기": ("def", "spa"), "촐랑": ("def", "spd"),
    "겁쟁이": ("spe", "atk"), "성급": ("spe", "def"), "성실": (None, None),
    "명랑": ("spe", "spa"), "천진난만": ("spe", "spd"),
    "조심": ("spa", "atk"), "의젓": ("spa", "def"), "냉정": ("spa", "spe"),
    "수줍음": (None, None), "덜렁": ("spa", "spd"),
    "차분": ("spd", "atk"), "얌전": ("spd", "def"), "건방": ("spd", "spe"),
    "신중": ("spd", "spa"), "변덕": (None, None),
}


def nature_up_down(stat: str, nature_ko: str | None) -> float:
    """성격명과 스탯으로 보정 배율 반환. up=1.1, down=0.9, 나머지 1.0."""
    if not nature_ko:
        return 1.0
    up, down = NATURE_MOD.get(nature_ko, (None, None))
    if up == stat:
        return 1.1
    if down == stat:
        return 0.9
    return 1.0

# ---------------------------------------------------------------------------
# 6) 타입 상성 (시리즈 공통 — 챔피언스도 동일)
#    TYPE_CHART[공격타입][수비타입] = 데미지 배율
# ---------------------------------------------------------------------------
TYPE_CHART = {
    "normal":   {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water":    {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5},
    "ice":      {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5},
    "fighting": {"normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0, "dark": 2.0, "steel": 2.0, "fairy": 0.5},
    "poison":   {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0, "fairy": 2.0},
    "ground":   {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0},
    "flying":   {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5},
    "psychic":  {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5},
    "bug":      {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5},
    "rock":     {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5},
    "ghost":    {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon":   {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark":     {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
    "steel":    {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "steel": 0.5, "fairy": 2.0},
    "fairy":    {"fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5},
}


def type_multiplier(attack_type: str, *defend_types: str) -> float:
    """공격 타입이 수비 타입(들)에 주는 최종 데미지 배율."""
    if attack_type not in TYPE_CHART:
        return 1.0
    mult = 1.0
    for dt in defend_types:
        mult *= TYPE_CHART[attack_type].get(dt, 1.0)
    return mult


def describe_type_effectiveness(mult: float) -> str:
    if mult == 0:
        return "효과가 없다"
    if mult >= 4.0:
        return "효과는 굉장함 (x4)"
    if mult >= 2.0:
        return "효과는 굉장함 (x2)"
    if mult <= 0.25:
        return "효과가 거의 없음 (x0.25)"
    if mult <= 0.5:
        return "효과가 별로임 (x0.5)"
    return "보통 (x1)"


def team_defensive_profile(types_list: list[tuple[str, ...]]) -> dict:
    """팀 전체의 타입 약점 프로파일. (약점이 겹치는 타입순 정렬)"""
    weaknesses = {t: 0 for t in TYPE_KO}
    for types in types_list:
        for atk_type in TYPE_KO:
            if type_multiplier(atk_type, *types) >= 2.0:
                weaknesses[atk_type] += 1
    sorted_weak = sorted(
        [(t, c) for t, c in weaknesses.items() if c > 0],
        key=lambda x: -x[1],
    )
    return {
        "약점_겹침": [{"타입": TYPE_KO[t], "코드": t, "노출_팀원수": c} for t, c in sorted_weak],
        "안전한_타입": [TYPE_KO[t] for t, c in weaknesses.items() if c == 0],
    }


def labelize_types(types_en: list[str]) -> list[str]:
    return [TYPE_KO.get(t, t) for t in types_en]


def labelize_base_stats(base_stats: dict) -> dict:
    return {STAT_LABEL_KO.get(k, k): v for k, v in base_stats.items()}


# (이전 버전의 lookup_hint / *_ROLE_HINTS 는 챔피언스와 안 맞아 제거.
#  동적 힌트는 kb_builder.py 가 데이터 기반으로 생성.)


if __name__ == "__main__":
    # 자체 점검
    print("== 챔피언스 규칙 요약 ==")
    print(CHAMPIONS_RULES["배틀_포맷"]["Doubles"][:80], "...")
    print()
    print("== 상태이상: 마비 ==", STATUS_CONDITIONS["마비_Paralysis"])
    print()
    print("== 타입상성 점검 ==")
    print("  지진 vs 한카리아스(드래곤/땅):", type_multiplier("ground", "dragon", "ground"))
    print("  얼음 vs 한카리아스:", type_multiplier("ice", "dragon", "ground"),
          describe_type_effectiveness(type_multiplier("ice", "dragon", "ground")))
