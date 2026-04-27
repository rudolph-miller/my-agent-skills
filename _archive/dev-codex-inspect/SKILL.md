---
name: dev-codex-inspect
description: Codex にコード読解・原因調査・影響範囲確認をさせ、実装せずに構造化レポートを返させる
user-invocable: false
disable-model-invocation: false
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "<feature-name>"
---

# Purpose

Codex を使ってコード読解・原因調査・仕様確認を行う。ここでは実装しない。
出力は `inspect report` に固定し、`dev` がその結果を使って
`answer-only` / `safe-small-fix` / `plan-needed` に分岐する。

# Path Resolution

ファイル保存先は以下のルールで自動決定する:

- `docs/inspect-request/` または `docs/inspect/` がリポジトリルートに存在する → `docs/` 配下を使用
- 存在しない → `/tmp/claude-dev/<repo-name>/` 配下にフォールバック（自動作成）

| 種別 | docs/ あり | フォールバック |
|------|-----------|---------------|
| Inspect Request | `docs/inspect-request/{date}-{name}.md` | `/tmp/claude-dev/<repo>/inspect-request/{date}-{name}.md` |
| Inspect Report | `docs/inspect/{date}-{name}.md` | `/tmp/claude-dev/<repo>/inspect/{date}-{name}.md` |

# Inputs

- Claude が作った短い inspect request memo
  - 問い
  - 症状または期待動作
  - 再現条件（あれば）
  - 制約
  - いま欲しい出口（説明だけ / 修正判断 / 実装判断）

# Scripts

スキルのディレクトリの `scripts/` にスクリプトがあるのでパスを補完して使用する

- `run_codex.sh`: inspect request をもとに Codex 調査を実行する

# Instructions

1. `feature-name` を決め、Path Resolution ルールに従って inspect request / report のパスを決定する
2. inspect request memo がない場合は、Claude が先に作成する
3. Bash で `scripts/run_codex.sh inspect <feature-name> [YYYY-MM-DD]` を実行する
4. 生成された inspect report を読み、次アクションを確認する
5. `dev` へ返すときは、report 全文ではなく以下だけを短く要約する
   - 事実
   - 根本原因または主要候補
   - 関連ファイル / 関連シンボル
   - 次の推奨アクション

# Rules

- ここでは実装しない
- ここでは PRD / Todo を作らない
- 主目的は「コードを読むこと」であり、解決策を膨らませすぎない
- 必ず `answer-only` / `safe-small-fix` / `plan-needed` のいずれかを report に書かせる
- `safe-small-fix` は、局所変更・期待動作が明確・既存パターン準拠のときだけ使う
- 複数ファイルにまたがる設計判断、検証計画、比較が必要なら `plan-needed` を返す
