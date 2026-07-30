# CLAUDE.md

이 프로젝트는 **포켓몬 챔피언스(Pokémon Champions) 싱글/더블배틀 팀 추천 스킬** 이다.
역할 정의와 지식베이스 사용 규칙은 스킬로 옮겨졌다:

`.agents/skills/champs-team-builder/SKILL.md`

포켓몬 팀빌딩 작업 시 **반드시 해당 스킬을 먼저 읽을 것**. SKILL.md 가 진실의 원천이며,
모든 역할·절차·출력 포맷·검증 규칙·CLI 사용법이 거기에 있다.

## 이 프로젝트에서 쓰지 않는 것

- 데이터 재수집(`pkmnchamps_source.py --all`)은 **사용자가 명시적으로 요청할 때만** 실행한다.
  HTTP 호출이 수백 번 발생한다. 팀 추천에는 이미 만들어진 `knowledge_base/`·`champs_*.json` 만 쓰면 충분.
- `cache/pokeapi_cache.json` 은 약 95MB다 (구 파이프라인 잔재, 현재 미사용). 절대 Read 로 통째로 읽지 말 것.
