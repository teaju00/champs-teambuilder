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

import os
import re
import shutil
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_SKILL_MD = os.path.join(BASE_DIR, ".agents", "skills", "champs-team-builder", "SKILL.md")
BUILD_DIR = os.path.join(BASE_DIR, "build", "champs-team-builder")
DIST_DIR = os.path.join(BASE_DIR, "dist")
ZIP_PATH = os.path.join(DIST_DIR, "champs-team-builder.zip")

# 런타임에 실제로 필요한 것만. 데이터 재수집 파이프라인(pkmnchamps_source.py,
# champs_dataset.py, kb_builder.py, guides_builder.py)은 네트워크가 필요해서
# 샌드박스 Skill 환경에선 못 돌리므로 뺀다.
SCRIPT_FILES = [
    "kb_search.py", "offmeta.py", "validate_team.py",
    "team_doc.py", "team_score.py", "meta_trend.py",
    "battle_rules.py", "i18n.py", "data_hints.py",
]
DATA_ITEMS = [
    "knowledge_base",
    "champs_singles.json",
    "champs_doubles.json",
    os.path.join("data", "pkmnchamps"),
]

DATA_PIPELINE_LINE = (
    "데이터 갱신 파이프라인과 `data/pkmnchamps/` 파일별 상세는 "
    "`references/data-pipeline.md` 참조."
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
    text = re.sub(
        r"\n## 데이터 갱신 \(사용자가 명시적으로 요청할 때만\)\n.*\Z",
        "\n" + ATTRIBUTION_SECTION,
        text,
        flags=re.S,
    )
    return text


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

    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print("빌드 완료: %s (%.1f MB)" % (ZIP_PATH, size_mb))


if __name__ == "__main__":
    main()
