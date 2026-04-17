---
name: dev-verify
description: 実装の検証と人間への報告を行う
user-invocable: false
disable-model-invocation: false
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "<feature-name>"
---

# Purpose

PRD / Todo / 実装結果 / レビュー結果を照合し、マージ後の統合状態を検証する。
Codex に review / verify をさせつつ、Claude が最終的な点検と人間向け報告を行う。

# Inputs

- PRD ファイル（Path Resolution ルールで決定されたディレクトリ内）
- Todo ファイル（同上）
- Review ファイル（同上、存在すれば）
- 差分や commit 状況
- マージ済みの作業ツリー状態

パス解決: `docs/prd/` が存在すれば `docs/` 配下、なければ `/tmp/claude-dev/<repo-name>/` 配下。

# Instructions

1. まず worktree 由来の変更がすでに統合済みか確認する。未統合なら、この skill でマージせず `dev-codex-implement` 側に戻す
2. `references/verify-checklist.md` に沿って確認する
3. テスト、ビルド、リントなどの検証コマンドを実行する
4. Codex に review / verify を依頼し、PRD / Todo / 現在の差分の整合性を点検させる
5. 未完タスク、未反映レビュー、要件漏れがあれば明示し、`fix` に戻すための修正メモを作る
6. 問題がなければ `references/report-template.md` に従って、目的 / 実施内容 / 完了したこと / 残課題 / リスク / 人間確認事項の順で報告を作る
