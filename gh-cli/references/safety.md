# 安全ルール

## 破壊的コマンドは禁止
以下は絶対に使用しない。

- gh repo delete
- gh repo archive
- gh release delete
- gh release delete-asset
- gh run delete
- gh cache delete
- gh secret delete
- gh variable delete
- gh label delete
- gh ssh-key delete
- gh gpg-key delete
- gh codespace delete
- gh extension remove
- gh gist delete
- xargs と破壊的コマンドの組み合わせ
- rm -rf（テンポラリ削除以外）

## 許可される操作
- 作成、閲覧、検索、更新
- PR/Issue のクローズと再オープン
- ワークフローのキャンセル
- PR のマージ
- 読み取り専用の git 操作
