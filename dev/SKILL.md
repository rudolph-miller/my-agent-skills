---
name: dev
description: Codexで行うソフトウェア開発の入口。コード・設定・テスト・ビルド・技術設計・PRD/Todo・CI/CD・runtime障害の調査、実装、修正、レビュー、worktree並列化、統合、検証、PR作成へ進む可能性があるときに使う。
---

# Dev

Codexだけで、調査から検証可能な成果までを最小の工程で進める。モデル名やreasoning effortはruntime設定をsource of truthとし、このスキルでは固定しない。

## 最初に分類する

編集前に分類を1行で宣言する。scopeが変わったら再分類する。

- **inspect**: 原因、影響、実現可能性、次の実装候補だけを調べる。編集しない。
- **direct-fix**: 原因と期待動作が確認済みの単一変更を直接実装する。
- **planned-change**: 複数コンポーネント、設計判断、migration、required config、infra、複数write group、高リスク変更を計画して実装する。

`direct-fix` は次をすべて満たす場合だけ使う。

- 原因が仮説ではなく確認済みである。
- 変更する主要ファイルを特定済みで、概ね3ファイル以内である。
- 既存patternに従う単一の挙動変更である。
- 公開契約、schema、required config、権限、infra、本番データを変更しない。

1回の修正で改善しない、scopeが広がる、原因が変わる場合は`planned-change`へ昇格する。

## 権限を解釈する

- `実装して`、`修正して`は、依頼scopeのlocal編集と検証を許可する。同じscopeで実装開始を再確認しない。
- `すすめて`、`すべてすすめて`、`PR作成まで`は、宣言済みscopeの実装・検証・必要なcommit/push/PR作成までを許可する。
- `すすめて`、`すべて対応する`、`PR作成まですすめて`を、GitHub PR merge、deploy、本番変更の承認へ拡張しない。
- GitHub PR merge、deploy、本番データ変更、外部送信、破壊的cleanupは、明示された場合だけ行う。
- 未解決のproduct判断、受け入れ条件の変更、重大なscope拡張が必要な場合だけ止まって確認する。

`Integrate`はWorker差分のローカル統合を指し、GitHub PR mergeを意味しない。

## 成果物を最小化する

### direct-fix

会話内で目的、対象、検証方法を短く示す。永続成果物は原則不要。

### planned-change

既定では`.codex/artifacts/<task-slug>/brief.md` 1枚に次をまとめる。

- 背景、目的、非目標
- scopeと受け入れ条件
- チェックボックスTodoとwrite scope
- 検証方法
- リスク、rollback、進行Notes
- 1回のreview判定と指摘

repoが永続的な設計履歴を求める場合、または複数repo・複数write group・長期移行の場合だけ、既存規約に従ってinspect / PRD / Todo / review / verifyを分割する。成果物は原則日本語にする。

reviewは要件漏れ、受け入れ条件、write scope衝突、検証範囲に絞る。文面だけのreviewを繰り返さない。

## execution surfaceを選ぶ

### メインスレッド

単一write group、統合判断、fallback実装を逐次担当する。現在のruntime configをそのまま使う。

### read-only subagent

独立した調査、検索、比較、reviewへ自律的に使ってよい。shared filesystemであることを前提に、原則として編集させない。1 agent 1 taskにする。

### isolated worktree Worker

複数の独立write groupを並列実装するときだけ使う。ユーザーが並列writeを明示的に許可した場合、または依頼自体がworktree並列実装を含む場合に起動する。

- groupごとにworktree、write scope、受け入れ条件、検証commandを分ける。
- 最初のWorkerでmodel、effort、agent role、cwd/worktreeをruntime metadataから確認する。
- TOMLや静的configだけで実効modelを確定扱いしない。
- role/modelを選べない、想定外、または分離を証明できない場合は、メインで逐次実装する。
- 他Workerやユーザーの変更を巻き戻さない。衝突はOrchestratorへ戻す。

runtime routingを変更・再検証するときは、利用可能なら`audit-codex-runtime`を使う。

## 標準フロー

1. **Inspect**
   - project指示、関連Memory、git status/worktree、コード、テスト、ログ、既存仕様を読む。
   - 原因未解明の障害は、観察 → 仮説 → 切り分けで進め、原因確認前に実装commitしない。
   - 一時的な診断変更は根本修正に含まれない限りcommitしない。
2. **Plan / Review**
   - `planned-change`ではbriefまたはrepo規約の成果物を作り、1回reviewする。
   - ユーザーがすでに実装を承認し、scopeが変わっていなければそのまま実装へ進む。
3. **Implement**
   - 既存patternを優先し、依頼外のrefactor、formatter churn、dead code削除を行わない。
   - worktree作成後は必要なdependencyを用意し、編集前にcwdと既存差分を確認する。
4. **Integrate**
   - Worker差分を意図した挙動に沿ってローカル統合する。
   - verify前に統合diffとscope外変更をreviewする。
5. **Verify**
   - 変更に最も近いテストから始め、影響範囲に応じてlint、typecheck、build、UI確認へ広げる。
   - 既存baseline failureと今回起因のfailureを分ける。
   - required config変更では、code、fixture、local/prd config、secret反映順、後方互換性、startup readbackを一つの受け入れ条件として扱う。利用可能なら`config-rollout-guard`を使う。
   - failureはfixへ戻し、greenまたは証拠付きblockerになるまで続ける。
6. **Publish**
   - 許可scopeにcommit/push/PR作成が含まれる場合だけ進める。
   - mixed worktreeでは対象pathだけstageする。
   - broad/high-risk変更で指定がなければdraft PRを使う。
7. **Closeout**
   - pushしたcommit SHAに紐づくGitHub Actionsを確認する。
   - repo/workflowから実際のdeploy surfaceを確定し、Vercel、Cloud Run、Cloudflare等は該当する場合だけ確認する。非該当は根拠付きでN/Aにする。
   - live readback可能な変更は、公開endpoint、DB、ログ、HTML等で確認する。利用可能なら`verify-dev-closeout`を使う。

## worktree方針

runtimeが管理するisolated worktreeを優先する。明示的に作る場合はrepo-localまたは作業用外部pathを使い、場所を報告する。

repo-localの`.codex/worktrees/**`を使う前に、ESLint、TypeScript、test runner、build tool、file watcherがその配下を走査しないか確認する。`.git/info/exclude`だけではlint/build除外にならない。

`git reset --hard`、未確認のworktree削除、ユーザー差分の破棄を行わない。cleanupはcandidate、判定根拠、real diff、削除後の残差を確認する。

## checkpointと引き継ぎ

compaction、material scope変更、owner変更、長時間化が起きたらbriefのTodoとNotesを更新する。Notesに未コミット差分、完了済み検証、残作業、次の一手を書く。

compaction回数だけで新しいtaskを強制しない。同じ成果を継続できるならcheckpointから続け、別write groupや独立成果へ変わる場合だけtaskを分ける。

## 最終報告

目的に対して何を変えたか、検証結果、残リスクを先に返す。pushした場合は次を含める。

- Commit: SHA
- Push: branch / remote
- GitHub Actions: URL / status / conclusion
- Deploy surface: provider / URLまたはproject / status、非該当はN/A理由
- 備考: failure対応、確認不能理由、runtime Worker証拠
