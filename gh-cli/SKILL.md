---
name: gh-cli
description: GitHub CLI(gh)の安全な運用ガイド。PR/Issue/Repo/Actions/Codespaces/Release/Gistの作成・閲覧・更新・可逆操作に対応。破壊的操作は一切行わない。
---

# gh-cli

## 目的
GitHub CLI(gh)による日常運用を安全に支援する。読み取り中心と可逆操作に限定し、破壊的コマンドは使用しない。

## 安全ルール
破壊的コマンドは禁止。詳しくは `references/safety.md` を参照。

## 基本方針
- 対話入力を優先。必要時のみフラグを指定。
- 確認が必要な操作は `--web` でブラウザ確認を促す。
- JSON出力は `--json` を使い、フィールドは `--help` で確認する。

## 代表的なワークフロー
- PR: 作成、閲覧、レビュー、マージ、クローズ/再オープン
- Issue: 作成、閲覧、編集、コメント、クローズ/再オープン
- Repo: 参照、クローン、フォーク、同期
- Actions: 実行、確認、監視
- Codespaces: 作成、接続、ログ確認
- Releases: 作成、参照、ダウンロード
- Gists: 作成、参照、編集

詳細なコマンド例は `references/commands.md` を参照。
