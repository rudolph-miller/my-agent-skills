---
name: update-dev-skills
description: devフロー自体や関連スキル、global指示、Worker定義、配備・mirror・方針Noteを更新するときに使うメンテナンス手順。review済みcommitted sourceから対象を配備し、実際のconsumerが読む版まで照合する。通常のアプリ開発はdevを使う。
---

# Update Dev Skills

devフローの設計変更と公開を、master・active・mirror・global policy・durable Noteの整合性を保って進める。

通常の開発taskへこの更新工程を追加しない。スキル自体の変更・配備を依頼されたときに使い、今回の変更に必要な検証を行う。

## source of truth

masterは`~/projects/my-agent-skills`とする。

作業開始時に、今回編集・validate・commit・publishするmainまたはfeature worktreeの絶対pathを`<source-worktree>`として1つ確定する。以降のsource操作はすべて同じ`<source-worktree>`を使い、dirtyなcanonical main worktreeへ暗黙に戻らない。

主な対象:

```text
~/projects/my-agent-skills/dev/SKILL.md
~/projects/my-agent-skills/dev/assets/agents/worker.toml
~/projects/my-agent-skills/dev/assets/global/AGENTS.md
~/projects/my-agent-skills/update-dev-skills/SKILL.md
~/projects/my-agent-skills/verify-dev-closeout/SKILL.md
~/projects/my-agent-skills/config-rollout-guard/SKILL.md
~/projects/my-agent-skills/cleanup-worktrees/SKILL.md
~/.codex/AGENTS.md
~/.claude/CLAUDE.md
~/.codex/agents/worker.toml
~/projects/myNote/04_Resources/Memos/ClaudeとCodexの開発スタイル方針.md
```

配備先:

- active実体: `~/.agents/skills/<対象skill>`。変更したskillと、その変更が依存するhelperを今回の対象として確定する
- 互換entry: `~/.codex/skills/<skill>` と `~/.claude/skills/<skill>` をactive実体へのsymlinkにする。root directory自体は置換しない
- mirror: `~/projects/ichi.social/ichi-social-frontend/.agents/skills`
- Worker active定義: `~/.codex/agents/worker.toml`

activeやmirrorをmasterとして編集しない。

global指示は既存の管理元を優先する。CLAUDE.mdの管理元がない場合は、全文を公開sourceへコピーせず、今回管理する行だけを`dev/assets/global/claude-policy-lines.json`で管理する。既存の関係ない指示を保持し、秘密値・個人情報をsourceへ取り込まない。

## 変更を分類する

- **Skill-only**: dev内部の分類、成果物、実装、検証手順。
- **Global invariant**: 全projectに効く権限、安全性、完了条件。`~/.codex/AGENTS.md`へ置く。
- **Runtime config**: model、effort、custom agent。config/TOMLへ置き、skill文面へ固定値を重複させない。
- **Durable policy**: 判断理由と履歴。方針Noteへdated sectionとして残す。
- **Reference-only**: 旧Claude Code由来の文脈。active flowへ戻さない。

AGENTSは不変ルールへ絞り、devの工程を再掲しない。Noteは現行方針を冒頭で短く示し、過去sectionを履歴として残す。

## transactional update

### 1. Inspect

- master、active、mirror、global指示、config、Worker TOML、方針Noteの現状を読む。
- 各repoの`git status --short`と`git worktree list --porcelain`を確認する。
- mixed dirtyならcleanなfeature worktreeを作り、既存差分を触らない。
- 変更対象と依存helper、関連global指示、mirror、実consumerのcheckout/skill実体を列挙する。旧mirrorの存在だけで個別不具合の原因と断定しない。
- dev関連一式の更新では`dev`、`update-dev-skills`、`publish-agent-skills`、`audit-codex-runtime`、`verify-dev-closeout`、`config-rollout-guard`と、devが参照する`cleanup-worktrees`を配備単位として確認する。他の無関係なskillは変更しない。
- global指示とdev/helperの矛盾を確認する。provider確認は実deploy surfaceに基づき、failure対応は今回diffとの因果に限定する。
- runtime routing変更では、過去の静的configではなく現在のtool schemaとsession metadataを確認する。

### 2. Plan / Review

- 目的、変更範囲、非目標、受け入れ条件、rollbackを成果物へ書く。
- runtime-sensitive変更はsmoke planを含める。
- reviewが`進行可`になるまでactiveへ配備しない。

### 3. Edit master

- `dev/SKILL.md`を簡潔で手順的に保つ。
- model/effortの固定値をskillとAGENTSへ重複させない。
- custom agent assetを変える場合は、failure policyとruntime検証も更新する。
- 旧`dev-codex-*`の多重フローを復活させない。

### 4. Validate source

最低限、両skillへvalidatorを実行する。

```bash
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py <source-worktree>/dev
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py <source-worktree>/update-dev-skills
```

