---
name: dev-codex-implement
description: Codex に実装または修正を依頼する
user-invocable: false
disable-model-invocation: false
allowed-tools: Bash, Read, Write
argument-hint: "<implement|fix> <feature-name> [YYYY-MM-DD]"
---

# Purpose

Codex を使って feature を実装する。修正時は Todo frontmatter の
`codex_session_id` を使って `codex exec resume <session_id>` で継続する。

# Scripts

スキルのディレクトリのscripts/にスクリプトがあるのでそれをパスを補完して使用

- run_codx.sh: codexを使用するためのスクリプト

# Modes

## implement
- 初回実装
- `scripts/run_codex.sh implement <feature-name> [YYYY-MM-DD]` を使う
- 日付省略時は feature 名で自動検索し、最新の PRD/Todo を使う
- 実行後、wrapper script が JSON 出力から session id を抽出して Todo に保存する

## fix
- 修正
- `scripts/run_codex.sh fix <feature-name> [YYYY-MM-DD]` を使う
- 日付省略時は feature 名で自動検索し、最新の Todo を使う
- Todo に保存された `codex_session_id` を使って resume する

# Rules

- PRD / Todo に従って実装させる
- Todo チェックボックスは進捗に応じて逐次更新させる
- 各タスク単位で commit させる
- commit メッセージは Todo 項目を要約したものにする
