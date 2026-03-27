---
name: dev
description: Claude + Codex の開発フローを一気通貫で実行する。微修正以外の機能開発時は必ずこのフローを行う
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "<feature-name>"
---

# Purpose

Claude を設計・検証責任者、Codex をレビュー・実装実行者として使い、
PRD と Todo ファイルを橋渡しにして開発を進める。

# Path Resolution

ファイル保存先は以下のルールで自動決定する:

- `docs/prd/` または `docs/todo/` がリポジトリルートに存在する → `docs/` 配下を使用
- 存在しない → `/tmp/claude-dev/<repo-name>/` 配下にフォールバック（自動作成）

| 種別 | docs/ あり | フォールバック |
|------|-----------|---------------|
| PRD | `docs/prd/{date}-{name}.md` | `/tmp/claude-dev/<repo>/prd/{date}-{name}.md` |
| Todo | `docs/todo/{date}-{name}.md` | `/tmp/claude-dev/<repo>/todo/{date}-{name}.md` |
| Review | `docs/review/{date}-{name}.md` | `/tmp/claude-dev/<repo>/review/{date}-{name}.md` |

# Workflow

1. `dev-plan` を呼び出して PRD / Todo を作成する
2. `dev-codex-review-prd-todo` を呼び出して Codex にレビューさせる
3. Claude がレビューを反映して PRD / Todo を手直しする
4. `dev-codex-review-prd-todo` の指摘がなくなるまでレビューの反映と `dev-codex-review-prd-todo` でのレビューを繰り返す
5. 必要なら人間確認を取る
6. `dev-codex-implement` を `implement` モードで呼び出して実装させる
7. `dev-verify` を呼び出して検証する
8. 修正が必要なら `dev-codex-implement` を `fix` モードで呼び出す
9. `dev-verify` が通るまで `dev-codex-implement` の `fix` モードでの修正と `dev-verify` を繰り返す
10. `dev-verify` の report テンプレートで人間に報告する

※ 5のステップと最終報告以外で人間にもどさないで自律的に進める

# Rules

- feature file naming must be exactly `{YYYY-MM-DD}-<feature-name>.md`
- パスは上記 Path Resolution ルールに従って決定する
- Todo は Markdown チェックボックスで管理する
- 実装時は Todo のチェック更新と commit を同じ変更単位で行わせる
- fix 時は Todo frontmatter に保存された `codex_session_id` を利用して resume する
