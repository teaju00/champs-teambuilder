# -*- coding: utf-8 -*-
"""
데이터 기반 역할 힌트 생성기.

배경:
  챔피언스는 메인라인 포켓몬과 아이템 풀/수치가 다르다.
  정적 추측 힌트를 쓰면 틀릴 위험이 크므로,
  실제 사용 데이터(champs_singles.json)에서 당겨온 pkmnchamps 한국어 원문 효과로
  "왜 이 기술/아이템/특성이 자주 쓰이는가" 를 데이터 기반으로 요약한다.

  각 함수는 영문 이름(slug) + (선택) 디테일 dict 를 받아 한국어 한 줄 힌트를 반환.
  디테일이 부족하면 None 반환 -> kb_builder 는 힌트 없이 이름만 표시.
"""

from battle_rules import (
    DAMAGE_CLASS_KO, TYPE_KO, type_multiplier,
)


def move_role_hint(name_en: str, detail: dict | None = None,
                   user_types: list[str] | None = None) -> str | None:
    """기술 힌트를 데이터 기반으로 생성.
    detail 은 champs_singles 의 move_detail ({위력,명중률,PP,타입,분류,효과,선공도,범위,플래그}).
    user_types: 이 기술을 쓰는 포켓몬의 타입(STAB 여부 판정용).
    """
    if not name_en:
        return None
    slug = name_en.lower().replace(" ", "-").replace(".", "").replace("'", "")
    d = detail or {}

    parts = []

    # STAB(자속) 여부
    move_type = d.get("타입")
    if move_type and user_types and move_type in user_types:
        parts.append("자속")

    # 범위기 힌트 (더블에서 중요) — 타입 기반 추정
    if slug == "earthquake":
        parts.append("양쪽 범위기(지진) - 파트너는 보호로 피함")
    elif slug == "rock-slide":
        parts.append("양쪽 범위기 + 30% 풀죽음")
    elif slug == "blizzard":
        parts.append("양쪽 범위기 (싸라기눈시 명중 100%)")
    elif slug in ("surf", "muddy-water", "dazzling-gleam"):
        parts.append("양쪽 범위기")

    # 우선도/선공
    if slug in ("fake-out", "sucker-punch", "extreme-speed",
                "bullet-punch", "mach-punch", "quick-attack",
                "aqua-jet", "ice-shard", "shadow-sneak"):
        parts.append("우선도 선공")
    if slug == "fake-out":
        parts.append("데려온 첫턴만, 100% 풀죽임 (이후 선택불가)")

    # 보조기
    if slug == "protect":
        parts.append("그 턴 무효 (PP 8, 더블 기본기)")
    elif slug in ("trick-room",):
        parts.append("5턴 스피드 역전")
    elif slug in ("tailwind",):
        parts.append("4턴 아군 스피드 2배 (속도조절)")
    elif slug in ("follow-me", "rage-powder"):
        parts.append("상대 기술 자신에게 유도 (파트너 보호)")
    elif slug == "helping-hand":
        parts.append("파트너 기술 위력 1.5배")
    elif slug in ("reflect", "light-screen", "aurora-veil"):
        parts.append("스크린(데미지 절감)")
    elif slug in ("thunder-wave", "glare", "stun-spore"):
        parts.append("마비(12.5% 행동불가, 스피드 50%)")

    # 강력한 화력
    power = d.get("위력")
    if isinstance(power, (int, float)) and power >= 120:
        parts.append("고화력")

    if not parts:
        return None
    return ", ".join(parts)


def _has_hangul(s: str | None) -> bool:
    return bool(s) and any("가" <= c <= "힣" for c in s)


def item_role_hint(name_en: str, detail: dict | None = None) -> str | None:
    """지닌도구 한국어 효과 설명.

    우선순위:
      1) detail 에 담긴 한국어 원문(pkmnchamps effectKo) — 347개 도구 전부 커버, 공식 문구
      2) 열매 일반 설명 / 영문 표시

    (이전에는 item_effects_ko 손매핑을 구 PokeAPI 폴백으로 썼으나,
     pkmnchamps 원문이 347개 도구를 전부 한국어로 제공하므로 폐기했다.)
    """
    if not name_en:
        return None
    slug = name_en.lower().replace(" ", "-").replace(".", "").replace("'", "")
    d = detail or {}
    eff = d.get("item_effect")

    # 1) 공식 한국어 원문 우선
    if _has_hangul(eff):
        return eff

    # 2) 매핑되지 않은 열매 fallback
    if "berry" in slug:
        return "열매 (발동 조건에 따라 회복/반감/해이상 등)"

    # 3) 그 외 — 영문임을 명시
    if eff:
        return f"[영문 효과] {eff}"
    return None


