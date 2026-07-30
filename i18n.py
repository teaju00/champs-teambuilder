# -*- coding: utf-8 -*-
"""다국어(ko/en/ja) 지원 코어.

포켓몬 챔피언스 스킬의 모든 CLI 가 언어를 전환할 수 있게 한다.
데이터 차원에서는 pokemon/moves/items/abilities 가 Ko/En/Ja 필드를 거의 완비하고
있어, 이 모듈은 (1) UI 라벨 사전, (2) 타입/스탯/분류 등 고정 명칭, (3) 설명문 폴백,
(4) 영어명 결손(natures/forms/megas) 보정 을 담당한다.

사용:
    from i18n import L, LANGS
    L("ko", "team_check")          # "팀 검사"
    L("en", "team_check")          # "Team check"
    L("ja", "usage_rank")          # "使用率順位"

데이터셋/원본에서 다언어 값을 꺼낼 때는 pick_desc() / pick_name() 를 쓴다.
"""

from __future__ import annotations

LANGS = ["ko", "en", "ja"]
DEFAULT_LANG = "ko"

# ---------------------------------------------------------------------------
# 1) UI 라벨 사전 — CLI 출력의 고정 문구
# ---------------------------------------------------------------------------
_LABELS: dict[str, dict[str, str]] = {
    # kb_search
    "pokemon_search": {"ko": "포켓몬 검색", "en": "Pokémon search", "ja": "ポケモン検索"},
    "type_list": {"ko": "타입별 목록 (종족합 순)", "en": "By type (BST order)", "ja": "タイプ別（種族値順）"},
    "teammates_of": {"ko": "%s의 자주 같이 쓰이는 팀원", "en": "Frequent teammates of %s", "ja": "%sとよく一緒に使われる"},
    "bst_top": {"ko": "종족합 상위 %d", "en": "Top %d by BST", "ja": "種族値トップ%d"},
    "team_weakness": {"ko": "팀 약점 분석", "en": "Team weakness analysis", "ja": "チーム弱点分析"},
    "no_result": {"ko": "검색 결과 없음: %s", "en": "No result: %s", "ja": "結果なし: %s"},
    "members": {"ko": "팀원", "en": "Members", "ja": "メンバー"},
    "weak_overlap": {"ko": "약점 겹침 (노출 팀원수 순)", "en": "Weakness overlap (by exposed members)", "ja": "弱点の重複（露出順）"},

    # 공통 라벨
    "showdown_id": {"ko": "showdown_id", "en": "showdown_id", "ja": "showdown_id"},
    "bst": {"ko": "종족합", "en": "BST", "ja": "種族値合計"},
    "dex": {"ko": "도감", "en": "Dex", "ja": "図鑑"},
    "top_moves": {"ko": "대표 기술", "en": "Top moves", "ja": "代表的な技"},
    "top_items": {"ko": "대표 도구", "en": "Top items", "ja": "代表的な道具"},
    "abilities": {"ko": "특성", "en": "Abilities", "ja": "特性"},
    "detail": {"ko": "상세", "en": "Detail", "ja": "詳細"},
    "rank": {"ko": "순위", "en": "Rank", "ja": "順位"},
    "usage_rank": {"ko": "사용률 순위", "en": "Usage rank", "ja": "使用率順位"},
    "type": {"ko": "타입", "en": "Type", "ja": "タイプ"},
    "role": {"ko": "역할", "en": "Role", "ja": "役割"},
    "item": {"ko": "도구", "en": "Item", "ja": "道具"},
    "nature": {"ko": "성격", "en": "Nature", "ja": "せいかく"},
    "moves": {"ko": "기술", "en": "Moves", "ja": "技"},

    # validate_team
    "team_check": {"ko": "팀 검사", "en": "Team check", "ja": "チーム検査"},
    "pass": {"ko": "통과", "en": "PASS", "ja": "合格"},
    "fail": {"ko": "불합격", "en": "FAIL", "ja": "不合格"},
    "warn": {"ko": "경고", "en": "WARN", "ja": "警告"},
    "note": {"ko": "참고", "en": "NOTE", "ja": "参考"},
    "verdict": {"ko": "판정", "en": "Verdict", "ja": "判定"},

    # team_doc
    "team_config": {"ko": "팀 구성", "en": "Team composition", "ja": "チーム構成"},
    "detail_per_mon": {"ko": "개체 상세", "en": "Per-member detail", "ja": "個体詳細"},
    "format": {"ko": "포맷", "en": "Format", "ja": "フォーマット"},
    "base_stats": {"ko": "종족값", "en": "Base stats", "ja": "種族値"},
    "real_stats": {"ko": "실수치", "en": "Real stats", "ja": "実数値"},
    "speed_order": {"ko": "속도 정렬", "en": "Speed order", "ja": "すばやさ順"},
    "team_weak": {"ko": "팀 약점 분석", "en": "Team weakness", "ja": "チーム弱点"},
    "sp_alloc": {"ko": "SP 배분", "en": "SP allocation", "ja": "SP配分"},

    # team_score
    "team_eval": {"ko": "팀 평가", "en": "Team evaluation", "ja": "チーム評価"},
    "defense_coverage": {"ko": "방어 커버리지", "en": "Defense coverage", "ja": "防御カバレッジ"},
    "speed_control": {"ko": "속도 컨트롤", "en": "Speed control", "ja": "すばやさ調整"},
    "synergy": {"ko": "시너지", "en": "Synergy", "ja": "シナジー"},
    "archetype": {"ko": "아키타입 일관", "en": "Archetype consistency", "ja": "アーキタイプ一貫"},
    "firepower_durability": {"ko": "화력/내구", "en": "Firepower/Durability", "ja": "火力/耐久"},
    "total_score": {"ko": "총점", "en": "Total", "ja": "合計"},

    # meta_trend
    "meta_trend": {"ko": "메타 트렌드", "en": "Meta trend", "ja": "メタトレンド"},
    "rising": {"ko": "순위 상승", "en": "Rising", "ja": "上昇"},
    "falling": {"ko": "순위 하락", "en": "Falling", "ja": "下降"},
    "rank_change": {"ko": "순위 변동", "en": "Rank change", "ja": "順位変動"},
    "rising_top": {"ko": "순위 상승", "en": "Rising top", "ja": "上昇トップ"},
    "falling_top": {"ko": "순위 하락", "en": "Falling top", "ja": "下降トップ"},
    "delta_neg": {"ko": "Δ 음수 = 상승", "en": "Δ negative = rising", "ja": "Δ負=上昇"},
    "delta_pos": {"ko": "Δ 양수 = 하락", "en": "Δ positive = falling", "ja": "Δ正=下降"},

    # offmeta
    "offmeta_candidates": {"ko": "비주류 후보", "en": "Off-meta candidates", "ja": "オフメタ候補"},
    "legal_unused": {"ko": "합법인데 사용률 데이터 없음", "en": "Legal but unused", "ja": "合法だが未使用"},

    # 약점/내성
    "weak": {"ko": "약점", "en": "Weak", "ja": "弱点"},
    "immune": {"ko": "무효", "en": "Immune", "ja": "無効"},
    "exposed_members": {"ko": "노출 팀원수", "en": "exposed", "ja": "露出"},
}


