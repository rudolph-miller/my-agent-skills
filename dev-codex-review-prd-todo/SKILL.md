---
name: dev-codex-review-prd-todo
description: Codex に PRD と Todo のレビューを依頼する
user-invocable: false
disable-model-invocation: false
allowed-tools: Bash, Read, Write
argument-hint: "<feature-name>"
---

# Purpose

PRD と Todo を入力として Codex にレビューを依頼する。
ファイルパスは `run_codex.sh` が Path Resolution ルールに従って自動解決する。

# Scripts

スキルのディレクトリのscripts/にスクリプトがあるのでそれをパスを補完して使用

- run_codx.sh: codexを使用するためのスクリプト

# Instructions

1. Bash で `scripts/run_codex.sh review <feature-name>` を実行する
2. 出力は Review ディレクトリ（Path Resolution ルールで決定）に保存される
3. Claude はその結果を読んで、PRD / Todo の修正点を整理する
