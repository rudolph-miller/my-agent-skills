---
name: dev
description: Claude を入口にして、Codex の inspect / plan / implement / verify を分岐させる
user-invocable: true
disable-model-invocation: false
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "<feature-name>"
---

# Purpose

Claude を入口のオーケストレータ、Codex をコード読解・調査・計画・実装・検証の実働主体として使い、
必要なファイルを橋渡しにして開発を進める。

# Path Resolution

ファイル保存先は以下のルールで自動決定する:

- `docs/prd/` または `docs/todo/` がリポジトリルートに存在する → `docs/` 配下を使用
- 存在しない → `/tmp/claude-dev/<repo-name>/` 配下にフォールバック（自動作成）

| 種別 | docs/ あり | フォールバック |
|------|-----------|---------------|
| PRD | `docs/prd/{date}-{name}.md` | `/tmp/claude-dev/<repo>/prd/{date}-{name}.md` |
| Todo | `docs/todo/{date}-{name}.md` | `/tmp/claude-dev/<repo>/todo/{date}-{name}.md` |
| Inspect Request | `docs/inspect-request/{date}-{name}.md` | `/tmp/claude-dev/<repo>/inspect-request/{date}-{name}.md` |
| Inspect | `docs/inspect/{date}-{name}.md` | `/tmp/claude-dev/<repo>/inspect/{date}-{name}.md` |
| Review | `docs/review/{date}-{name}.md` | `/tmp/claude-dev/<repo>/review/{date}-{name}.md` |

# Workflow

1. 依頼を `inspect-only` / `inspect-then-plan` / `plan-direct` のどれかに分類する
2. `inspect-only` または `inspect-then-plan` の場合:
   - Claude は症状・問い・期待動作・制約・欲しい出口を短い inspect request memo にまとめる
   - `dev-codex-inspect` を呼び出して inspect report を作る
3. `inspect-only` の場合:
   - `dev-codex-inspect` の結果を Claude が要約して人間へ返し、ここで終了する
4. `inspect-then-plan` の場合:
   - inspect report の `Recommended Next Action` を確認する
   - `answer-only` なら調査結果だけ返して終了する
   - `safe-small-fix` なら `dev-codex-implement` に進む
   - `plan-needed` なら `dev-codex-plan` に進む
5. `plan-direct` の場合:
   - Claude が質問して planning input を具体化する
   - 以下が揃うまで `dev-codex-plan` を呼び出さない
     - 目的
     - 成功条件
     - 制約
     - 今回やらないこと
     - 未解決質問の有無
6. `dev-codex-plan` が `PRD / Todo + Codex inline self-review + 全体設計レビュー` を完了したら、`references/review-completion-template.md` に従って人間へ確認を取る
7. 実装開始の確認後、`dev-codex-implement` を `implement` または `parallel` モードで呼び出して実装させる
8. worktree の変更が統合されたら `dev-verify` を呼び出して検証する
9. 修正が必要なら `dev-codex-implement` を `fix` モードで呼び出す
10. `dev-verify` が通るまで `fix → verify` を繰り返す
11. 最後に `dev-verify` の結果をもとに、Claude が人間向け最終報告を整える

※ 3、6 と最終報告以外で人間にもどさないで自律的に進める

# Rules

- feature file naming must be exactly `{YYYY-MM-DD}-<feature-name>.md`
- パスは上記 Path Resolution ルールに従って決定する
- コードを読まないと答えられない依頼では、Claude が主スレッドで多段の `Read` / `Grep` / `Bash` 調査を始めず、まず `dev-codex-inspect` を使う
- `inspect-only` は説明や原因確認が目的のときだけ使う
- `safe-small-fix` は、局所変更・期待動作が明確・既存パターン準拠のときだけ implement に直行してよい
- `plan-needed` なら brainstorming を飛ばして `dev-codex-plan` に直行してはいけない。必要なら Claude が追加質問を行う
- Todo は Markdown チェックボックスで管理する
- レビュー完了後の実装開始確認は `references/review-completion-template.md` の項目順で報告する
- 実装時は Todo のチェック更新と commit を同じ変更単位で行わせる
- fix 時は Todo frontmatter に保存された `codex_session_ids` を利用して resume する
