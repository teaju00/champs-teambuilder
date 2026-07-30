# -*- coding: utf-8 -*-
"""pkmnchamps 원본 -> kb_builder 가 먹는 데이터셋 형태로 변환.

왜 새 빌더를 안 만들고 변환기를 만드는가:
  kb_builder.py / kb_search.py / team_builder.py 가 이미 특정 스키마에 의존한다.
  소스만 갈아끼우면 문서 생성·검색·팀빌더가 그대로 동작한다.

PokeAPI 기반(translate_pipeline.py) 대비 개선점:
  - 도구 효과: 손으로 쓴 item_effects_ko 매핑 -> pkmnchamps effectKo 원문
  - 특성 효과: data_hints 의 known 딕트 -> descKo 원문
  - 기술: priority(선공도) / targetKo(범위) / flags 추가
  - 메가: 메가 후 종족값·타입·특성까지
  - pick_rank: 전체 사용률 순위 (비주류 판단용)
  - 합법성: regulationMB

합법 판정 주의:
  regulationMB 플래그만 믿으면 안 된다. 데스판·모르페코는 플래그가 False 인데
  20개 사용률 파일 전부에 실제로 등장한다(현재 M-B 싱글 #125, #174).
  그래서 **"플래그가 True 이거나, 현재 사용률에 존재"** 를 합법으로 본다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "data/pkmnchamps"

# pkmnchamps 스탯키 -> 기존 데이터셋(PokeAPI 계열) 스탯키
STAT_MAP = {
    "hp": "hp", "atk": "attack", "def": "defense",
    "spa": "special-attack", "spd": "special-defense", "spe": "speed",
}
EV_MAP = {
    "hp": "hp_points", "atk": "attack_points", "def": "defense_points",
    "spa": "sp_atk_points", "spd": "sp_def_points", "spe": "speed_points",
}
TARGET_KO = {
    "all-other-pokemon": "상대 전체 + 아군(전체 범위)",
    "all-opponents": "상대 양쪽",
    "selected-pokemon": "상대 1마리",
    "user": "자신",
    "users-field": "자신 진영",
    "opponents-field": "상대 진영",
    "entire-field": "필드 전체",
    "all-pokemon": "필드의 모든 포켓몬",
    "random-opponent": "상대 랜덤 1마리",
    "user-and-allies": "자신과 아군",
    "ally": "아군",
}
# 팀빌딩에서 의미 있는 플래그만
FLAG_KO = {
    "contact": "접촉", "punch": "펀치", "sound": "소리", "pulse": "파동",
    "bite": "이빨", "dance": "춤", "powder": "가루", "heal": "회복",
    "charge": "차지필요", "recharge": "경직",
}


def load(name: str):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def title_en(s: str | None) -> str:
    """pkmnchamps 의 nameEn 은 소문자다 (garchomp). 문서 표기는 Garchomp 로."""
    if not s:
        return ""
    return "-".join(w.capitalize() for w in s.split("-"))


def pct(v) -> str:
    try:
        return "%.1f%%" % float(v)
    except (TypeError, ValueError):
        return ""


class Source:
    def __init__(self, usage_file: str):
        self.pokemon = load("pokemon.json")
        self.megas = load("megas.json")
        self.forms = load("forms.json")
        self.moves = load("moves.json")
        self.items = load("items.json")
        self.abilities = load("abilities.json")
        self.natures = {n["name"]: n for n in load("natures.json")}
        self.usage = load(usage_file)
        self.usage_file = usage_file
        self.by_id = {p["id"]: p for p in self.pokemon}
        self.form_by_name = {f["name"]: f
                             for v in self.forms.values() for f in v}
        # 주의: 사용률 데이터는 메가 폼도 mega_form 이 아니라 region_form 에 담아 보낸다
        # (예: 냐오닉스의 "meowstic-mega"). 그래서 메가 맵도 이름으로 찾을 수 있어야 한다.
        self.mega_by_name = {f["name"]: f
                             for v in self.megas.values() for f in v}
        self.used_ids = {r["pokemon_id"] for r in self.usage}

    # -- 합법성 ----------------------------------------------------------
    def is_legal(self, pid: int) -> bool:
        p = self.by_id.get(pid)
        if not p:
            return False
        return bool(p.get("regulationMB")) or pid in self.used_ids

    # -- 폼 해석 ---------------------------------------------------------
    def resolve(self, row: dict) -> tuple[dict, str]:
        """usage 행 -> (종족/폼 데이터, showdown_id)."""
        rf = row.get("region_form") or row.get("mega_form") or ""
        src = self.form_by_name.get(rf) or self.mega_by_name.get(rf)
        if rf and src:
            f = dict(src)
            base = self.by_id.get(row["pokemon_id"]) or {}
            # 폼은 도감번호를 기본형에서 물려받는다
            f.setdefault("id", base.get("id"))
            return f, rf
        base = self.by_id.get(row["pokemon_id"])
        if not base:
            return {}, ""
        return base, base["nameEn"]

    # -- 전체 습득기 (learnset) ------------------------------------------
    def learnset_ko(self, pid: int, form_name: str = "") -> list[str]:
        """해당 종(폼)의 전체 습득기 한국어명 집합.

        pokemon.json 의 moves(영문 slug 목록)만 믿으면 안 된다 — 지방폼 고유 기술이
        통째로 빠져 있다(켄타로스 팔데아 화염종 도깨비불 등). 그래서 원종 습득기에
        모든 usage 파일에서 관측된 기술(폼별)을 합친다. validate_team 의 합법 기술
        판정이 이 필드에 의존한다.
        """
        import glob
        out: set[str] = set()
        # 원종 습득기
        base = self.by_id.get(pid) or {}
        for slug in base.get("moves") or []:
            ko = (self.moves.get(slug) or {}).get("nameKo")
            if ko:
                out.add(ko)
        # 폼 전용 습득기 (forms.json 이 습득기를 가진 경우)
        if form_name:
            f = self.form_by_name.get(form_name) or {}
            for slug in f.get("moves") or []:
                ko = (self.moves.get(slug) or {}).get("nameKo")
                if ko:
                    out.add(ko)
        return sorted(out)

    def observed_moves_all(self) -> dict[str, set[str]]:
        """모든 usage 파일(다월·다레귤)을 훑어 (폼명/한글명) -> 관측된 한국어 기술 집합.

        현 레귤 파일에서 빠진 폼이라도 과거 usage 파일에 관측치가 남아 있으므로
        전 파일을 읽는다. validate_team 의 폼별 기술 합법 판정 근거.
        """
        import glob
        out: dict[str, set[str]] = {}
        for path in glob.glob(os.path.join(SRC, "usage_*.json")):
            if "usage_index" in path:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    rows = json.load(f)
            except (OSError, ValueError):
                continue
            if not isinstance(rows, list):
                continue
            for e in rows:
                if not isinstance(e, dict):
                    continue
                form = e.get("region_form") or ""
                base = e.get("pokemon_name_ko") or ""
                names = {n for n in (form, base) if n}
                used = set()
                for m in e.get("moves") or []:
                    slug = m.get("name")
                    if not slug:
                        continue
                    ko = (self.moves.get(slug) or {}).get("nameKo", slug)
                    used.add(ko)
                for n in names:
                    out.setdefault(n, set()).update(used)
        return out

    # -- 각 섹션 ---------------------------------------------------------
    def conv_moves(self, row: dict, own_types: list[str]) -> list[dict]:
        out = []
        for i, m in enumerate(row.get("moves") or [], 1):
            if not (m.get("usage") or 0) > 0:
                continue
            d = self.moves.get(m["name"]) or {}
            flags = [ko for k, ko in FLAG_KO.items() if (d.get("flags") or {}).get(k)]
            detail = {
                "위력": d.get("power"),
                "명중률": d.get("accuracy"),
                "PP": d.get("pp"),
                "타입": d.get("type"),
                "분류": d.get("damageClass"),
                "효과": d.get("descKo"),
                "선공도": d.get("priority"),
                "범위": TARGET_KO.get(d.get("target"), d.get("targetKo") or d.get("target")),
                "플래그": flags,
                "실존": d.get("available"),
            }
            meta = d.get("meta") or {}
            if meta.get("flinchChance"):
                detail["풀죽음률"] = meta["flinchChance"]
            if meta.get("drain"):
                detail["흡수/반동"] = meta["drain"]
            if meta.get("minHits"):
                detail["연속타"] = "%s~%s" % (meta.get("minHits"), meta.get("maxHits"))
            out.append({
                "rank": i,
                "name_en": d.get("nameEn") or m["name"],
                "name_ko": d.get("nameKo") or m["name"],
                "name_ja": d.get("nameJa"),
                "percentage": pct(m["usage"]),
                "desc_ko": d.get("descKo"),
                "desc_en": d.get("descEn"),
                "desc_ja": d.get("descJa"),
                "detail": {"move_detail": detail},
            })
        return out

    def conv_items(self, row: dict) -> list[dict]:
        out = []
        for i, it in enumerate(row.get("items") or [], 1):
            if not (it.get("usage") or 0) > 0:
                continue
            d = self.items.get(it["name"]) or {}
            out.append({
                "rank": i,
                "name_en": d.get("nameEn") or it["name"],
                "name_ko": d.get("nameKo") or it["name"],
                "name_ja": d.get("nameJa"),
                "percentage": pct(it["usage"]),
                "desc_ko": d.get("effectKo") or d.get("effect"),
                "desc_en": d.get("effectEn") or d.get("effect"),
                "desc_ja": d.get("effectJa"),
                # effectKo 가 공식 한국어 효과문. 없으면 영문으로 폴백.
                "detail": {"item_effect": d.get("effectKo") or d.get("effect")},
            })
        return out

    def conv_abilities(self, row: dict) -> list[dict]:
        out = []
        for i, a in enumerate(row.get("abilities") or [], 1):
            d = self.abilities.get(a["name"]) or {}
            out.append({
                "rank": i,
                "name_en": d.get("nameEn") or a["name"],
                "name_ko": d.get("nameKo") or a["name"],
                "name_ja": d.get("nameJa"),
                "percentage": pct(a.get("usage")),
                "desc_ko": d.get("descKo"),
                "desc_en": d.get("descEn"),
                "desc_ja": d.get("descJa"),
                "detail": {"ability_effect": d.get("descKo") or d.get("descEn")},
            })
        return out

    def conv_natures(self, row: dict) -> list[dict]:
        out = []
        for i, n in enumerate(row.get("natures") or [], 1):
            if not (n.get("usage") or 0) > 0:
                continue
            d = self.natures.get(n["name"]) or {}
            up, down = d.get("up"), d.get("down")
            out.append({
                "rank": i,
                "name_en": d.get("name") or n["name"],   # nameEn 결손 — slug 사용
                "name_ko": d.get("nameKo") or n["name"],
                "name_ja": d.get("nameJa"),
                "percentage": pct(n["usage"]),
                "stat_up_down": {"up": up, "down": down},
                "detail": {"nature_stats": {"up": up, "down": down}},
            })
        return out

    def conv_spreads(self, row: dict) -> list[dict]:
        out = []
        for i, sp in enumerate(row.get("spreads") or [], 1):
            s = sp.get("sps") or {}
            pts = {EV_MAP[k]: v for k, v in s.items() if k in EV_MAP}
            out.append({
                "rank": i,
                "name_en": "/".join(str(s.get(k, 0)) for k in STAT_MAP),
                "name_ko": "/".join(str(s.get(k, 0)) for k in STAT_MAP),
                "percentage": pct(sp.get("usage")),
                "ev_points": pts,
                "sp_total": sum(s.values()),
            })
        return out

    def conv_megas(self, pid: int) -> list[dict]:
        out = []
        for f in self.megas.get(str(pid), []):
            if not f.get("regulationMB"):
                continue
            out.append({
                "name_ko": f.get("nameKo"), "name_en": f.get("name"), "name_ja": f.get("nameJa"),
                "types": f.get("types"),
                "base_stats": {STAT_MAP[k]: v for k, v in (f.get("stats") or {}).items()
                               if k in STAT_MAP},
                "base_total": sum((f.get("stats") or {}).values()),
                "abilities": [{"name_en": a["name"],
                               "name_ko": (self.abilities.get(a["name"]) or {}).get("nameKo", a["name"]),
                               "name_ja": (self.abilities.get(a["name"]) or {}).get("nameJa"),
                               "effect": (self.abilities.get(a["name"]) or {}).get("descKo")}
                              for a in f.get("abilities") or []],
            })
        return out

    # -- 엔트리 ----------------------------------------------------------
    def build(self, fmt: str = "Singles") -> dict:
        # 다월 usage 에서 관측된 폼별 기술 (한 번만 수집)
        observed = self.observed_moves_all()

        entries = []
        seen = set()
        for row in sorted(self.usage, key=lambda r: r["pick_rank"]):
            data, sid = self.resolve(row)
            if not data or sid in seen:
                continue
            seen.add(sid)
            pid = row["pokemon_id"]
            form = row.get("region_form") or ""
            stats = data.get("stats") or {}
            base_stats = {STAT_MAP[k]: v for k, v in stats.items() if k in STAT_MAP}
            types = data.get("types") or []
            name_ko = row.get("pokemon_name_ko") or data.get("nameKo")
            # learnset = 원종 습득기 ∪ 폼 관측 기술
            learn = set(self.learnset_ko(pid, form))
            learn.update(observed.get(form, set()))
            if name_ko:
                learn.update(observed.get(name_ko, set()))
            entries.append({
                "pokemon_en": title_en(data.get("nameEn") or data.get("name") or sid),
                "pokemon_ko": name_ko,
                "pokemon_ja": data.get("nameJa"),
                "showdown_id": sid,
                "format": fmt,
                "pokedex_id": pid,
                "types": types,
                "base_stats": base_stats,
                "real_stats": data.get("realStats"),
                "abilities": [{"name_en": a["name"],
                               "name_ko": (self.abilities.get(a["name"]) or {}).get("nameKo", a["name"]),
                               "name_ja": (self.abilities.get(a["name"]) or {}).get("nameJa"),
                               "is_hidden": a.get("isHidden")}
                              for a in data.get("abilities") or []],
                "pick_rank": row["pick_rank"],
                "usage_total": len(self.usage),
                "regulation_mb": bool(self.by_id.get(pid, {}).get("regulationMB")),
                "legal": self.is_legal(pid),
                "form": form,
                "megas": self.conv_megas(pid),
                "learnset": sorted(learn),
                "usage": {
                    "moves": self.conv_moves(row, types),
                    "abilities": self.conv_abilities(row),
                    "held_items": self.conv_items(row),
                    "teammates": [{"name_ko": t.get("name_ko"),
                                   "name_en": "", "percentage": pct(t.get("usage"))}
                                  for t in row.get("teammates") or []],
                    "natures": self.conv_natures(row),
                    "ev_spreads": self.conv_spreads(row),
                },
            })

        # 사용률엔 없지만 합법인 포켓몬도 넣는다 (비주류 발굴 대상)
        for p in self.pokemon:
            if not p.get("regulationMB") or p["id"] in self.used_ids:
                continue
            stats = p.get("stats") or {}
            name_ko = p["nameKo"]
            learn = set(self.learnset_ko(p["id"], ""))
            learn.update(observed.get(name_ko, set()))
            entries.append({
                "pokemon_en": title_en(p["nameEn"]), "pokemon_ko": name_ko,
                "pokemon_ja": p.get("nameJa"),
                "showdown_id": p["nameEn"], "format": fmt,
                "pokedex_id": p["id"], "types": p.get("types") or [],
                "base_stats": {STAT_MAP[k]: v for k, v in stats.items() if k in STAT_MAP},
                "real_stats": p.get("realStats"),
                "abilities": [{"name_en": a["name"],
                               "name_ko": (self.abilities.get(a["name"]) or {}).get("nameKo", a["name"]),
                               "name_ja": (self.abilities.get(a["name"]) or {}).get("nameJa"),
                               "is_hidden": a.get("isHidden")}
                              for a in p.get("abilities") or []],
                "pick_rank": None, "usage_total": len(self.usage),
                "regulation_mb": True, "legal": True, "form": "",
                "megas": self.conv_megas(p["id"]),
                "learnset": sorted(learn),
                "usage": {"moves": [], "abilities": [], "held_items": [],
                          "teammates": [], "natures": [], "ev_spreads": []},
            })

        return {
            "source": "pkmnchamps.com",
            "usage_file": self.usage_file,
            "format": fmt,
            "count": len(entries),
            "pokemon": entries,
        }


def main() -> None:
    ap = argparse.ArgumentParser(description="pkmnchamps -> KB 데이터셋 변환")
    ap.add_argument("--usage", default=None,
                    help="usage 파일명. 생략 시 --format 에 따라 현행 M-B 파일 자동 선택")
    ap.add_argument("--format", default="Singles", choices=["Singles", "Doubles"])
    ap.add_argument("--out", default=None,
                    help="출력 파일. 생략 시 --format 에 따라 자동 (champs_singles.json / champs_doubles.json)")
    ap.add_argument("--both", action="store_true",
                    help="싱글+더블 둘 다 빌드 (현행 M-B 기준)")
    a = ap.parse_args()

    def _default_usage(fmt: str) -> str:
        return "usage_reg_mb_2026-07_%s.json" % ("singles" if fmt == "Singles" else "doubles")

    def _default_out(fmt: str) -> str:
        return "champs_%s.json" % ("singles" if fmt == "Singles" else "doubles")

    def _build_one(fmt: str, usage: str | None, out: str | None) -> None:
        usage = usage or _default_usage(fmt)
        out = out or _default_out(fmt)
        src = Source(usage)
        ds = src.build(fmt)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(ds, f, ensure_ascii=False, indent=1)

        ranked = sum(1 for p in ds["pokemon"] if p["pick_rank"])
        megas = sum(1 for p in ds["pokemon"] if p["megas"])
        with_learn = sum(1 for p in ds["pokemon"] if p.get("learnset"))
        flagfix = [p["pokemon_ko"] for p in ds["pokemon"]
                   if p["legal"] and not p["regulation_mb"]]
        print("[OK] %s  %d 엔트리 (사용률 있음 %d / 미사용 합법 %d)"
              % (out, ds["count"], ranked, ds["count"] - ranked))
        print("     메가 보유 %d | 폼 %d | learnset 보유 %d"
              % (megas, sum(1 for p in ds["pokemon"] if p["form"]), with_learn))
        print("     플래그 False 지만 실사용이라 합법 처리: %s" % (", ".join(flagfix) or "없음"))

    if a.both:
        _build_one("Singles", None, None)
        _build_one("Doubles", None, None)
    else:
        _build_one(a.format, a.usage, a.out)


if __name__ == "__main__":
    main()
