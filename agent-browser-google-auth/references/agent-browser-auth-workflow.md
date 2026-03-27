# agent-browser で Google ログイン状態を保存/復元する詳細手順

## 前提
- 開発サーバ: `http://localhost:3000`
- セッション保存先: `./.agent-browser/auth.json`

## 初回
1. `ensure_auth_session.sh` を実行
2. `LOGIN_REQUIRED` が出たら、開いたブラウザで手動ログイン
3. ログイン後に `save_auth_state.sh` を実行

## 2回目以降
1. `ensure_auth_session.sh` を実行
2. `restore_localhost_auth.sh` が cookie/localStorage を注入して認証状態を復元
3. 復元済みセッション `restore` を使って操作

## トラブルシュート
- ログイン画面に戻る場合
  - `auth.json` が古い可能性があるため、再ログインして `save_auth_state.sh` を再実行
- 別ドメイン扱いになる場合
  - `localhost` と `127.0.0.1` を混在させない
- セッションをクリーンにしたい場合
  - `agent-browser --session restore close`
