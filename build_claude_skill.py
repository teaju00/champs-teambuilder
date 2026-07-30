# -*- coding: utf-8 -*-
"""claude.ai / Claude API 업로드용 포터블 Agent Skill 패키지 빌드.

.agents/skills/champs-team-builder/SKILL.md 는 리포를 열어 Bash로 로컬 파일을
읽는 코딩 에이전트(Claude Code, Cursor 등) 전용이다. claude.ai 의 커스텀 Skill은
그 리포에 접근할 수 없고, zip 하나에 담긴 파일만 본다 — 그래서 SKILL.md와
CLI 스크립트, 데이터를 한 폴더에 모아 별도로 압축해야 한다.

이 스크립트는 그 zip을 만든다:
  python build_claude_skill.py            # dist/champs-team-builder.zip 생성

레이아웃은 리포 루트와 동일한 flat 구조를 그대로 쓴다 (스크립트들이 이미
os.path.dirname(__file__) 기준으로 데이터를 찾으므로, 같은 폴더에 스크립트+
데이터를 나란히 두면 CWD 와 무관하게 동작한다).
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_SKILL_MD = os.path.join(BASE_DIR, ".agents", "skills", "champs-team-builder", "SKILL.md")
BUILD_DIR = os.path.join(BASE_DIR, "build", "champs-team-builder")
DIST_DIR = os.path.join(BASE_DIR, "dist")
ZIP_PATH = os.path.join(DIST_DIR, "champs-team-builder.zip")

# claude.ai custom Skill 업로드는 두 한도가 있다: 압축 해제 크기 30MB, 파일 개수 200개.
# data/pkmnchamps 전체(28MB, 전 레귤레이션·전 월 사용률 이력)를 다 넣으면 용량부터
# 넘기고, knowledge_base/pokemon/*.md(237개)를 그대로 넣으면 그것만으로 개수 한도를
# 넘긴다 — 둘 다 내용은 그대로 두고 개수/용량만 줄인다.
SOFT_LIMIT_MB = 28  # 30MB 제한에 여유를 둔 목표치(신규 포켓몬 등으로 KB가 조금씩 늘어나므로)
MAX_FILES = 200

# 런타임에 실제로 필요한 것만. 데이터 재수집 파이프라인(pkmnchamps_source.py,
# champs_dataset.py, kb_builder.py, guides_builder.py)은 네트워크가 필요해서
# 샌드박스 Skill 환경에선 못 돌리므로 뺀다.
SCRIPT_FILES = [
    "kb_search.py", "offmeta.py", "validate_team.py",
    "team_doc.py", "team_score.py", "meta_trend.py",
    "battle_rules.py", "i18n.py", "data_hints.py",
]
DATA_ITEMS = [
    "champs_singles.json",
    "champs_doubles.json",
]

# offmeta.py 가 로드하는 정적 참조 파일 (megas/forms/natures/guide_i18n 은
# 데이터 갱신 파이프라인 전용이라 런타임 CLI 중 아무도 안 읽는다 — 뺀다)
PKMNCHAMPS_STATIC_FILES = ["pokemon.json", "moves.json", "items.json", "abilities.json"]

# meta_trend.py 는 같은 레귤레이션·포맷의 사용률 파일이 최소 2개월 있어야 트렌드를
# 비교한다. 현 레귤레이션(M-B)만, 최근 이 개수만큼만 담는다 — m1/showdown-ma 레귤레이션
# 이력은 이 패키지엔 없음(전체가 필요하면 GitHub 리포를 쓴다).
USAGE_MONTHS_KEPT = 2

DATA_PIPELINE_LINE = (
    "데이터 갱신 파이프라인과 `data/pkmnchamps/` 파일별 상세는 "
    "`references/data-pipeline.md` 참조."
)

FULL_DATA_NOTE = (
    "더 정확하고 넓은 원본이 `data/pkmnchamps/` 에 있다(pokemon.json 1025마리, moves.json,\n"
    "items.json, abilities.json, 사용률 파일들). **애매하면 이쪽을 본다.**"
)
FULL_DATA_NOTE_PACKAGED_SUFFIX = (
    "\n(이 패키지는 용량 제한 때문에 사용률 파일을 현재 레귤레이션(M-B) 최근 "
    + str(USAGE_MONTHS_KEPT)
    + "개월치만 담았다 — `meta_trend.py` 트렌드 비교도 이 범위 안에서만 된다. "
    "전체 이력·다른 레귤레이션이 필요하면 GitHub 리포를 쓴다.)"
)

# zip 파일 개수 200개 한도 때문에, 포켓몬별/가이드별 문서를 각각 파일 하나로 합친다
# (내용은 그대로, 개수만 줄임). SKILL.md 의 지식구조 트리도 그에 맞춰 고쳐야 한다.
KB_TREE_ORIGINAL = (
    "├── pokemon/*.md      # 포켓몬별 상세 문서 (종족값/특성/기술/도구/성격/EV/약점)\n"
    "└── guides/*.md       # pkmnchamps 공식 가이드 7종 (날씨/필드/특성/타입/상태이상/능력치/명중률)"
)
KB_TREE_PACKAGED = (
    "├── pokemon_all.md    # 포켓몬별 상세 문서 전체 (종족값/특성/기술/도구/성격/EV/약점),\n"
    "│                     #   '# <한글이름>' 헤더로 구분 — 파일 개수 한도 때문에 한 파일로 합침\n"
    "└── guides_all.md     # pkmnchamps 공식 가이드 7종 (날씨/필드/특성/타입/상태이상/능력치/명중률), 동일 방식"
)

ATTRIBUTION_SECTION = """## 데이터 스냅샷 & 출처

