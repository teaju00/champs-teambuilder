# 포켓몬 챔피언스 팀빌딩 스킬

**[한국어](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

**포켓몬 챔피언스(Pokémon Champions) 싱글배틀 팀 추천 스킬.** [pkmnchamps.com](https://championsbattledata.com) 의 사용률 데이터와 로컬 지식베이스를 결합해, 6마리 등록 팀을 제안하고 검증 스크립트로 합법성을 보장합니다. ZCode, Claude Code, Cursor, Gemini CLI, GitHub Copilot, Windsurf, Codex 등 사실상 모든 AI 코딩 도구에서 사용할 수 있습니다.

> 스킬 규칙의 진실의 원천은 `.agents/skills/champs-team-builder/SKILL.md` 입니다. 각 AI 도구의 인덱스 파일(`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.windsurfrules`, `.cursor/rules/`)은 이 스킬을 가리키는 얇은 포인터 역할만 합니다.

## 뭘 하나요?

"한카리아스 중심 공격형 팀 짜줘" 같은 자연어 요청이 들어오면:

1. `kb_search.py` / `offmeta.py` 로 지식베이스·사용률 통계를 검색
2. 약점 분석 + 시너지를 고려해 6마리 팀 구성
3. `validate_team.py` 로 합법성·SP 배분·아키타입 일치를 자동 검증 (**통과 전엔 제안하지 않습니다**)
4. 세팅 규칙(성격/SP/도구/기술)과 선발 가이드를 한국어로 정리

---

## 다운로드 및 설치

### 방법 1: Git으로 클론

```bash
git clone https://github.com/<사용자명>/champs-teambuilder.git
cd champs-teambuilder
```

### 방법 2: ZIP 다운로드

GitHub 페이지에서 `Code` → `Download ZIP` 을 누르고 압축을 풉니다.

### 요구 사항

- **Python 3.8 이상** (타입 힌트 `dict[str, int]` 등 사용)
- **의존성**: 데이터 수집 스크립트(`pkmnchamps_source.py`)만 `requests` 필요. 검색·검증 CLI는 표준 라이브러리만 씁니다.

```bash
# 데이터 갱신을 할 때만 필요
pip install requests
```

### 데이터가 이미 포함되어 있습니다

이 repo에는 이미 생성된 데이터가 포함되어 있어, 클론 직후 바로 검색·검증이 가능합니다:

| 경로 | 크기 | 내용 |
|---|---|---|
| `knowledge_base/` | 약 2MB | 238마리 메타데이터(`index.json`) + 포켓몬별 상세 문서 273개 + 공식 가이드 7종 |
| `data/pkmnchamps/` | 약 28MB | pkmnchamps 원본 DB (포켓몬/기술/도구/특성 + 사용률 파일 20종) |
| `champs_singles.json` | 약 4MB | 정제 데이터셋 (KB 입력용) |

데이터를 갱신할 필요가 없다면 아래 "데이터 갱신" 섹션은 건너뛰어도 됩니다.

---

## 사용 방법

### 방법 A: AI 코딩 도구에서 자연어로

이 repo를 AI 도구로 열면, 포켓몬 팀빌딩 관련 요청 시 스킬이 자동으로 동작합니다.

```
한카리아스 메가진화 중심 공격형 팀 짜줘
방어형 스톨 팀 추천해줘
트릭룸 팀인데 화강돌 넣고 싶어
비주류 위주로 팀 구성해줘
```

#### 지원 AI 도구 및 설정

이 repo는 여러 AI 코딩 도구를 지원합니다. **추가 설정 없이** repo를 열면 됩니다:

| 도구 | 인덱스 파일 | 비고 |
|---|---|---|
| **ZCode** | `.agents/skills/` (자동 인식) | 스킬을 직접 발견. `/champs-team-builder` 로도 호출 가능 |
| **Claude Code** | `CLAUDE.md` (자동 로드) | 스킬 경로를 안내하는 포인터 |
| **Cursor** | `.cursor/rules/` | 스킬 경로를 안내하는 규칙 (팀 파일·JSON·KB 편집 시 트리거) |
| **Gemini CLI** | `GEMINI.md` (자동 로드) | 스킬 경로를 안내하는 포인터 |
| **GitHub Copilot** | `.github/copilot-instructions.md` (자동 로드) | 스킬 경로를 안내하는 포인터 |
| **Windsurf** | `.windsurfrules` (자동 로드) | 스킬 경로를 안내하는 포인터 |
| **Codex / 기타** | `AGENTS.md` (자동 로드) | 스킬 경로를 안내하는 포인터 (다수 도구가 채택하는 사실상 표준) |

AGENTS.md 를 인식하지 못하는 도구(ChatGPT 웹, Gemini 앱 등 파일 접근이 없는 대화형 AI)라면
`.agents/skills/champs-team-builder/SKILL.md` 내용을 그대로 복사해 시스템 프롬프트/커스텀 지침에
붙여넣으면 동일하게 동작합니다.

> **작동 방식**: 스킬 본체는 `.agents/skills/champs-team-builder/SKILL.md` 하나입니다. 각 도구의 인덱스 파일은 "포켓몬 팀빌딩 작업 시 이 스킬을 읽어라" 라는 안내만 담고 있어, 어느 도구에서든 동일한 워크플로우가 동작합니다.

### 방법 B: 명령줄(CLI)에서 직접

AI 없이도 검색·검증 도구를 직접 쓸 수 있습니다.

#### 출력 언어 (`--lang`)

`kb_search.py`, `offmeta.py`, `validate_team.py`, `team_score.py`, `team_doc.py`, `meta_trend.py` 는
모두 `--lang ko|en|ja` 옵션을 지원합니다 (기본값 `ko`). 예:

```bash
python offmeta.py --rank 화강돌 --lang en
python team_score.py 팀/보유_트릭룸.json --lang ja
```

#### `kb_search.py` — 포켓몬/타입/팀 검색

```bash
# 포켓몬 한 마리 요약 (한국어/영문/showdown_id 모두 가능)
python kb_search.py 한카리아스
python kb_search.py Garchomp
python kb_search.py garchomp

# 타입별 목록 (종족합 순)
python kb_search.py --type 드래곤
python kb_search.py --type 강철

# 자주 같이 쓰이는 팀원
python kb_search.py --teammates 한카리아스

# 종족합 상위 10
python kb_search.py --strong

# 팀 약점 분석 (여러 마리)
python kb_search.py --team 한카리아스 리자몽 누리레느
```

#### `offmeta.py` — 비주류(오프메타) 발굴

사용률 순위(`pick_rank`) 기반으로 "순위는 낮지만 종족값·상성상 쓸 만한" 포켓몬을 찾습니다.

```bash
# 특정 포켓몬의 순위 + 실제 세팅(성격/SP/기술/도구/팀원)
python offmeta.py --rank 화강돌

# 120위 밖 + 종족합 500 이상
python offmeta.py --list --min-rank 120 --min-bst 500

# 타입 필터
python offmeta.py --list --min-rank 100 --type 물

# 합법인데 사용률 데이터에 없는 포켓몬 (완전 비주류)
python offmeta.py --unused

# 여러 마리 순위 비교
python offmeta.py --compare 한카리아스 화강돌 만마드
```

#### `validate_team.py` — 팀 검증 (**제안 전 필수**)

```bash
python validate_team.py 팀/보유_트릭룸.json
python validate_team.py 팀/보유_트릭룸.json --format doubles   # 더블 (6등록→4선발)
```

검사 항목: 현 레귤레이션 합법 여부 · 종족 조항(같은 종 2마리 금지) · 도구 중복 · SP 배분(스탯당 0~32, 합 66) · 메가스톤 보유 · 기술 습득 가능 · 기술 4개 이하 · **아키타입 불일치**(성격/SP가 역할에 부합하는지). 통과(exit 0) 전에는 팀을 제안하지 않습니다.

#### `team_doc.py` — 팀 문서 자동 생성

```bash
python team_doc.py 팀/보유_트릭룸.json            # 팀/<이름>.md 생성
python team_doc.py 팀/보유_트릭룸.json --update   # 기존 MD 수동 섹션 보존, 데이터만 갱신
python team_doc.py 팀/보유_트릭룸.json --format doubles
```

구성표·실수치·기술 채용률·약점 분석·속도 정렬을 자동 생성합니다. 전략·운영법은 `<!-- TEAM_DOC:manual -->` 마커 안에 남겨 직접 채웁니다. `--update` 시 마커 영역은 보존됩니다.

#### `team_score.py` — 팀 평가 (0~100점)

```bash
python team_score.py 팀/보유_트릭룸.json
python team_score.py 팀/보유_트릭룸.json --format doubles
```

방어 커버리지(35) / 속도 컨트롤(20) / 시너지(20) / 아키타입 일관(15) / 화력·내구(10) 로 채점해 등급(S~D)을 매깁니다. 팀의 강점·약점을 한눈에 볼 수 있어 추천 근거로 쓰기 좋습니다.

#### `meta_trend.py` — 메타 트렌드 분석 (다월 usage 비교)

```bash
python meta_trend.py                        # 현행 레귀 순위 변동
python meta_trend.py --rising               # 상승 Top 10
python meta_trend.py --falling              # 하락 Top 10
python meta_trend.py --pokemon 한카리아스    # 특정 포켓몬 월별 세팅 변화
python meta_trend.py --regulation m1        # 구 레귀(M1)
```

같은 레귀레이션 내 월별 사용률 순위 변동을 비교해 "이번 시즌 뜨는/지는 포켓몬"을 찾습니다.

---

## 팀 파일 포맷

팀은 JSON 배열로 표현합니다 (싱글 = 6마리). `팀/` 디렉토리의 예시를 참고하세요.

```json
[
  {
    "name": "한카리아스",
    "role": "물리 메인 어태커",
    "ability": "까칠한피부",
    "item": "기합의띠",
    "nature": "명랑",
    "sp": { "hp": 0, "atk": 32, "def": 0, "spa": 0, "spd": 2, "spe": 32 },
    "moves": ["지진", "역린", "칼춤", "스톤샤워"]
  }
]
```

- `sp` 키: `hp, atk, def, spa, spd, spe` (각 0~32, 합계 최대 66)
- `item`, `nature`, `moves`, `ability` 는 생략 가능하며, 있는 것만 검사합니다
- `role` 은 메모용으로 검증에 영향을 주지 않습니다

검증 통과한 팀은 같은 이름의 `.md` 파일로 정리합니다 (`팀/보유_트릭룸.md` 참고 — 세팅 표 + 선발 가이드 + 운영법 + 세팅 근거).

---

## 디렉토리 구조

```
├── .agents/skills/champs-team-builder/   # 스킬 본체 (모든 도구가 참조)
│   ├── SKILL.md                           # 역할·절차·출력 포맷·검증 규칙
│   └── references/data-pipeline.md        # 데이터 갱신 절차 (필요 시만)
├── .cursor/rules/                         # Cursor 규칙 (스킬 포인터)
├── .github/copilot-instructions.md        # GitHub Copilot용 인덱스 (스킬 포인터)
├── .windsurfrules                         # Windsurf용 인덱스 (스킬 포인터)
├── GEMINI.md                               # Gemini CLI용 인덱스 (스킬 포인터)
├── knowledge_base/                        # 검색 대상 (약 2MB)
│   ├── index.json                         # 메타데이터 (검색용)
│   ├── rules.md · type_chart.md · summary.md
│   ├── pokemon/*.md                       # 포켓몬별 상세 문서
│   └── guides/*.md                        # 공식 가이드 7종
├── data/pkmnchamps/                       # 원본 DB (약 28MB)
│   ├── pokemon.json · moves.json · items.json · abilities.json
│   └── usage_*.json                       # 사용률 파일 (레귤·월·포맷별)
├── 팀/                                    # 확정된 팀 세팅 (JSON + MD)
│
├── kb_search.py                           # 포켓몬/타입/팀 검색 CLI
├── offmeta.py                             # 비주류 발굴 CLI (요청 시만)
├── validate_team.py                       # 팀 검증 CLI (제안 전 필수)
├── team_doc.py                            # 팀 문서 자동 생성 CLI
├── team_score.py                          # 팀 평가 (0~100점) CLI
├── meta_trend.py                          # 메타 트렌드 분석 CLI
├── battle_rules.py                        # 챔피언스 규칙 + 타입상성 엔진
├── champs_singles.json                    # 정제 데이터셋 (싱글, learnset 포함)
├── champs_doubles.json                    # 정제 데이터셋 (더블)
│
├── pkmnchamps_source.py                   # ┐
├── champs_dataset.py                      # ├ 데이터 갱신 파이프라인
├── kb_builder.py                          # │ (데이터 바뀌었을 때만)
├── guides_builder.py                      # ┘
│
├── AGENTS.md                              # Codex/기타 도구용 인덱스 (스킬 포인터)
├── CLAUDE.md                              # Claude Code용 인덱스 (스킬 포인터)
└── README.md
```

---

## 데이터 갱신 (필요할 때만)

pkmnchamps.com 의 새 시즌 데이터가 나왔을 때. **이미 포함된 데이터로 충분하다면 이 섹션은 건너뛰세요.** 절차는 `.agents/skills/champs-team-builder/references/data-pipeline.md` 에 상세히 있습니다.

```bash
pip install requests   # 아직 안 했다면

# 1) 원본 DB + 사용률 다운로드
python pkmnchamps_source.py --all

# 2) 정제 데이터셋 생성 (싱글+더블, learnset 포함)
python champs_dataset.py --both

# 3) 지식베이스 재빌드
python kb_builder.py --data champs_singles.json --out knowledge_base
python guides_builder.py
```

첫 실행은 HTTP 호출 때문에 수 분 소요됩니다.

---

## 챔피언스 핵심 차이점 (메인라인 포켓몬과)

이 스킬은 챔피언스 실제 규칙만 따릅니다. 메인라인 포켓몬 상식을 덧붙이지 않습니다 — 수치가 다릅니다:

| 항목 | 챔피언스 | 메인라인 |
|---|---|---|
| 개체 육성 | **IV 31 고정 + SP 슬라이더** (스탯당 0~32, 합 66) | EV 252 / 합 510 |
| 싱글 포맷 | **6마리 등록 → 3마리 선발** | 6마리 풀 교대전 |
| 성격 | **변경 가능** (개체 다시 안 구해도 됨) | 고정 |
| 마비 행동불가 | **12.5%** | 25% |
| 수면 | **최대 2턴** | 2~4턴 |
| 보호 PP | **8** | 16 |
| 특수 메커니즘 | **메가진화만 구현** (테라스탈/Z/다이맥스는 향후) | 여러 시스템 |

자세한 규칙은 `knowledge_base/rules.md` 를 참조하세요.

---

## 라이선스

코드는 MIT 라이선스입니다 ([LICENSE](LICENSE) 참고). 데이터 출처는 [pkmnchamps.com](https://championsbattledata.com)이며, 재배포 시 원 출처 표기를 권장합니다.
