# Story Workbench

`Story Workbench` は、LLM と一緒に物語制作を進めるためのファイルベースのプロジェクト土台です。
設定、現在状態、物語進行を分離して保持し、長い話でも一つの巨大なメモに崩れないようにします。

英語版: [README.md](README.md)

## この構成にしている理由

- `data/canon/` は固定寄りの世界設定を保存します。
- `data/ideas/` はまだ固まりきっていない案や保留案を退避します。
- `data/state/` は現在の状況やシーン時点の真実を保存します。
  人物や世界だけでなく、追跡したい物品の snapshot もここに置きます。
- `data/plot/` は未回収要素、章構成、進行中の物語課題を保存します。
- `data/timeline/` は出来事の時系列を保存し、因果関係を明示します。
- `ops/checkpoints/` と `ops/handoff/` は、確定事項と保留事項をセッションをまたいで維持します。
- `tools/story.py` は、検証、検索、文脈生成、ドラフト補助、引き継ぎ更新の入口です。

## プロジェクト境界

1つの Story Workbench workspace は、1つの物語プロジェクトを扱う前提です。無関係な複数作品を同じ
`data/` に混ぜたり、全 record に `project_id` を付けて分岐させたりしないでください。`context`、
`audit`、`checkpoint`、`handoff` は、全 record が同じ物語に属する前提で動きます。別作品は別リポジトリ、
または別 workspace として作ります。

## 基本的な作業フロー

1. `python3 tools/story.py validate` を実行する
2. `list`、`show`、`search`、`context` で必要情報を確認する
3. シーンの整合性が重要なら `python3 tools/story.py audit <scene-id>` を実行する
4. `python3 tools/story.py draft <scene-id>` で執筆用の足場を作る
5. 本文を書く、または改稿する
6. 必要なら `python3 tools/story.py delta <scene-id>` で、シーン後更新用の空の差分メモを作る
7. 結果を `data/state/` や `data/plot/` に反映する
8. 保留案の採用・却下が決まったら `adopt` / `reject` で記録する
9. `python3 tools/story.py checkpoint ...` で今回の確定事項と保留事項を記録する
   `checkpoint` はデフォルトで validation / semantic audit のエラーが残っていると失敗します。意図的に壊れた状態も記録したい時だけ `--allow-findings` を使います。
10. `validate`、`audit`、または `doctor` を再実行する

## 主なコマンド

```bash
python3 tools/story.py validate
python3 tools/story.py list character
python3 tools/story.py show character mira-quill
python3 tools/story.py search ledger
python3 tools/story.py context scene-001
python3 tools/story.py audit scene-001
python3 tools/story.py draft scene-001 --mode scaffold
python3 tools/story.py audit scene-001 --draft drafts/scenes/scene-001.md
python3 tools/story.py audit --ideas
python3 tools/story.py idea flood-prophet --name "Flood Prophet rumor" --summary "A possible witness figure" --spark "What if the city has a human rumor engine?" --question "Is this a person or a distributed legend?"
python3 tools/story.py adopt flood-prophet --into ledger-theft --decision "Adopted as an in-world rumor network, not one person."
python3 tools/story.py reject flood-prophet --reason "Too similar to another rumor mechanism."
python3 tools/story.py delta scene-001
python3 tools/story.py threads
python3 tools/story.py checkpoint "Opening beat aligned" --scene scene-001 --decision "Kept Jun at Tidegate as the gate obstacle" --pending "Write the actual scene prose"
python3 tools/story.py handoff
python3 tools/story.py handoff --with-ideas
python3 tools/story.py doctor
python3 tools/story.py stub character lio-vann --name "Lio Vann"
```

## 設計ドキュメント

- [docs/architecture.md](docs/architecture.md)
- [docs/workflow.md](docs/workflow.md)
- [docs/context-contract.md](docs/context-contract.md)
- [docs/drafting-and-audit.md](docs/drafting-and-audit.md)
- [docs/write-through.md](docs/write-through.md)

## ディレクトリ構成

```text
story-workbench/
├── AGENTS.md
├── config/
├── data/
│   ├── canon/
│   ├── ideas/
│   ├── plot/
│   ├── state/
│   └── timeline/
├── docs/
├── drafts/
├── ops/
├── schemas/
├── src/
├── templates/
├── tests/
└── tools/
```

## 保存方針

JSON を正典フォーマットとして扱います。構造が厳密で、検証しやすく、差分も追いやすいためです。
Markdown は設計メモや運用ルール、引き継ぎ用途に使い、設定そのものの正本にはしません。

`scene_state.sort_key` を時系列アンカーにして、`character_state` / `world_state` / `item_state`
の `updated_at` から、その scene 時点で有効な snapshot を引く前提になっています。

## セッション継続

物語上の決定や進行が確定したら、そのたびに `checkpoint` を実行します。
これにより `ops/handoff/current.md` と `ops/handoff/current.json` が更新され、別セッションからの再開時に
まず読むべき最新状態が残ります。

引き継ぎは安全側がデフォルトです。`handoff`、checkpoint 後の更新、`ops/handoff/current.*` には
保留中の idea の詳細を出しません。ブレスト文脈が必要な時だけ
`python3 tools/story.py handoff --with-ideas` を使ってください。
