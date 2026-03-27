---
name: agent-browser-google-auth
description: agent-browserでlocalhost:3000のGoogleログインが必要なブラウザテストを行うときに、.agent-browser/auth.json のセッション保存/復元を自動化する。ユーザーが「ブラウザでテストして」「localhost:3000で確認して」と依頼した場合に使う。
---

# agent-browser-google-auth

## 目的
`agent-browser` を使うブラウザ検証で、`http://localhost:3000` のGoogle認証状態を再利用し、毎回ログイン操作をやり直さずにテストできるようにする。

## 使う場面
- ユーザーがブラウザE2E/手動検証を依頼したとき
- 対象が `localhost:3000` でGoogleログインを要求する画面のとき
- 「ブラウザでテストして」「画面で再現して」など、操作検証が必要なとき

## 実行フロー
1. まず認証状態を準備する
```bash
/Users/rudolph/.agents/skills/agent-browser-google-auth/scripts/ensure_auth_session.sh
```

2. `LOGIN_REQUIRED` が出た場合
- その時点でブラウザは `--headed` で開かれている
- ユーザーにログインを依頼して待つ
- 完了後に状態保存を実行
```bash
/Users/rudolph/.agents/skills/agent-browser-google-auth/scripts/save_auth_state.sh
```
- もう一度 `ensure_auth_session.sh` を実行して復元確認

3. 認証準備ができたら通常のテスト手順を続行
- `agent-browser --session restore ...` を使って操作する

## 運用ルール
- 認証ファイルは `./.agent-browser/auth.json` を使う
- テストURLは `http://localhost:3000` で統一する（`127.0.0.1` を混ぜない）
- `auth.json` は機密情報を含むためコミットしない
- セッション終了時は必要に応じて `agent-browser --session restore close` を実行する

## 参照
詳細手順は `references/agent-browser-auth-workflow.md` を参照。