変更したhelperにも同じvalidatorを実行し、関連reference・README一覧との整合を確認する。今回変更した判断は、必要な実例と対照例で限定的に確認する。validatorだけで挙動を保証したと報告せず、検証用の外部操作を勝手に追加しない。

Worker assetがある場合はTOML parseを確認する。model routingを変更した場合は、利用可能なら`audit-codex-runtime`で隔離smokeを行い、agent role、model、effort、cwd/worktreeをruntime metadataから確認する。

静的configだけでruntime成功と判定しない。smokeが失敗したらreviewを差し戻し、activeへ配備しない。

### 5. Commit source

- `<source-worktree>`で今回scopeだけをstageする。
- validation結果を確認してsource commitを作る。
- `<source-worktree>`がcleanで、commit SHAを取得できる状態にする。
- commit前のworking treeからactiveへ配備しない。

### 6. Publish committed SHA

利用可能なら`publish-agent-skills`を使う。

- `<source-worktree>`で期待commit SHAを`git rev-parse <sha>^{commit}`でき、そのcommitに対象fileが存在することを確認する。feature worktreeやrollback commitを許容し、working tree HEADとの一致は要求しない。
- skill directory単位で、まずactiveへ同期する。
- skills root全体へ`rsync --delete`しない。
- Workerが今回対象なら、assetはsource commitのfileからactive定義へ配備する。
- global AGENTSが今回対象なら、source commitの`dev/assets/global/AGENTS.md`から配備する。working tree外のdraftを直接使わない。
- Claudeの管理行は`scripts/align_claude_policy.py --source-root <source-worktree> --commit <sha> --target ~/.claude/CLAUDE.md`でdry-runし、配備承認済みなら`--apply --backup-dir <走査外backup先>`を追加する。全対象行が旧文面または新文面に一意に一致する場合だけ反映し、その他の内容を保持する。未知・重複は現物を確認し、全文の上書きで解消しない。
- `.codex/skills/<skill>`と`.claude/skills/<skill>`の対象entryがactive実体へのsymlinkであることを確認する。`.codex/skills/.system`等を含むroot directory自体は変更しない。
- activeでvalidatorと必要なruntime smokeを再実行する。

active検証が成功してから、同じsource commitと対象skill一覧をmirrorへ別invocationで同期する。skill、Worker TOML、global指示、方針Noteは単一transactionではないため、配備前に今回対象のsurfaceごとのbackupまたはknown-good commitを確定し、検証とrollback条件を持つ。

active validationまたはruntime smokeが失敗したら、このreleaseで変更したskill、Worker TOML、global指示をそれぞれ直前のbackupまたはknown-good commitから個別に戻し、該当するvalidator、TOML parse、runtime readbackを再確認する。ユーザー差分、skills root全体、今回変更していないsurfaceは巻き戻さない。

### 7. Commit mirror / Note

- mirrorは同じsource commitから同期し、対象skillだけをcommitする。
- 方針Noteは過去sectionを削除せず、新しいdated sectionで現行判断と旧判断のstatusを記録する。
- 各repoの既存dirtyを混ぜない。
- mirror作業branchへのcommitと、実consumerのcheckoutへの到達を区別する。未承認のGitHub mergeは行わず、必要なPRと未反映の状態を報告する。

### 8. Verify publish

- source、active、mirrorの対象directoryを比較する。
- 今回変更したWorker assetとactive TOML、global AGENTS assetとactive fileを比較する。Claudeの管理行は同じcommitで再dry-runし`identical`を確認する。全文hashは今回のbefore/after照合用とし、私的な全文をsourceへ保存しない。
- consumerごとに実体path、symlink解決先、対象fileのhashとcheckoutを確認する。配備先だけでなく、実際に使用するproject内の同名コピーも照合する。
- 更新後の新しいtaskまたは隔離smokeで、意図した版の読込を確認する。routingを変更していなければmodel/effortの再設定はしない。
- pushした各commit SHAのGitHub Actionsを確認する。
- deploy surfaceはrepo/workflowから確定し、非該当はN/Aとする。

## skill discoveryの安全ルール

Codexは`~/.codex/skills`と`~/.agents/skills`を走査する。同名skillが別実体で存在すると暗黙呼び出しが曖昧になる。

- 実体は`~/.agents/skills`の1箇所だけに置く。
- 互換root内の対象skill entryだけをsymlinkにする。root directory自体はsymlink化・置換しない。
- `_archive/`を走査対象skill root配下へ置かない。
- archiveは`~/projects/my-agent-skills/_archive/`など走査外へ置く。

## report

- source commitとbranch、今回の対象skill/helper/関連file
- validation / runtime smoke結果
- active配備、mirror commit、consumer checkout到達を分けた状態と実体/hash照合
- global指示・Worker・方針Noteの変更
- GitHub Actionsと該当deploy surface
- rollback実施有無と残課題
