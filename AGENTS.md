# AGENTS.md

이 프로젝트는 **포켓몬 챔피언스(Pokémon Champions) 싱글/더블배틀 팀 추천 스킬** 이다.

포켓몬 팀빌딩 관련 작업(팀 구성, 세팅 추천, 약점 분석, 비주류 발굴, 팀 문서 생성, 평가)을
요청받으면 **반드시 먼저 스킬 문서를 읽어라**:

```
.agents/skills/champs-team-builder/SKILL.md
```

이 파일에 역할·추천 절차·출력 포맷·검증 규칙·CLI 도구 사용법이 전부 있다.
SKILL.md 가 진실의 원천이며, 이 AGENTS.md 와 CLAUDE.md / .cursor/rules/ 는
모두 그 스킬을 가리키는 포인터다.

## 핵심 규칙 (요약 — 상세는 SKILL.md)

- **챔피언스 실제 규칙만** 사용. 메인라인 포켓몬 상식을 덧붙이지 말 것 (IV/SP/상태이상 수치가 다름).
- 팀 제안 전 **반드시 `python validate_team.py 팀/<이름>.json`** 을 통과시킬 것 (exit 0).
- 응답은 **한국어**. 사용률(percentage)을 근거로 제시.
- 데이터 없는 조합/세팅은 "데이터에 없음"이라 솔직히 말할 것.

## 빠른 CLI 참조

```bash
python kb_search.py 한카리아스                      # 포켓몬 검색
python offmeta.py --rank 화강돌                      # 비주류 순위 (사용자 요청 시만)
python validate_team.py 팀/보유_트릭룸.json           # 팀 검증 (제안 전 필수)
python team_doc.py 팀/보유_트릭룸.json               # 팀 문서 자동 생성
python team_score.py 팀/보유_트릭룸.json             # 팀 평가 (0~100점)
python meta_trend.py --rising                       # 메타 순위 상승 Top
```
