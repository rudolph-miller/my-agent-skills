---
name: dev
description: Claude + Codex の開発フローを一気通貫で実行する。微修正以外の機能開発時は必ずこのフローを行う
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "<feature-name>"
---

# Purpose

Claude を入口のオーケストレータ、Codex を調査・計画・実装・検証の実働主体として使い、
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

1. feature の意図を確認し、必要なら Claude が質問してアイデアを具体化する
2. 以下の planning input が揃うまで `dev-codex-plan` を呼び出さない
   - 目的
   - 成功条件
   - 制約
   - 今回やらないこと
   - 未解決質問の有無
3. planning input を短いメモにまとめて `dev-codex-plan` を呼び出す
4. `dev-codex-plan` が `PRD / Todo + Codex inline self-review + 全体設計レビュー` を完了したら、`references/review-completion-template.md` に従って人間へ確認を取る
5. 実装開始の確認後、`dev-codex-implement` を `implement` または `parallel` モードで呼び出して実装させる
6. worktree の変更が統合されたら `dev-verify` を呼び出して検証する
7. 修正が必要なら `dev-codex-implement` を `fix` モードで呼び出す
8. `dev-verify` が通るまで `fix → verify` を繰り返す
9. 最後に `dev-verify` の結果をもとに、Claude が人間向け最終報告を整える

※ 4 と最終報告以外で人間にもどさないで自律的に進める

# Rules

- feature file naming must be exactly `{YYYY-MM-DD}-<feature-name>.md`
- パスは上記 Path Resolution ルールに従って決定する
- brainstorming を飛ばして `dev-codex-plan` に直行してはいけない
- planning input が不足している場合は、先に Claude が追加質問を行う
- Todo は Markdown チェックボックスで管理する
- レビュー完了後の実装開始確認は `references/review-completion-template.md` の項目順で報告する
- 実装時は Todo のチェック更新と commit を同じ変更単位で行わせる
- fix 時は Todo frontmatter に保存された `codex_session_ids` を利用して resume する
