---
name: dev-codex-plan
description: Claude が要件を具体化した後に、Codex に調査・PRD/Todo 作成・自己点検・全体設計レビューをさせる
user-invocable: false
disable-model-invocation: false
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "<feature-name>"
---

# Purpose

Claude が人間との対話で整理した要求をもとに、Codex で調査しつつ
PRD と Todo を作成する。計画段階でのレビューは、細かい task の反復
レビューではなく、以下の2段に限定する。

1. Codex 自身の inline self-review
2. Codex の別セッションによる全体設計レビュー

必要な場合のみ、追加で 1 回だけレッドチームレビューを行う。

# Path Resolution

ファイル保存先は以下のルールで自動決定する:

- `docs/prd/` または `docs/todo/` がリポジトリルートに存在する → `docs/` 配下を使用
- 存在しない → `/tmp/claude-dev/<repo-name>/` 配下にフォールバック（自動作成）

| 種別 | docs/ あり | フォールバック |
|------|-----------|---------------|
| PRD | `docs/prd/{date}-{name}.md` | `/tmp/claude-dev/<repo>/prd/{date}-{name}.md` |
| Todo | `docs/todo/{date}-{name}.md` | `/tmp/claude-dev/<repo>/todo/{date}-{name}.md` |
| Review | `tmp/review/{date}-{name}.md` | `<repo>/tmp/review/{date}-{name}.md` |

# HARD-GATE

以下が揃っていない限り、PRD / Todo を作成してはいけない。

- 目的
- 成功条件
- 制約
- 今回やらないこと
- 未解決質問の有無

不足がある場合は、計画に進まず `不足情報` と `確認質問` を返して終了すること。
この skill は brainstorm の代替ではない。

# Inputs

`dev` から以下が引き渡されている前提:

- feature 名
- Claude が整理した planning input memo
  - 目的
  - 成功条件
  - 制約
  - 今回やらないこと
  - 未解決質問の有無
  - 必要に応じて既存コードや既存ノートの要約

# Instructions

1. planning input memo が HARD-GATE を満たしているか確認する
2. 必要な追加調査があれば、Codex に調査させる
3. `references/prd-template.md` と `references/todo-template.md` に沿って、Codex に PRD / Todo を作成させる
4. Codex の計画作成プロンプトには、以下を同一セッション内で必ず行わせる
   - 必要な調査
   - PRD 作成
   - Todo 作成
   - inline self-review
5. inline self-review では少なくとも以下を点検させる
   - PRD の要求を Todo がカバーしているか
   - placeholder や曖昧表現が残っていないか
   - 旧方針の残骸や矛盾がないか
   - task 粒度が大きすぎないか
   - group 間で file scope の衝突が起きないか
6. PRD / Todo を保存したら、Codex の別セッションで全体設計レビューを 1 回だけ行う
7. 全体設計レビューは以下に限定する
   - 要件漏れ
   - 設計の矛盾
   - 実装順序や依存関係の破綻
   - テスト観点の不足
   - 過剰設計または危険な前提
8. 全体設計レビューの指摘を反映したら、同じ論点で再レビューをループさせない
9. 以下の条件に当てはまるときだけ、Codex の別セッションでレッドチームレビューを 1 回だけ追加する
   - 認証や権限に関わる
   - データ移行や破壊的変更がある
   - 公開 API / 契約変更がある
   - 非同期処理や外部依存が複雑
10. レビュー完了後、`dev` に返す内容は以下に絞る
   - 何のためにやるか
   - 何を行うか
   - 対象範囲
   - 主要な設計判断
   - 実装しないこと
   - リスク / 未確定事項

# Rules

- review loop を細かい task 単位に拡張しない
- 計画レビューの主対象は文面ではなく全体設計と実装可能性
- Todo は Markdown チェックボックスで管理する
- Todo 先頭には以下の frontmatter を入れる

```yaml
---
codex_session_ids: {}
---
```

- グループ名は短い英語識別子にする
- 異なるグループが同じファイルを変更しないように分割する
- レビュー結果は必要なら `tmp/review/` に保存してよいが、レビューを増やすために保存してはいけない