def L(lang: str, key: str, *args) -> str:
    """라벨을 해당 언어로 반환. %s/%d 치환 지원. 미정의 키면 key 그대로."""
    if lang not in LANGS:
        lang = DEFAULT_LANG
    entry = _LABELS.get(key)
    if not entry:
        return key
    s = entry.get(lang, entry.get(DEFAULT_LANG, key))
    if args:
        try:
            return s % args
        except (TypeError, ValueError):
            return s
    return s


# ---------------------------------------------------------------------------
# 2) 고정 명칭 — 타입/스탯/분류 (데이터 의존 아님)
# ---------------------------------------------------------------------------
TYPE_NAME = {
    "ko": {"normal": "노말", "fire": "불꽃", "water": "물", "electric": "전기",
           "grass": "풀", "ice": "얼음", "fighting": "격투", "poison": "독",
           "ground": "땅", "flying": "비행", "psychic": "에스퍼", "bug": "벌레",
           "rock": "바위", "ghost": "고스트", "dragon": "드래곤", "dark": "악",
           "steel": "강철", "fairy": "페어리"},
    "en": {"normal": "Normal", "fire": "Fire", "water": "Water", "electric": "Electric",
           "grass": "Grass", "ice": "Ice", "fighting": "Fighting", "poison": "Poison",
           "ground": "Ground", "flying": "Flying", "psychic": "Psychic", "bug": "Bug",
           "rock": "Rock", "ghost": "Ghost", "dragon": "Dragon", "dark": "Dark",
           "steel": "Steel", "fairy": "Fairy"},
    "ja": {"normal": "ノーマル", "fire": "ほのお", "water": "みず", "electric": "でんき",
           "grass": "くさ", "ice": "こおり", "fighting": "かくとう", "poison": "どく",
           "ground": "じめん", "flying": "ひこう", "psychic": "エスパー", "bug": "むし",
           "rock": "いわ", "ghost": "ゴースト", "dragon": "ドラゴン", "dark": "あく",
           "steel": "はがね", "fairy": "フェアリー"},
}