def ability_role_hint(name_en: str, detail: dict | None = None) -> str | None:
    """특성 힌트. detail 은 {ability_effect}.
    데이터 기반: 캐시된 효과 텍스트를 간결히 정리.
    """
    if not name_en:
        return None
    slug = name_en.lower().replace(" ", "-").replace(".", "").replace("'", "")
    d = detail or {}
    eff = d.get("ability_effect")

    # 더블 메타 핵심 특성은 정확히 설명 (챔피언스 수치 반영)
    known = {
        "intimidate": "데려오면 상대 물리공격 -1단계 (더블 최강 서포트 특성)",
        "rough-skin": "접촉시 상대 최대 HP 1/8 데미지",
        "iron-barbs": "접촉시 상대 최대 HP 1/8 데미지",
        "prankster": "변화기에 우선도 +1 (서포트 우선권)",
        "speed-boost": "매턴 끝 스피드 +1단계",
        "huge-power": "물리공격 2배",
        "pure-power": "물리공격 2배",
        "drizzle": "데려오면 잔비 (비)",
        "drought": "데려오면 가뭄 (햇살)",
        "sand-stream": "데려오면 모래날림",
        "snow-warning": "데려오면 싸라기눈",
        "magic-bounce": "상태 변화기 반사",
        "multiscale": "최대 HP일 때 데미지 절반",
        "intrepid-sword": "데려오면 공격 +1단계",
        "dauntless-shield": "데려오면 방어 +1단계",
        "levitate": "땅 타입 무효 (지진 회피)",
        "flash-fire": "불꽃 무효 + 자신 불꽃 강화",
        "water-absorb": "물 무효 + 회복",
        "volt-absorb": "전기 무효 + 회복",
        "lightning-rod": "전기 무효 + 자신 특공 +1 (더블 파트너 보호)",
        "storm-drain": "물 무효 + 자신 특공 +1 (더블 파트너 보호)",
        "sapsipper": "풀 무효 + 공격 +1",
        "wonder-guard": "약점(2배 이상) 공격만 맞음",
        "parental-bond": "기술 2회 연속 (2타째 위력 0.25)",
        "technician": "위력 60 이하 기술 위력 1.5배",
        "strong-jaw": "이빨 기술 위력 1.5배",
        "sharpness": "베기 기술 위력 1.5배",
        "moxie": "상대 쓰러뜨리면 공격 +1",
        "beast-boost": "상대 쓰러뜨리면 최고 능력치 +1",
        "libero": "기술 타입으로 변신 (자속 확보)",
        "protean": "기술 타입으로 변신 (자속 확보)",
        "unburden": "도구 소모시 스피드 2배",
        "guts": "상태이상시 물리공격 1.5배",
        # 팔데아 신특성 (데이터에서 영어로 남던 것들)
        "electromorphosis": "공격 받으면 다음 전기 기술 위력 1.5배",
        "opportunist": "상대의 능력치 상승을 그대로 복사",
        "armor-tail": "상대의 우선도 기술을 무효화 (이상한끈)",
        "cud-chew": "먹은 열매를 다음 턴 끝에 한 번 더 효과 발동",
        "purifying-salt": "상태이상 무효 + 고스트 데미지 반감",
        "good-as-gold": "상대의 변화기(상태기) 무효 (보물의부적)",
        "toxic-debris": "물리 공격 받을 때 상대편에 독압정 뿌림",
        "supersweet-syrup": "데려올 때 상대 회피율 -1단계 (1회)",
        "supreme-overlord": "데려오면 쓰러진 아군 수만큼 공격/특공 +1 (최대 5단계)",
        "earth-eater": "땅 타입 공격 받으면 무효+회복 (대지포식)",
        "zero-to-hero": "교체하면 히어로폼으로 변신 (돌핀맨)",
        "hospitality": "데려올 때 아군 HP 회복 (환대)",
        "wind-power": "바람 기술 받으면 충전 상태(전기 위력 2배)",
        "guard-dog": "위협/도발 무효 + 교대 강제 무시",
    }
    if slug in known:
        return known[slug]

    # 메가진화로 얻는 특성
    if slug in ("tough-claws", "aerilate", "pixilate", "refrigerate",
                "galvanize", "normalize"):
        boost = {
            "aerilate": "노말->비행", "pixilate": "노말->페어리",
            "refrigerate": "노말->얼음", "galvanize": "노말->전기",
            "tough-claws": "접촉기 위력 1.3배",
        }
        if slug in boost:
            return f"메가진화 특성: {boost[slug]}"

    # known 에 없으면 공식 한국어 원문(pkmnchamps descKo) 사용.
    # known 을 먼저 두는 이유: 공식 문구는 "까칠까칠한 피부로 상처를 입힌다" 처럼
    # 서술적이라 수치가 없다. known 은 챔피언스 수치(1/8 등)를 담고 있어 팀빌딩에 더 쓸모 있다.
    if eff:
        return eff if len(eff) <= 120 else eff[:117] + "..."
    return None
