# ポケモンチャンピオンズ チームビルディングスキル

**[한국어](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

**ポケモンチャンピオンズ(Pokémon Champions)シングルバトルのチーム推薦スキル。** [pkmnchamps.com](https://championsbattledata.com) の使用率データとローカルのナレッジベースを組み合わせ、6匹登録チームを提案し、検証スクリプトで合法性を保証します。ZCode、Claude Code、Cursor、Gemini CLI、GitHub Copilot、Windsurf、Codex など、ほぼすべてのAIコーディングツールで使用できます。

> スキルルールの信頼できる情報源は `.agents/skills/champs-team-builder/SKILL.md` です。各AIツールのインデックスファイル(`AGENTS.md`、`CLAUDE.md`、`.cursor/rules/`)は、このスキルを指す薄いポインターに過ぎません。

## 何をするツール?

「ガブリアス中心の物理アタッカーチームを組んで」のような自然言語のリクエストが来たら:

1. `kb_search.py` / `offmeta.py` でナレッジベース・使用率統計を検索
2. 弱点分析とシナジーを考慮して6匹のチームを構成
3. `validate_team.py` で合法性・SP配分・アーキタイプの整合性を自動検証(**通過するまでは提案しません**)
4. 調整案(性格/SP/持ち物/技)と選出ガイドをまとめる

---

## ダウンロードとインストール

### 方法1: Gitでクローン

```bash
git clone https://github.com/<ユーザー名>/champs-teambuilder.git
cd champs-teambuilder
```

### 方法2: ZIPダウンロード

GitHubのページで `Code` → `Download ZIP` を押して解凍します。

### 必要環境

- **Python 3.8以上**(`dict[str, int]` などの型ヒントを使用)
- **依存パッケージ**: データ収集スクリプト(`pkmnchamps_source.py`)のみ `requests` が必要。検索・検証CLIは標準ライブラリのみで動作します。

```bash
# データ更新をする場合のみ必要
pip install requests
```

### データは既に同梱されています

このリポジトリには生成済みのデータが同梱されているため、クローン直後からすぐに検索・検証が可能です:

| パス | サイズ | 内容 |
|---|---|---|
| `knowledge_base/` | 約2MB | 238匹分のメタデータ(`index.json`)+ ポケモン別詳細ドキュメント273件 + 公式ガイド7種 |
| `data/pkmnchamps/` | 約28MB | pkmnchamps 原本DB(ポケモン/技/道具/特性 + 使用率ファイル20種) |
| `champs_singles.json` | 約4MB | 整形済みデータセット(KBの入力用) |

データを更新する必要がなければ、下記の「データ更新」セクションはスキップして構いません。

---

## 使い方

### 方法A: AIコーディングツールで自然言語

このリポジトリをAIツールで開くと、ポケモンチームビルディング関連のリクエスト時にスキルが自動で動作します。

```
ガブリアスのメガシンカ中心の物理アタッカーチームを組んで
受け・積みチームを推薦して
トリックルームチームでゴロンダを入れたい
オフメタ中心でチームを組んで
```

#### 対応AIツールと設定

このリポジトリは複数のAIコーディングツールに対応しています。**追加設定は不要**で、リポジトリを開くだけです:

| ツール | インデックスファイル | 備考 |
|---|---|---|
| **ZCode** | `.agents/skills/`(自動認識) | スキルを直接発見。`/champs-team-builder` でも呼び出し可能 |
| **Claude Code** | `CLAUDE.md`(自動読み込み) | スキルの場所を案内するポインター |
| **Cursor** | `.cursor/rules/` | スキルの場所を案内するルール(チームファイル・JSON・KB編集時にトリガー) |
| **Gemini CLI** | `GEMINI.md`(自動読み込み) | スキルの場所を案内するポインター |
| **GitHub Copilot** | `.github/copilot-instructions.md`(自動読み込み) | スキルの場所を案内するポインター |
| **Windsurf** | `.windsurfrules`(自動読み込み) | スキルの場所を案内するポインター |
| **Codex / その他** | `AGENTS.md`(自動読み込み) | スキルの場所を案内するポインター(多くのツールが採用する事実上の標準) |

ファイルアクセスのない対話型AI(ChatGPTやGeminiのWeb版など)の場合は、
`.agents/skills/champs-team-builder/SKILL.md` の内容をそのままシステムプロンプト/カスタム指示に
貼り付ければ同様に動作します。

### claude.ai(Web/アプリ)で本物の Agent Skill として使う

上記はすべて、リポジトリを開いて Bash でローカルファイルを読めるコーディングエージェント
専用です。claude.ai(Pro/Max/Team/Enterprise、コード実行有効)には、リポジトリへの
アクセスなしで動作する別の **Agent Skill アップロード**機能があります —
SKILL.md と必要なスクリプト・データを1つの zip にまとめてアップロードすれば、
リクエスト内容に応じて自動的にトリガーされます。

```bash
python build_claude_skill.py   # dist/champs-team-builder.zip を生成
```

この zip には SKILL.md、9個のランタイム用 CLI スクリプト、`knowledge_base/`、
`champs_singles.json`/`champs_doubles.json`、`data/pkmnchamps/` が1つの
self-contained なフォルダにまとめられます(スクリプトは自分自身のファイル位置基準で
データを探すため、作業ディレクトリに関係なく動作します)。claude.ai の
**Settings → Features → Skills** でこの zip をアップロードしてください。
データ再収集パイプライン(`pkmnchamps_source.py` など)はネットワークが必要で
サンドボックス環境に合わないため、このパッケージには含まれていません —
最新データが必要な場合はリポジトリ側で更新してから zip を作り直してください。

> **仕組み**: スキル本体は `.agents/skills/champs-team-builder/SKILL.md` の一つだけです。各ツールのインデックスファイルは「ポケモンチームビルディング作業時はこのスキルを読め」という案内だけを持っているため、どのツールでも同じワークフローが動作します。

### 方法B: コマンドラインから直接

AIなしでも検索・検証ツールを直接使用できます。

#### 出力言語(`--lang`)

`kb_search.py`、`offmeta.py`、`validate_team.py`、`team_score.py`、`team_doc.py`、`meta_trend.py` は
すべて `--lang ko|en|ja` オプションに対応しています(デフォルトは `ko`)。例:

```bash
python offmeta.py --rank 화강돌 --lang en
python team_score.py 팀/보유_트릭룸.json --lang ja
```

#### `kb_search.py` — ポケモン/タイプ/チーム検索

```bash
# ポケモン1匹の要約(韓国語名・英語名・showdown_id いずれも可)
python kb_search.py 한카리아스
python kb_search.py Garchomp
python kb_search.py garchomp

# タイプ別リスト(種族値合計順)
python kb_search.py --type 드래곤
python kb_search.py --type 강철

# よく一緒に使われる相棒
python kb_search.py --teammates 한카리아스

# 種族値合計トップ10
python kb_search.py --strong

# チーム弱点分析(複数匹)
python kb_search.py --team 한카리아스 리자몽 누리레느
```

#### `offmeta.py` — オフメタ(非主流)発掘

使用率順位(`pick_rank`)を基準に、「順位は低いが種族値・タイプ相性的に使える」ポケモンを探します。

```bash
# 特定ポケモンの順位 + 実際の調整(性格/SP/技/道具/相棒)
python offmeta.py --rank 화강돌

# 120位圏外 + 種族値合計500以上
python offmeta.py --list --min-rank 120 --min-bst 500

# タイプフィルター
python offmeta.py --list --min-rank 100 --type 물

# 合法だが使用率データにないポケモン(完全なオフメタ)
python offmeta.py --unused

# 複数匹の順位比較
python offmeta.py --compare 한카리아스 화강돌 만마드
```

#### `validate_team.py` — チーム検証(**提案前に必須**)

```bash
python validate_team.py 팀/보유_트릭룸.json
python validate_team.py 팀/보유_트릭룸.json --format doubles   # ダブル(6登録→4選出)
```

検査項目: 現行レギュレーションの合法性 · 種族条項(同じ種2匹禁止) · 道具の重複禁止 · SP配分(ステータスごと0~32、合計66) · メガストーン所持 · 技の習得可否 · 技は4つ以下 · **アーキタイプの不一致**(性格/SPが役割に合っているか)。通過(exit 0)するまではチームを提案しません。

#### `team_doc.py` — チームドキュメント自動生成

```bash
python team_doc.py 팀/보유_트릭룸.json            # 팀/<名前>.md を生成
python team_doc.py 팀/보유_트릭룸.json --update   # 既存MDの手動セクションを保持し、データのみ更新
python team_doc.py 팀/보유_트릭룸.json --format doubles
```

構成表・実数値・技採用率・弱点分析・素早さ順を自動生成します。戦略・運用方法は `<!-- TEAM_DOC:manual -->` マーカー内に残しておき、手動で記入します。`--update` 時、マーカー領域は保持されます。

#### `team_score.py` — チーム評価(0~100点)

```bash
python team_score.py 팀/보유_트릭룸.json
python team_score.py 팀/보유_트릭룸.json --format doubles
```

防御カバレッジ(35)/ すばやさ調整(20)/ シナジー(20)/ アーキタイプ一貫性(15)/ 火力・耐久(10)で採点し、ランク(S~D)を付けます。チームの強み・弱みが一目でわかり、推薦の根拠として使いやすいです。

#### `meta_trend.py` — メタトレンド分析(複数月の使用率比較)

```bash
python meta_trend.py                        # 現行レギュ順位変動
python meta_trend.py --rising               # 上昇トップ10
python meta_trend.py --falling              # 下降トップ10
python meta_trend.py --pokemon 한카리아스    # 特定ポケモンの月別調整変化
python meta_trend.py --regulation m1        # 旧レギュ(M1)
```

同じレギュレーション内での月別使用率順位の変動を比較し、「今シーズン伸びている/落ちているポケモン」を見つけます。

---

## チームファイル形式

チームはJSON配列で表現します(シングル=6匹)。`팀/` ディレクトリのサンプルを参考にしてください。

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

- `sp` キー: `hp, atk, def, spa, spd, spe`(それぞれ0~32、合計最大66)
- `item`、`nature`、`moves`、`ability` は省略可能で、存在するものだけ検査します
- `role` はメモ用で検証には影響しません

検証を通過したチームは、同じ名前の `.md` ファイルにまとめます(`팀/보유_트릭룸.md` 参照 — 調整表 + 選出ガイド + 運用方法 + 調整の根拠)。

---

## ディレクトリ構成

```
├── .agents/skills/champs-team-builder/   # スキル本体(全ツールが参照)
│   ├── SKILL.md                           # 役割・手順・出力フォーマット・検証ルール
│   └── references/data-pipeline.md        # データ更新手順(必要な時のみ)
├── .cursor/rules/                         # Cursorルール(スキルへのポインター)
├── .github/copilot-instructions.md        # GitHub Copilot用インデックス(スキルへのポインター)
├── .windsurfrules                         # Windsurf用インデックス(スキルへのポインター)
├── GEMINI.md                               # Gemini CLI用インデックス(スキルへのポインター)
├── knowledge_base/                        # 検索対象(約2MB)
│   ├── index.json                         # メタデータ(検索用)
│   ├── rules.md · type_chart.md · summary.md
│   ├── pokemon/*.md                       # ポケモン別詳細ドキュメント
│   └── guides/*.md                        # 公式ガイド7種
├── data/pkmnchamps/                       # 原本DB(約28MB)
│   ├── pokemon.json · moves.json · items.json · abilities.json
│   └── usage_*.json                       # 使用率ファイル(レギュ・月・フォーマット別)
├── 팀/                                    # 確定したチーム調整(JSON + MD)
│
├── kb_search.py                           # ポケモン/タイプ/チーム検索CLI
├── offmeta.py                             # オフメタ発掘CLI(リクエスト時のみ)
├── validate_team.py                       # チーム検証CLI(提案前に必須)
├── team_doc.py                            # チームドキュメント自動生成CLI
├── team_score.py                          # チーム評価(0~100点)CLI
├── meta_trend.py                          # メタトレンド分析CLI
├── battle_rules.py                        # チャンピオンズのルール + タイプ相性エンジン
├── champs_singles.json                    # 整形済みデータセット(シングル、learnset含む)
├── champs_doubles.json                    # 整形済みデータセット(ダブル)
│
├── build_claude_skill.py                  # claude.ai用の携帯可能な Agent Skill zip をビルド
│
├── pkmnchamps_source.py                   # ┐
├── champs_dataset.py                      # ├ データ更新パイプライン
├── kb_builder.py                          # │ (データが変わった時のみ)
├── guides_builder.py                      # ┘
│
├── AGENTS.md                              # Codex/その他ツール用インデックス(スキルへのポインター)
├── CLAUDE.md                              # Claude Code用インデックス(スキルへのポインター)
└── README.md
```

---

## データ更新(必要な時のみ)

pkmnchamps.com で新シーズンのデータが出た時用。**同梱データで十分ならこのセクションはスキップしてください。** 手順は `.agents/skills/champs-team-builder/references/data-pipeline.md` に詳しく記載されています。

```bash
pip install requests   # まだの場合

# 1) 原本DB + 使用率データのダウンロード
python pkmnchamps_source.py --all

# 2) 整形済みデータセットの生成(シングル+ダブル、learnset含む)
python champs_dataset.py --both

# 3) ナレッジベースの再構築
python kb_builder.py --data champs_singles.json --out knowledge_base
python guides_builder.py
```

初回実行はHTTP通信のため数分かかります。

---

## チャンピオンズの本家との主な違い

このスキルはチャンピオンズの実際のルールのみに従います。本家ポケモンの常識は持ち込みません — 数値が異なるためです:

| 項目 | チャンピオンズ | 本家 |
|---|---|---|
| 個体育成 | **個体値31固定 + SPスライダー**(ステータスごと0~32、合計66) | 努力値252 / 合計510 |
| シングルフォーマット | **6匹登録 → 3匹選出** | 6匹総当たり |
| 性格 | **変更可能**(個体を取り直す必要なし) | 固定 |
| まひで行動不能 | **12.5%** | 25% |
| ねむり | **最大2ターン** | 2~4ターン |
| まもるのPP | **8** | 16 |
| 特殊システム | **メガシンカのみ実装**(テラスタル/Z技/ダイマックスは今後) | 複数のシステム |

詳しいルールは `knowledge_base/rules.md` を参照してください。

---

## ライセンス

コードは MIT ライセンスです([LICENSE](LICENSE) 参照)。

`data/pkmnchamps/`、`champs_singles.json`、`champs_doubles.json`、`knowledge_base/` のデータは
[Pokemon Champions Battle Data](https://championsbattledata.com/)
([license](https://championsbattledata.com/license.html)) から取得しています。同サイトは
「personal, educational, and competitive analysis use」目的での利用を許可しており、共有・再利用時には
**Pokemon Champions Battle Data を出典として明記し、https://championsbattledata.com/ にリンク**する
ことを求めています。本プロジェクトはこの条件に従います。ポケモン自体の知的財産権(任天堂/
ゲームフリーク/クリーチャーズ)はこのライセンスとは別であり、本プロジェクトはそれらと無関係です。
