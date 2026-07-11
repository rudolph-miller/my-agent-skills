# Memory curation policy

## keep

- 再取得が高コストな根本原因と再発防止
- 複数repoで繰り返す権限・安全性ルール
- live readbackやrollbackを含む不変runbook
- ユーザーが明示した安定したpreferences

## merge

- 同じautomationの日次no-op
- 日付、SHA、件数だけが異なる同一手順
- 同じrolloutを細分化した複数Task
- User preferences / Reusable knowledge / Failuresで重複する同一ルール

1つの不変手順、最新の意味ある状態遷移、rollout pointerへ縮約する。

## demote to snapshot

- commit SHA、PR/run/job id
- deployment URL、revision、IP、nameserver
- 件数、割合、価格、見積期限
- secret version、current status、最新メール・予定

値そのものはrollout summary、automation memory、project artifactへ残し、active Memoryには「live再確認する」ルールだけ置く。

## remove from active index

- 実行証跡のないcontract-only Task
- 完了・削除済みmonitorの個別検索結果
- AGENTSやskillがすでにsource of truthになった変更履歴
- 別のautomation memoryに完全に重複する各回結果

raw evidenceは削除しない。

## promote

- 全projectの権限、安全性、完了条件 → AGENTS
- 3手順以上のtool固有runbook → skill
- recurring runの各回結果 → automation memory / dated report
- repo固有の設計・schema・運用 → project docs

## sensitive data

Memory整理レポートへtoken、secret payload、private key、不要なPIIを転載しない。存在と分類だけを記録する。
