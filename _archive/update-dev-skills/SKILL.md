---
name: update-dev-skills
description: dev フロー関連スキル (dev, dev-codex-inspect, dev-codex-plan, dev-codex-implement, dev-next-action, dev-verify) を、登録済みの全サイトに対して同一内容で同期更新する。「dev スキルを更新したい」「dev フローのルールを変えたい」などと言われたときに使う。
user-invocable: true
disable-model-invocation: false
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Purpose

dev フロー関連スキル群を、登録済みの全サイトに対して **同一内容で** 同期更新する。

dev スキルは複数の場所にミラー配置されている。各サイトを毎回手で指定するのは面倒・抜けが起きるので、このスキルで一括更新する。サイト間で内容差分は許容しない（完全ミラー）。

# Target sites

以下の 5 サイトを対象とする。新しいミラーが増えたらここに追記する。

```
~/.claude/skills
~/.agents/skills
~/projects/my-agent-skills
~/projects/ichi.social/ichi-social-frontend/.claude/skills
~/projects/ichi.social/ichi-social-frontend/.agents/skills
```

各サイト配下の `dev*` ディレクトリのうち、現行フローで使用する
`dev`, `dev-codex-inspect`, `dev-codex-plan`, `dev-codex-implement`, `dev-next-action`, `dev-verify`
が同期対象。旧 wrapper は削除済みとみなし、復活させない。

# Target files

dev フローの説明は skill だけでなく Claude のグローバル設定にも存在する。
そのため、以下のファイルも **補助的な同期対象** として扱う。

```
~/.claude/CLAUDE.md
```

これは 5 サイトにミラーされるファイルではないが、dev フローの入口判断に直接効くため、
`dev` / `dev-codex-inspect` / `dev-codex-plan` などの責務や分岐を変えたときは必ず同時に更新する。

# Workflow

## Step 1: Drift check (必須・最初に実行)

各サイトを比較し、現状のドリフトを把握する。

1. 各サイトに存在する `dev*` ディレクトリ一覧を取得 (`ls -1 <site> | grep '^dev'`)
2. サイト間でディレクトリ集合が一致するか確認
3. 一致しないディレクトリがあれば **欠落・余剰** を列挙して人間に報告
4. 各 `dev*` ディレクトリについて、サイト間でファイル内容が一致するか `diff -rq` で確認
5. ドリフトがあれば **どのサイトが master か** を人間に確認する（自動判定しない）

ドリフトを見つけたら **解消方針を人間に確認してから** Step 2 に進む。勝手に上書きしない。

## Step 2: Master の決定

人間から master サイトの指定を受ける。デフォルト master は `~/projects/my-agent-skills`（agent skills のソースリポジトリ。他サイトはここからの派生ミラー）。ただし更新内容によっては別サイトに最新版がある可能性があるので、毎回確認する。

## Step 3: 更新内容の適用

ユーザーから指示された変更内容を **master サイト** に対してまず適用する。

- ファイル新規作成 → master に Write
- 既存ファイル編集 → master に Edit
- ファイル削除 → master で `rm`（人間に確認してから）
- 新規スキルディレクトリ追加 → master に作成

master に適用後、内容を Read で確認してから Step 4 へ。

dev フローの入口条件・分岐条件・役割分担を変えた場合は、このステップで `~/.claude/CLAUDE.md`
も同時に更新する。特に以下の変更は反映漏れを許容しない。

- `dev` の適用条件
- `dev-codex-inspect` の追加・削除
- `inspect-only` / `inspect-then-plan` / `plan-direct` の分岐
- Claude と Codex の責務変更

## Step 4: 全サイトへ伝播

master の `dev*` ディレクトリを残り 4 サイトに同期する。

- 安全なやり方: `rsync -av --delete <master>/dev<X>/ <site>/dev<X>/` を **対象スキルディレクトリ単位で** 実行する
- `--delete` を使うので、対象は必ず1スキル単位 (`dev-codex-plan/` など) に絞る。サイトのトップ (`skills/`) 全体に `--delete` をかけない。
- スキル新規作成のときは事前に `mkdir -p <site>/<new-skill>` してから rsync
- 削除のときは各サイトでも対応するディレクトリを削除

## Step 5: 検証

伝播後、以下を確認する:

1. 全サイトで現行スキル集合 (`dev`, `dev-codex-inspect`, `dev-codex-plan`, `dev-codex-implement`, `dev-next-action`, `dev-verify`) が一致する
2. master と各サイトで `diff -rq <master>/<skill> <site>/<skill>` が無差分
3. `~/.claude/CLAUDE.md` に最新の dev フロー分岐と役割分担が反映されている
4. 差分が残っているサイトがあれば原因調査して再同期

## Step 6: 人間に報告

以下を簡潔にまとめて報告:

- 変更したスキル名と変更概要
- 適用先サイト一覧（5 サイト）と各サイトの結果 (OK / NG)
- Step 1 で見つけたドリフトの解消結果
- 残課題があれば明記

# Rules

- **完全ミラー前提**: サイト間で内容差分は許容しない。site-specific なルールが必要になった場合は、このスキルの設計を見直してから対応する（勝手に分岐させない）。
- **drift を発見したら必ず人間に報告**: 自動で master を決めて上書きしない。古いほうを master にしてしまうと最新の更新を消す事故になる。
- **`--delete` の使用範囲**: 必ずスキル1個 (`dev-codex-plan/` 等) に絞る。`skills/` 全体に `--delete` をかけない（他のスキルを巻き込む）。
- **旧 wrapper の扱い**: 旧構成の wrapper は削除済みとして扱い、以後同期対象に含めない。
- **削除操作は人間確認必須**: ファイル・スキルディレクトリの削除は、master 側でも各サイト側でも、必ず人間に確認してから実行する。
- **target sites の追加**: 新しいミラー先が増えたら、このファイルの "Target sites" セクションを更新する。
- **`~/.claude/CLAUDE.md` は別系統で維持**: ミラー対象ではないが、dev フロー変更時は必ず一緒に更新・確認する。