STAT_NAME = {
    "ko": {"hp": "HP", "atk": "공격", "def": "방어", "spa": "특공", "spd": "특방", "spe": "속도"},
    "en": {"hp": "HP", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD", "spe": "Spe"},
    "ja": {"hp": "HP", "atk": "こうげき", "def": "ぼうぎょ", "spa": "とくこう", "spd": "とくぼう", "spe": "すばやさ"},
}

DAMAGE_CLASS = {
    "ko": {"physical": "물리", "special": "특수", "status": "변화"},
    "en": {"physical": "Physical", "special": "Special", "status": "Status"},
    "ja": {"physical": "物理", "special": "特殊", "status": "変化"},
}


def type_name(lang: str, type_en: str) -> str:
    return TYPE_NAME.get(lang, TYPE_NAME[DEFAULT_LANG]).get(type_en, type_en)


def stat_name(lang: str, stat: str) -> str:
    return STAT_NAME.get(lang, STAT_NAME[DEFAULT_LANG]).get(stat, stat)


def damage_class(lang: str, cls: str) -> str:
    return DAMAGE_CLASS.get(lang, DAMAGE_CLASS[DEFAULT_LANG]).get(cls, cls)


def type_names(lang: str, types_en: list[str]) -> list[str]:
    return [type_name(lang, t) for t in types_en]


# ---------------------------------------------------------------------------
# 3) 데이터셋 다언어 값 추출 — 설명문/이름 폴백 포함
# ---------------------------------------------------------------------------
# 데이터셋(champs_*.json) 항목에서 꺼낼 때 쓰는 필드명 매핑.
# 원본(data/pkmnchamps)필드명과 다를 수 있으므로, 데이터셋 스키마를 기준으로 한다.
def pick_name(lang: str, entry: dict, *fallback_keys) -> str:
    """entry 에서 언어별 이름을 꺼낸다. 필드 우선순위: name_<lang> -> fallback_keys."""
    key = "name_" + lang
    if entry.get(key):
        return entry[key]
    for k in fallback_keys:
        if entry.get(k):
            return entry[k]
    return entry.get("name_ko") or entry.get("name_en") or "?"


def pick_desc(lang: str, entry: dict, *fallback_keys) -> str:
    """entry 에서 언어별 설명을 꺼낸다. 폴백: 요청언어 -> en -> ko -> 주어진 키."""
    for trial in ([lang, "en", "ko"] + list(fallback_keys)):
        for prefix in ("desc_", "effect_", "description_"):
            v = entry.get(prefix + trial)
            if v:
                return v
        if entry.get(trial):
            return entry[trial]
    return ""


# ---------------------------------------------------------------------------
# 4) 영어명 보정 — natures/forms/megas 의 nameEn 결손 대응
# ---------------------------------------------------------------------------
def display_en(slug: str) -> str:
    """영문 slug(bulbasaur, rattata-alola) -> 표시명(Bulbasaur, Rattia-Alola 는 아니고 Rattata-Alola).

   pokemon.json nameEn(소문자) 도 표시용으로 쓸 때 capitalize.
    """
    if not slug:
        return ""
    return "-".join(w.capitalize() for w in slug.split("-"))


def validate_lang(lang: str) -> str:
    """지원 언어 아니면 기본언어(ko)로."""
    return lang if lang in LANGS else DEFAULT_LANG
