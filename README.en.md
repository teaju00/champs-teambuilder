# Pokémon Champions Team-Building Skill

**[한국어](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

**A team-recommendation skill for Pokémon Champions (single battles).** It combines usage-rate data from [pkmnchamps.com](https://championsbattledata.com) with a local knowledge base to propose a 6-Pokémon roster and guarantees legality with a validation script. Works with ZCode, Claude Code, Cursor, Gemini CLI, GitHub Copilot, Windsurf, Codex, and virtually any other AI coding tool.

> The single source of truth for the skill's rules is `.agents/skills/champs-team-builder/SKILL.md`. Each tool's index file (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules/`) is only a thin pointer to that skill.

## What does it do?

When a natural-language request like "build me a physical-attacker team centered on Garchomp" comes in:

1. Search the knowledge base / usage stats with `kb_search.py` / `offmeta.py`
2. Build a 6-Pokémon team, weighing weakness coverage and synergy
3. Auto-validate legality, SP allocation, and archetype consistency with `validate_team.py` (**no team is proposed until this passes**)
4. Write up the set (nature/SP/item/moves) and lead-selection guide

---

## Download & Install

### Option 1: Clone with Git

```bash
git clone https://github.com/<your-username>/champs-teambuilder.git
cd champs-teambuilder
```

### Option 2: Download ZIP

On the GitHub page, click `Code` → `Download ZIP` and extract it.

### Requirements

- **Python 3.8+** (uses type hints like `dict[str, int]`)
- **Dependencies**: only the data-collection script (`pkmnchamps_source.py`) needs `requests`. The search/validation CLIs use only the standard library.

```bash
# Only needed if you want to refresh the data
pip install requests
```

### The data is already included

This repo ships with pre-built data, so search and validation work right after cloning:

| Path | Size | Contents |
|---|---|---|
| `knowledge_base/` | ~2 MB | Metadata for 238 Pokémon (`index.json`) + 273 per-Pokémon detail docs + 7 official guides |
| `data/pkmnchamps/` | ~28 MB | Raw pkmnchamps DB (Pokémon/moves/items/abilities + 20 usage files) |
| `champs_singles.json` | ~4 MB | Curated dataset (feeds the knowledge base) |

If you don't need to refresh the data, you can skip the "Refreshing the data" section below.

---

## Usage

### Option A: Natural language in an AI coding tool

Open this repo in an AI tool and the skill kicks in automatically on any Pokémon team-building request.

```
Build me a physical-attacker team centered on Mega Garchomp
Recommend a defensive stall team
I want a Trick Room team with Gigalith in it
Build a team focused on off-meta picks
```

#### Supported AI tools & setup

This repo supports several AI coding tools. **No extra setup** — just open the repo:

| Tool | Index file | Notes |
|---|---|---|
| **ZCode** | `.agents/skills/` (auto-discovered) | Discovers the skill directly. Can also be invoked with `/champs-team-builder` |
| **Claude Code** | `CLAUDE.md` (auto-loaded) | Pointer to the skill path |
| **Cursor** | `.cursor/rules/` | Rule that points to the skill (triggers when editing team files/JSON/KB) |
| **Gemini CLI** | `GEMINI.md` (auto-loaded) | Pointer to the skill path |
| **GitHub Copilot** | `.github/copilot-instructions.md` (auto-loaded) | Pointer to the skill path |
| **Windsurf** | `.windsurfrules` (auto-loaded) | Pointer to the skill path |
| **Codex / others** | `AGENTS.md` (auto-loaded) | Pointer to the skill path (a de-facto standard adopted by many tools) |

For conversational AI without file access (e.g. the ChatGPT or Gemini web apps), just paste the
contents of `.agents/skills/champs-team-builder/SKILL.md` into the system prompt / custom
instructions — it works the same way.

> **How it works**: the skill itself lives in a single place, `.agents/skills/champs-team-builder/SKILL.md`. Each tool's index file just says "read this skill before doing Pokémon team-building work," so the same workflow runs no matter which tool you use.

### Option B: Directly from the command line

You can use the search/validation tools directly without an AI.

#### Output language (`--lang`)

`kb_search.py`, `offmeta.py`, `validate_team.py`, `team_score.py`, `team_doc.py`, and `meta_trend.py`
all support `--lang ko|en|ja` (default `ko`). Example:

```bash
python offmeta.py --rank 화강돌 --lang en
python team_score.py 팀/보유_트릭룸.json --lang ja
```

#### `kb_search.py` — Pokémon/type/team search

```bash
# Summary for one Pokémon (Korean name, English name, or showdown_id all work)
python kb_search.py 한카리아스
python kb_search.py Garchomp
python kb_search.py garchomp

# List by type (sorted by BST)
python kb_search.py --type 드래곤
python kb_search.py --type 강철

# Frequent teammates
python kb_search.py --teammates 한카리아스

# Top 10 by BST
python kb_search.py --strong

# Team weakness analysis (multiple Pokémon)
python kb_search.py --team 한카리아스 리자몽 누리레느
```

#### `offmeta.py` — Off-meta discovery

Using pick-rank usage data, finds Pokémon that rank low but are still viable on stats/typing.

```bash
# A specific Pokémon's rank + real-world set (nature/SP/moves/item/teammates)
python offmeta.py --rank 화강돌

# Outside top 120 + BST 500+
python offmeta.py --list --min-rank 120 --min-bst 500

# Type filter
python offmeta.py --list --min-rank 100 --type 물

# Legal Pokémon with no usage data at all (true off-meta)
python offmeta.py --unused

# Compare ranks across several Pokémon
python offmeta.py --compare 한카리아스 화강돌 만마드
```

#### `validate_team.py` — Team validation (**required before proposing**)

```bash
python validate_team.py 팀/보유_트릭룸.json
python validate_team.py 팀/보유_트릭룸.json --format doubles   # doubles (6 registered → 4 brought)
```

Checks: current-regulation legality · species clause (no two of the same species) · item duplication · SP allocation (0–32 per stat, 66 total) · mega-stone holders · move learnability · move count ≤ 4 · **archetype mismatch** (whether nature/SP fit the intended role). No team is proposed until this exits 0.

#### `team_doc.py` — Auto-generate team docs

```bash
python team_doc.py 팀/보유_트릭룸.json            # generates 팀/<name>.md
python team_doc.py 팀/보유_트릭룸.json --update   # keep existing manual sections, refresh data only
python team_doc.py 팀/보유_트릭룸.json --format doubles
```

Auto-generates the roster table, real stats, move usage rates, weakness analysis, and speed ordering. Strategy/play notes are left inside `<!-- TEAM_DOC:manual -->` markers for you to fill in by hand. `--update` preserves that marked region.

#### `team_score.py` — Team scoring (0–100)

```bash
python team_score.py 팀/보유_트릭룸.json
python team_score.py 팀/보유_트릭룸.json --format doubles
```

Scores defensive coverage (35) / speed control (20) / synergy (20) / archetype consistency (15) / firepower-durability balance (10), and assigns a grade (S–D). A quick way to see a team's strengths/weaknesses and back up a recommendation.

#### `meta_trend.py` — Meta trend analysis (multi-month usage comparison)

```bash
python meta_trend.py                        # rank changes for the current regulation
python meta_trend.py --rising               # top 10 risers
python meta_trend.py --falling              # top 10 fallers
python meta_trend.py --pokemon 한카리아스    # a specific Pokémon's monthly set changes
python meta_trend.py --regulation m1        # older regulation (M1)
```

Compares monthly usage-rank changes within the same regulation to find "what's rising/falling this season."

---

## Team file format

A team is a JSON array (6 Pokémon for singles). See the examples in the `팀/` directory.

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

- `sp` keys: `hp, atk, def, spa, spd, spe` (each 0–32, 66 total max)
- `item`, `nature`, `moves`, `ability` are optional — only what's present gets checked
- `role` is a note field and doesn't affect validation

A team that passes validation is written up as a `.md` file of the same name (see `팀/보유_트릭룸.md` — set table + lead-selection guide + play notes + rationale for the set).

---

## Directory structure

```
├── .agents/skills/champs-team-builder/   # the skill itself (referenced by every tool)
│   ├── SKILL.md                           # role, procedure, output format, validation rules
│   └── references/data-pipeline.md        # data-refresh procedure (only needed occasionally)
├── .cursor/rules/                         # Cursor rule (skill pointer)
├── .github/copilot-instructions.md        # index for GitHub Copilot (skill pointer)
├── .windsurfrules                         # index for Windsurf (skill pointer)
├── GEMINI.md                               # index for Gemini CLI (skill pointer)
├── knowledge_base/                        # search target (~2 MB)
│   ├── index.json                         # metadata (for search)
│   ├── rules.md · type_chart.md · summary.md
│   ├── pokemon/*.md                       # per-Pokémon detail docs
│   └── guides/*.md                        # 7 official guides
├── data/pkmnchamps/                       # raw DB (~28 MB)
│   ├── pokemon.json · moves.json · items.json · abilities.json
│   └── usage_*.json                       # usage files (by regulation/month/format)
├── 팀/                                    # finalized team sets (JSON + MD)
│
├── kb_search.py                           # Pokémon/type/team search CLI
├── offmeta.py                             # off-meta discovery CLI (on request only)
├── validate_team.py                       # team validation CLI (required before proposing)
├── team_doc.py                            # auto-generate team docs CLI
├── team_score.py                          # team scoring (0–100) CLI
├── meta_trend.py                          # meta trend analysis CLI
├── battle_rules.py                        # Champions rules + type-matchup engine
├── champs_singles.json                    # curated dataset (singles, includes learnset)
├── champs_doubles.json                    # curated dataset (doubles)
│
├── pkmnchamps_source.py                   # ┐
├── champs_dataset.py                      # ├ data-refresh pipeline
├── kb_builder.py                          # │ (only needed when the data changes)
├── guides_builder.py                      # ┘
│
├── AGENTS.md                              # index for Codex/other tools (skill pointer)
├── CLAUDE.md                              # index for Claude Code (skill pointer)
└── README.md
```

---

## Refreshing the data (only when needed)

For when a new season's data drops on pkmnchamps.com. **If the bundled data is already enough, skip this section.** The full procedure is in `.agents/skills/champs-team-builder/references/data-pipeline.md`.

```bash
pip install requests   # if you haven't already

# 1) Download the raw DB + usage data
python pkmnchamps_source.py --all

# 2) Build the curated dataset (singles+doubles, with learnset)
python champs_dataset.py --both

# 3) Rebuild the knowledge base
python kb_builder.py --data champs_singles.json --out knowledge_base
python guides_builder.py
```

The first run takes a few minutes due to the HTTP calls involved.

---

## Key differences from mainline Pokémon

This skill follows Champions' actual rules only — it doesn't carry over mainline conventions, since the numbers differ:

| Aspect | Champions | Mainline |
|---|---|---|
| Individual growth | **IVs fixed at 31 + SP slider** (0–32 per stat, 66 total) | EVs, 252 per stat / 510 total |
| Singles format | **6 registered → 3 brought** | Full 6-Pokémon rotation |
| Nature | **Changeable** (no need to re-obtain the Pokémon) | Fixed |
| Paralysis full-para chance | **12.5%** | 25% |
| Sleep | **Max 2 turns** | 2–4 turns |
| Protect PP | **8** | 16 |
| Special mechanics | **Only Mega Evolution implemented** (Terastallization/Z-Moves/Dynamax planned) | Multiple systems |

See `knowledge_base/rules.md` for detailed rules.

---

## License

The code is MIT licensed (see [LICENSE](LICENSE)).

Data under `data/pkmnchamps/`, `champs_singles.json`, `champs_doubles.json`, and `knowledge_base/`
comes from [Pokemon Champions Battle Data](https://championsbattledata.com/)
([license](https://championsbattledata.com/license.html)). That site permits use for
"personal, educational, and competitive analysis use" and requires that anyone sharing or reusing
the data **credit Pokemon Champions Battle Data and link to https://championsbattledata.com/** —
this project follows that requirement. Pokemon's own intellectual property (Nintendo/Game
Freak/Creatures Inc.) is separate from this license, and this project is not affiliated with them.
