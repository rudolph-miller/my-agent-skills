---
name: dev-plan
description: PRD と Todo を作成する
user-invocable: false
disable-model-invocation: false
allowed-tools: Read, Write, Edit
argument-hint: "<feature-name>"
---

# Purpose

feature 名を受け取り、PRD と Todo の2ファイルを作成する。

保存先は `dev` スキルの Path Resolution ルールに従う:
- `docs/prd/` が存在すれば `docs/` 配下
- なければ `/tmp/claude-dev/<repo-name>/` 配下（自動作成）

# Instructions

1. PRD は `references/prd-template.md` に従って作成する
2. Todo は `references/todo-template.md` に従って作成する
3. Todo は実装可能な粒度に分解する
4. Todo は Markdown チェックボックス形式にする
5. Todo ファイル先頭には以下の frontmatter を入れる

```yaml
---
codex_session_id:
---
```
