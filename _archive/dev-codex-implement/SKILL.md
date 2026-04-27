---
name: dev-codex-implement
description: Codex に full-auto で実装または修正を依頼する（並列実装対応）
user-invocable: false
disable-model-invocation: false
allowed-tools: Bash, Read, Write, Agent
argument-hint: "<implement|parallel|fix> <feature-name> [YYYY-MM-DD] [--group <group>]"
---

# Purpose

Codex を使って feature を実装する。初回実装は `codex exec --full-auto` を
前提に進める。修正時は Todo frontmatter の `codex_session_ids` を使って
`codex exec resume <session_id>` で継続する。

# Scripts

スキルのディレクトリのscripts/にスクリプトがあるのでそれをパスを補完して使用

- run_codex.sh: codexを使用するためのスクリプト

# Prerequisites

- PRD / Todo ファイルが `docs/` 配下にある場合は git commit 済みであること（worktree はコミット済みファイルのみ参照可能）
- `/tmp/` フォールバック時は commit 不要（スクリプトが元リポジトリ名で絶対パスを解決する）

# Modes

## implement
- 単一グループまたはグループ未指定の実装
- Claude の Agent ツール（`isolation: "worktree"`）でサブエージェントを生成する
- サブエージェント内で `scripts/run_codex.sh implement <feature-name> [YYYY-MM-DD] [--group <group>]` を実行する
- 日付省略時は feature 名で自動検索し、最新の PRD/Todo を使う
- 実行後、wrapper script が JSON 出力から session id を抽出して Todo に保存する
- 実装は `--full-auto` 前提で回し、worktree 内で完結させる
- サブエージェント完了後、worktree の変更をメインブランチにマージする
- マージコンフリクトが発生した場合は Claude が解決する
- マージ完了後、`git worktree remove <path>` と `git branch -d <branch>` で worktree を削除する

## parallel
- Todo に複数グループがある場合の並列実装
- 手順:
  1. `scripts/run_codex.sh list-groups <feature-name>` でグループ一覧を取得する
  2. 各グループにつき Claude の Agent ツール（`isolation: "worktree"`）でサブエージェントを生成する
  3. 各サブエージェント内で `scripts/run_codex.sh implement <feature-name> --group <group>` を実行する
  4. 全サブエージェント完了後、各 worktree の変更をメインブランチにマージする
  5. マージコンフリクトが発生した場合は Claude が解決する
  6. マージ完了後、各 worktree を `git worktree remove <path>` と `git branch -d <branch>` で削除する
- サブエージェントは全て同時に起動する（並列実行）
- 各サブエージェントの完了を待ってからマージ工程に進む

## fix
- 修正
- Claude の Agent ツール（`isolation: "worktree"`）でサブエージェントを生成する
- サブエージェント内で `scripts/run_codex.sh fix <feature-name> [YYYY-MM-DD] [--group <group>]` を実行する
- 日付省略時は feature 名で自動検索し、最新の Todo を使う
- Todo に保存された `codex_session_ids` のうち該当グループの session_id を使って resume する
- `resume` は既存 session 継続を優先し、同じ session の文脈を壊さない
- サブエージェント完了後、worktree の変更をメインブランチにマージする
- マージコンフリクトが発生した場合は Claude が解決する
- マージ完了後、`git worktree remove <path>` と `git branch -d <branch>` で worktree を削除する

# Rules

- PRD / Todo に従って実装させる
- Todo チェックボックスは進捗に応じて逐次更新させる
- 各タスク単位で commit させる
- commit メッセージは Todo 項目を要約したものにする
- parallel モード時、各サブエージェントは自グループのファイルスコープのみ変更する
- worktree のマージまでを implement/fix 側の責務とし、`dev-verify` に部分状態を渡さない
