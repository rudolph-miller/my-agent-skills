---
name: dev-verify
description: 実装の検証と人間への報告を行う
user-invocable: false
disable-model-invocation: false
allowed-tools: Read, Write, Edit, Glob, Grep
argument-hint: "<feature-name>"
---

# Purpose

PRD / Todo / 実装結果 / レビュー結果を照合し、Claude が最終的な検証を行う。
そのうえで `references/report-template.md` を使って人間向け報告を作る。

# Inputs

- PRD ファイル（Path Resolution ルールで決定されたディレクトリ内）
- Todo ファイル（同上）
- Review ファイル（同上、存在すれば）
- 差分や commit 状況

パス解決: `docs/prd/` が存在すれば `docs/` 配下、なければ `/tmp/claude-dev/<repo-name>/` 配下。

# Instructions

1. `references/verify-checklist.md` に沿って確認する
2. 未完タスク、未反映レビュー、要件漏れがあれば明示する
3. 問題がなければ `references/report-template.md` に従って人間向け要約を作る
