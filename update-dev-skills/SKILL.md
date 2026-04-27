---
name: update-dev-skills
description: Codex用のdev開発フローと関連するグローバル指示を更新する。devスキル、devフロー、inspect/plan/review/worktree並列実装/merge/verify、または旧Claude Code devスキルのCodex移植を変更したいときに使う。
metadata:
  short-description: Codex devフロー更新
---

# Update Dev Skills

## 目的

Codex-only の `dev` 開発フローを、スキル本体・グローバル指示・永続Noteの整合性を保ちながら更新する。

現在の前提:

- Codex を唯一の入口にする
- 開発入口は `dev` スキルに統一する
- 役割は Orchestrator / Inspector / Planner / Reviewer / Worker / Verifier に分ける
- 標準フローは `inspect -> PRD/Todo -> review -> worktree実装 -> merge -> verify`
- チャット、報告、PRD、Todo、review、verify 成果物は原則日本語で作成する

## 主な更新対象

`dev` フローを変えるときは、必要に応じて次を一緒に更新する。`~/.codex/skills` を master とし、Codex版の active skill を各ミラーへ同期する。

```text
~/.codex/skills/dev/SKILL.md
~/.codex/skills/update-dev-skills/SKILL.md
~/.codex/AGENTS.md
~/projects/myNote/04_Resources/Memos/ClaudeとCodexの開発スタイル方針.md
```

方針Noteは過去版を消さない。大きな変更では dated section を追加し、小さな補足では最新セクションに追記する。

## Codex版スキルの同期先

Codex版の active skill は、次の場所に同一内容で配置する。

```text
~/.codex/skills
~/projects/my-agent-skills
~/projects/ichi.social/ichi-social-frontend/.claude/skills
~/projects/ichi.social/ichi-social-frontend/.agents/skills
```

同期対象:

```text
dev
update-dev-skills
```

`~/.codex/skills` を master として、各 skill ディレクトリ単位で同期する。`skills/` root 全体に `--delete` をかけない。

同期後、次の repo では必ず commit する。

```text
~/projects/my-agent-skills
~/projects/ichi.social/ichi-social-frontend
```

## 旧 Claude Code 由来の参照元

旧 Claude Code dev 系スキルは `_archive/` に退避されている場合がある。

```text
~/projects/my-agent-skills/_archive/
~/projects/ichi.social/ichi-social-frontend/.claude/skills/_archive/
~/projects/ichi.social/ichi-social-frontend/.agents/skills/_archive/
```

これらは参照専用。ユーザーが明示しない限り、旧 multi-skill の Claude + Codex フローを復活させない。

## 更新手順

1. **現状確認**
   - `~/.codex/skills/dev/SKILL.md` を読む
   - `~/.codex/skills/update-dev-skills/SKILL.md` を読む
   - `~/.codex/AGENTS.md` の `dev` 関連セクションを読む
   - 方針Noteの最新 dated section を読む
   - 旧 Claude の挙動に関係する依頼なら、該当する `_archive/` スキルを参照する

2. **変更種別の分類**
   - Skill-only: `dev/SKILL.md` だけに入れるべき手順
   - Global rule: 全プロジェクトに効くため `~/.codex/AGENTS.md` に入れるべきルール
   - Durable policy: 方針として残すため Note に書くべき判断
   - Reference-only: 旧 Claude 由来の文脈として見るが、標準フローには戻さない内容

3. **編集**
   - `dev/SKILL.md` は簡潔で手順的に保つ
   - `AGENTS.md` はデフォルト行動とルールに絞る
   - Note は判断理由が後から読めるように書く
   - 旧 Claude 前提は Codex 前提に置き換える
   - 用語は Codex Orchestrator / Inspector / Planner / Reviewer / Worker / Verifier を優先する
   - PRD / Todo / review / verify 成果物が日本語になるよう、言語ルールを崩さない

4. **検証**
   - スキルバリデーションを実行する

```bash
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/dev
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/update-dev-skills
```

   - 変更箇所を読み返す
   - 旧 Claude Code フローを誤って復活させていないか確認する

5. **ミラー同期**
   - `~/.codex/skills/dev/` を各同期先の `dev/` へ同期する
   - `~/.codex/skills/update-dev-skills/` を各同期先の `update-dev-skills/` へ同期する
   - `rsync --delete` を使う場合は、必ず skill ディレクトリ単位に限定する
   - 同期後に `my-agent-skills` と `ichi-social-frontend` の差分を確認する

6. **commit**
   - `~/projects/my-agent-skills` で同期差分を commit する
   - `~/projects/ichi.social/ichi-social-frontend` で同期差分を commit する
   - commit 前に `git status --short` を確認し、dev skill 同期以外の差分が混ざる場合は報告する

7. **報告**
   - 変更したファイル
   - バリデーション結果
   - ミラー同期先
   - commit hash
   - 参照した archive の有無
   - 残課題があれば明記する

## 移植ルール

- `Claude` が orchestrator になる記述は `Codex Orchestrator` に置き換える
- `dev-codex-*` サブスキルは原則 `dev` 内の役割に吸収する
- 明確な理由がある場合だけ、別の Codex スキルとして分離する
- inspect note、PRD、Todo、review note、verify note による成果物ハンドオフを維持する
- worktree による並列実装を維持する
- 明示的に worktree を作る場合は repo-local を優先する

```text
<repo>/.codex/worktrees/<task-slug>/<group-name>
```

- `~/.codex/worktrees/{hash}/{repo}` は runtime 管理の場所として扱い、明示作成時の推奨先にはしない
- 旧 Claude Code dev 系スキルは `_archive/` に残し、active な Codex版 `dev` / `update-dev-skills` とは混ぜない

## 安全ルール

- ユーザーが明示しない限り `_archive/` は削除しない
- skills root 全体に `rsync --delete` をかけない
- グローバル指示は、現在の内容を読んでから編集する
- 対象 repo に未コミット変更がある場合は保持し、報告する
