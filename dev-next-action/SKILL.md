---
name: dev-next-action
description: 次の実装計画を提案する
user-invocable: false
disable-model-invocation: false
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "<feature-name>"
---

# Purpose

プロジェクトの PRD / Todo を確認し、次に取り組むべき実装計画を提案する。
提案は Codex レビューを通して品質を担保する。

# Path Resolution

ファイル保存先は `dev` スキルと同じルールで自動決定する:

- `docs/prd/` または `docs/todo/` がリポジトリルートに存在する → `docs/` 配下を使用
- 存在しない → `/tmp/claude-dev/<repo-name>/` 配下にフォールバック（自動作成）

| 種別 | docs/ あり | フォールバック |
|------|-----------|---------------|
| PRD | `docs/prd/{date}-{name}.md` | `/tmp/claude-dev/<repo>/prd/{date}-{name}.md` |
| Todo | `docs/todo/{date}-{name}.md` | `/tmp/claude-dev/<repo>/todo/{date}-{name}.md` |
| Proposal | `docs/proposal/{date}-{name}.md` | `/tmp/claude-dev/<repo>/proposal/{date}-{name}.md` |
| Review | `docs/review/next-action-{date}-{name}.md` | `/tmp/claude-dev/<repo>/review/next-action-{date}-{name}.md` |

# Scripts

スキルのディレクトリの scripts/ にスクリプトがあるのでそれをパスを補完して使用

- run_codex.sh: 提案書を Codex にレビューさせるためのスクリプト

# Instructions

1. 既存の PRD / Todo ファイルを Path Resolution ルールに従って探索する
2. 各ファイルの達成状況・未完了タスク・漏れを洗い出す
3. プロジェクトの現状（コード構造、git log 等）を分析する
4. `references/proposal-template.md` に沿って次アクション提案書を作成し、Proposal ディレクトリに保存する
5. Bash で `scripts/run_codex.sh review <feature-name> [YYYY-MM-DD]` を実行して Codex レビューを依頼する
6. レビュー結果を読んで、提案書に反映・修正する
7. 修正項目がなくなるまで 5-6 を繰り返す
8. 最終提案を人間に提示する

# Rules

- feature file naming must be exactly `{YYYY-MM-DD}-<feature-name>.md`
- 提案書のファイル名には feature-name としてプロジェクト名やテーマ名を使う
- レビュー結果のファイル名には `next-action-` 接頭辞を付けて既存レビューと区別する
- Codex レビューで指摘がなくなるまで人間に戻さない
- 最終提案のみ人間に提示する
