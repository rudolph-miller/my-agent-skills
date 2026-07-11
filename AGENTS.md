# AGENTS.md

このリポジトリで作業する AI エージェント向けの指示です。

## 目的

- スキルの追加・更新を安全かつ一貫した形式で行う
- スキル一覧と内容の整合性を保つ

## 作業ルール

- 新規スキルは `<skill-name>/SKILL.md` を必須とする。
- `SKILL.md` には `name` と `description` を含める。
- 新規スキルは system `skill-creator` の `init_skill.py` で初期化する。
- 新規スキルには原則 `agents/openai.yaml` を含め、`default_prompt`で`$<skill-name>`を明示する。
- **スキルを追加・更新したら必ず `README.md` の一覧を更新する。**
- 認証情報・API キー・パスワード・トークンなどの秘匿情報は **絶対に含めない**。
- 外部参照が必要な場合はプレースホルダ（例: `YOUR_API_KEY`）を使用する。
- activeやmirrorへの配備は、validation済みのcommitted SHAからskill directory単位で行う。未commit working treeをsourceにしない。

## 推奨構成

- `SKILL.md`: スキル本体
- `references/`: 参照資料や安全ルール
- `scripts/`: 自動化スクリプト（必要時のみ）
- `assets/`: 画像・テンプレート（必要時のみ）

## 追加手順（簡易）

1. `init_skill.py` でskillと`agents/openai.yaml`を初期化する。
2. 必要に応じて `references/` や `scripts/` を追加する。
3. scriptを実際のfixtureでsmoke testする。
4. `quick_validate.py`、folder/name一致、openai metadata、重複nameを確認する。
5. `README.md` の「収録スキル一覧」を更新する。
6. `git diff --check`とsecret混入がないことを確認する。