이 패키지에 포함된 데이터는 특정 시점 스냅샷이다 (재수집 파이프라인은 네트워크가
필요해서 이 패키지엔 포함하지 않았다). 최신 데이터가 필요하면 GitHub 리포
(https://github.com/teaju00/champs-teambuilder) 에서 `python build_claude_skill.py`
로 새로 빌드한다.

데이터 출처: [Pokemon Champions Battle Data](https://championsbattledata.com/)
([license](https://championsbattledata.com/license.html)). 공유·재사용 시
Pokemon Champions Battle Data 를 출처로 표기하고 https://championsbattledata.com/
를 링크할 것.
"""


def build_skill_md() -> str:
    text = open(SOURCE_SKILL_MD, encoding="utf-8").read()
    text = text.replace(DATA_PIPELINE_LINE, "").rstrip() + "\n"
    text = text.replace(FULL_DATA_NOTE, FULL_DATA_NOTE + FULL_DATA_NOTE_PACKAGED_SUFFIX)
    text = text.replace(KB_TREE_ORIGINAL, KB_TREE_PACKAGED)
    text = re.sub(
        r"\n## 데이터 갱신 \(사용자가 명시적으로 요청할 때만\)\n.*\Z",
        "\n" + ATTRIBUTION_SECTION,
        text,
        flags=re.S,
    )
    return text


def _concat_md(src_dir: str, filenames: list[str], dst_path: str) -> None:
    with open(dst_path, "w", encoding="utf-8") as out:
        for i, fname in enumerate(filenames):
            if i:
                out.write("\n\n---\n\n")
            out.write(open(os.path.join(src_dir, fname), encoding="utf-8").read().rstrip())
            out.write("\n")


def copy_knowledge_base(dst_dir: str) -> None:
    src_dir = os.path.join(BASE_DIR, "knowledge_base")
    os.makedirs(dst_dir, exist_ok=True)

    for name in ("rules.md", "summary.md", "type_chart.md"):
        shutil.copy2(os.path.join(src_dir, name), os.path.join(dst_dir, name))

    pokemon_dir = os.path.join(src_dir, "pokemon")
    pokemon_files = sorted(os.listdir(pokemon_dir))
    _concat_md(pokemon_dir, pokemon_files, os.path.join(dst_dir, "pokemon_all.md"))

    guides_dir = os.path.join(src_dir, "guides")
    guide_files = sorted(f for f in os.listdir(guides_dir) if f.endswith(".md"))
    _concat_md(guides_dir, guide_files, os.path.join(dst_dir, "guides_all.md"))

    # index.json 의 doc_path 는 원래 "pokemon/<id>.md" 를 가리킨다. 위에서 한 파일로
    # 합쳤으니, kb_search.py 가 출력하는 안내 경로도 맞춰서 고쳐야 한다.
    index = json.load(open(os.path.join(src_dir, "index.json"), encoding="utf-8"))
    for entry in index.get("pokemon", []):
        if str(entry.get("doc_path", "")).startswith("pokemon/"):
            entry["doc_path"] = "pokemon_all.md"
    with open(os.path.join(dst_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)


def copy_data_pkmnchamps(dst_dir: str) -> None:
    src_dir = os.path.join(BASE_DIR, "data", "pkmnchamps")
    os.makedirs(dst_dir, exist_ok=True)
    for name in PKMNCHAMPS_STATIC_FILES:
        shutil.copy2(os.path.join(src_dir, name), os.path.join(dst_dir, name))
    for fmt in ("singles", "doubles"):
        pattern = os.path.join(src_dir, "usage_reg_mb_*_%s.json" % fmt)
        files = sorted(glob.glob(pattern))[-USAGE_MONTHS_KEPT:]
        for f in files:
            shutil.copy2(f, os.path.join(dst_dir, os.path.basename(f)))


def main() -> None:
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)

    with open(os.path.join(BUILD_DIR, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(build_skill_md())

    for name in SCRIPT_FILES:
        shutil.copy2(os.path.join(BASE_DIR, name), os.path.join(BUILD_DIR, name))

    for item in DATA_ITEMS:
        src = os.path.join(BASE_DIR, item)
        dst = os.path.join(BUILD_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    copy_knowledge_base(os.path.join(BUILD_DIR, "knowledge_base"))
    copy_data_pkmnchamps(os.path.join(BUILD_DIR, "data", "pkmnchamps"))

    all_files = [
        os.path.join(root, f)
        for root, _dirs, files in os.walk(BUILD_DIR)
        for f in files
    ]
    uncompressed_mb = sum(os.path.getsize(p) for p in all_files) / (1024 * 1024)
    n_files = len(all_files)

    if uncompressed_mb > 30:
        print("경고: 압축 해제 크기 %.1f MB — claude.ai 업로드 한도(30MB) 초과!" % uncompressed_mb)
    elif uncompressed_mb > SOFT_LIMIT_MB:
        print("주의: 압축 해제 크기 %.1f MB — 30MB 한도에 근접" % uncompressed_mb)
    if n_files > MAX_FILES:
        print("경고: 파일 %d개 — claude.ai 업로드 한도(%d개) 초과!" % (n_files, MAX_FILES))

    os.makedirs(DIST_DIR, exist_ok=True)
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(BUILD_DIR):
            for fname in files:
                fpath = os.path.join(root, fname)
                arcname = os.path.join(
                    "champs-team-builder",
                    os.path.relpath(fpath, BUILD_DIR),
                )
                zf.write(fpath, arcname)

    zip_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print("빌드 완료: %s (zip %.1f MB, 압축 해제 %.1f MB, 파일 %d개)"
          % (ZIP_PATH, zip_mb, uncompressed_mb, n_files))


if __name__ == "__main__":
    main()
