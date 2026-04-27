---
name: dev
description: Codexで行うソフトウェア開発作業の入口。機能実装、バグ修正、リファクタリング、コード調査からの実装、PRD/Todo作成、レビュー、worktree並列実装、merge、fix、verifyが必要なときに使う。
metadata:
  short-description: Codex開発フロー
---

# Dev

## 目的

Codex 一本で、成果物ファイルを介した開発フローを実行する。

非自明なコード変更、設計判断、PRD / Todo 作成、レビュー、並列実装、merge、verify が必要な作業で使う。小さく安全な修正では PRD / Todo を省略してよいが、調査・実装・検証の境界は崩さない。

## 言語

- チャット、途中進捗、最終報告は日本語で行う
- inspect note、PRD、Todo、review note、verify note は原則日本語で作成する
- ユーザーが英語を明示した場合だけ、指定された成果物を英語にする
- コード、識別子、コマンド、ログ、エラーメッセージ、外部仕様名は原文を保つ

## 基本モデル

使うエージェント群は Codex のみ。プロダクトで分けず、役割で分ける。

- **Orchestrator**: メインスレッドを担当する。依頼整理、経路選択、成果物管理、merge、最終報告を行う
- **Inspector**: コードや挙動を調査する。原則として編集しない
- **Planner**: 調査結果と依頼から PRD / Todo を作成する
- **Reviewer**: PRD / Todo と統合後 diff をレビューする
- **Worker**: Todo group ごとに、分離された worktree で実装する
- **Verifier**: 統合後の状態を、テスト、ビルド、lint、ログ、手動確認で検証する

サブエージェントが使える場合は、Inspector、Reviewer、Worker、Verifier に使う。使えない場合は、同じスレッド内で役割境界を明示して順番に進める。

## 経路選択

編集前に依頼を分類する。

- **inspect-only**: 原因、影響範囲、実現可能性、仕様確認だけが目的。編集しない
- **safe-small-fix**: 局所的で曖昧さが少ない修正。短く調査して直接実装し、検証する
- **inspect-then-plan**: 実装可否や方針判断のために調査が必要
- **plan-direct**: 目的は明確だが、実装が非自明。PRD / Todo を作ってから実装する
- **next-action**: 次に何を実装するかを決める。既存 PRD / Todo と repo 状態を見て提案する

安全な判断に必要な情報が足りない場合だけユーザーに質問する。ブロックしない不明点は、保守的な仮定として成果物や報告に明記する。

## 成果物ルール

工程間の橋渡しはファイルで行う。会話の暗黙コンテキストに依存しない。

既定パス:

```text
docs/inspect/{YYYY-MM-DD}-{task-slug}.md
docs/prd/{YYYY-MM-DD}-{task-slug}.md
docs/todo/{YYYY-MM-DD}-{task-slug}.md
docs/review/{YYYY-MM-DD}-{task-slug}.md
docs/verify/{YYYY-MM-DD}-{task-slug}.md
```

`docs/` を使わない repo では `.codex/artifacts/{task-slug}/` に一時成果物を置く。ユーザーまたはプロジェクト方針が永続的な計画履歴を求めない限り、これらはコミットしない。

PRD は日本語で、次を含める。

- 背景と問題
- 目的
- 非目標
- スコープ
- 要件
- 実装方針
- 受け入れ条件
- 検証方法

Todo は日本語で、次を含める。

- チェックボックス形式のタスク
- 並列実装できる group 境界
- group ごとの担当ファイル範囲または想定 write scope
- 検証タスク
- 既知リスクと、必要な場合の rollback note

## 標準フロー

1. **Inspect**
   - プロジェクト指示、現在の git 状態、関連ファイル、テスト、ログを読む
   - 非自明な作業では inspect note を日本語で作る
   - `inspect-only` では編集しない

2. **Plan**
   - 非自明な作業では PRD / Todo を日本語で作る
   - `safe-small-fix` の場合だけ省略してよい
   - Todo は独立して実装できる group に分ける

3. **Review**
   - 実装前に PRD / Todo を1回レビューする
   - 観点は、要件漏れ、受け入れ条件、ファイル範囲の衝突、並列化リスク、検証範囲に絞る
   - 文面だけのレビューを繰り返さない

4. **Implement**
   - group が1つなら、必要に応じて main worktree で実装する
   - group が複数なら、group ごとに worktree を作り、担当範囲を分ける
   - Worker は Todo のチェックボックスを更新し、変更ファイルと実行した検証を報告する

5. **Merge**
   - Worker の成果を main worktree に統合する
   - コンフリクトは、どちらかを機械的に採用せず、意図した挙動を保つよう解決する
   - verify 前に統合 diff をレビューする

6. **Verify**
   - 関連テストに加え、現実的な範囲で repo 標準の build / lint / typecheck を実行する
   - UI 変更では、可能な限りアプリを起動して対象画面を確認する
   - 失敗した場合は fix に戻り、green になるかブロック理由が明確になるまで繰り返す

7. **Report**
   - 何を変えたか、何を検証したか、残リスクを日本語で報告する
   - push した場合は、グローバル AGENTS の形式に従って commit、push 先、GitHub Actions、Vercel、備考を含める

## worktree 方針

このスキルが明示的に worktree を作る場合は、repo-local worktree を優先する。

```text
<repo>/.codex/worktrees/<task-slug>/<group-name>
```

推奨手順:

```bash
mkdir -p .codex/worktrees/<task-slug>
grep -qxF ".codex/worktrees/" .git/info/exclude || printf "\n.codex/worktrees/\n" >> .git/info/exclude
git worktree add .codex/worktrees/<task-slug>/<group-name> -b codex/<task-slug>/<group-name>
```

実行環境が自動で作る Codex 管理 worktree を使った場合は、最終報告で場所を明記する。

`git reset --hard` や worktree 削除のような破壊的 cleanup は、ユーザーが明示した場合だけ行う。通常は `git worktree list` で確認し、merge 済みまたは破棄可能であることが明確な場合に限って `git worktree remove` を検討する。

## 人間確認ポイント

確認は軽く、必要な場所に絞る。

- 非自明な PRD / Todo 実装前: 目的、変更範囲、非目標、主要リスクを短く提示する
- 不可逆操作前: 破壊的 git 操作、本番データ変更、deploy、外部送信
- 検証後: 最終報告

内部工程の通常遷移では、ブロックしていない限り止まらない。

## 品質基準

- 応急処置ではなく根本原因を解決する
- 変更範囲を依頼に絞る
- ユーザーの未コミット変更を保持する
- 既存の project pattern を優先する
- 曖昧な依頼を検証可能な成果に変換する
- 完了前に必ず検証する
