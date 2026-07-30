# 데이터 파이프라인 & 원본 데이터

지식베이스 재생성 절차. **사용자가 명시적으로 "데이터 갱신해줘" 라고 요청할 때만** 실행한다.
팀 추천에는 이미 만들어진 `knowledge_base/` 만 쓰면 충분하다.

## 재생성 명령

```bash
# 현행 파이프라인 (pkmnchamps 기반 — 한국어 원문 + 레귤레이션 + 사용률 순위)
python pkmnchamps_source.py --all      # 원본 DB 7종 + 가이드 i18n + 사용률 20조합
python champs_dataset.py --both        # -> champs_singles.json + champs_doubles.json
                                        #    (learnset = 원종 습득기 ∪ 모든 usage 관측 기술 포함)
python kb_builder.py --data champs_singles.json --out knowledge_base
python guides_builder.py               # -> knowledge_base/guides/*.md
```

`champs_dataset.py` 옵션:
- `--format Singles|Doubles` — 한쪽만 빌드 (기본 Singles)
- `--both` — 싱글+더블 동시 빌드 (현행 M-B 기준)
- `--usage <파일명>` — 사용률 파일 지정 (생략 시 포맷별 현행 M-B 자동 선택)

데이터셋의 `learnset` 필드는 원종 습득기 ∪ 모든 usage 파일에서 관측된 기술(폼별)을 합친 것이다.
`validate_team.py` 가 이 필드만 읽어 기술 합법 판정을 하므로, 과거처럼 `data/pkmnchamps/` 를
직접 훑지 않아도 된다.

## `pkmnchamps_source.py` 주의사항 (하드코딩이 아니라 사이트 구조상 필요)

- 두 엔드포인트 모두 **`Referer` 헤더 없으면 403**. UA 만으로는 안 통한다.
- `.js` 응답은 charset 을 안 주므로 `r.content.decode("utf-8")` 로 받아야 한글이 안 깨진다.
- 청크 파일 해시는 배포마다 바뀌므로 HTML 에서 자동 탐색한다 (하드코딩 금지).
- i18n 청크에 ko/en/ja 가 다 들어있어 한글 값을 골라내야 한다.

## `data/pkmnchamps/` 원본 파일 구조

`knowledge_base/` 보다 **더 정확하고 넓은** 원본. 애매하면 이쪽을 본다.

| 파일 | 내용 | 여기에만 있는 것 |
|---|---|---|
| `pokemon.json` | 1025마리 | **`regulationMA`/`regulationMB` = 레귤레이션 합법 여부**, 전체 습득기, `realStats`, `bulk` |
| `moves.json` | 기술 822개 (available 742) | **`priority`(선공도)**, `targetKo`(범위), `flags`(접촉/펀치/소리/파동/춤), `meta`(풀죽음률·흡수·연속타), `descKo` |
| `items.json` | 도구 347개 | **`effectKo`(한국어 효과)**, 레귤레이션 합법 여부 |
| `abilities.json` | 특성 305개 | **`descKo`**, `affectsDamage` |
| `natures.json` | 성격 25종 | `up`/`down` |
| `usage_<reg>_<month>_<format>.json` | 사용률 20조합 | **`pick_rank` = 전체 사용률 순위** (비주류 발굴용) |

기본 사용률 파일: `usage_reg_mb_2026-07_singles.json` (M-B, 2026-07, 싱글, 230마리)

**주의**: `usage` 에는 같은 `pokemon_id` 가 폼별로 여러 번 나온다(로토무 6폼 등).
키는 `(pokemon_id, region_form, mega_form)` 다.
