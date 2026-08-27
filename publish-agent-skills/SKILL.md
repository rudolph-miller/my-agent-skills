---
name: publish-agent-skills
description: Git管理されたmasterのcommitted SHAから、Codex skillをactive rootとproject mirrorへ安全に配備・照合する。skill更新の公開、master/active/mirror不一致の解消、未commit版の部分配備防止、skill directory単位のatomic syncとrollbackが必要なときに使う。
---

# Publish Agent Skills

working treeではなく、明示したgit commitのarchiveを公開する。既定はdry-runとし、ユーザーが配備を明示した場合だけ`--apply`を使う。

## preflight

1. source repo、commit SHA、skill名、active root、mirror rootを確定する。
2. 各repoのdirtyを確認し、対象外差分をstage/revertしない。
3. source commitに対象skillが含まれ、validation済みであることを確認する。
4. `references/deployment-contract.md`を読む。

## dry-run

```bash
python scripts/publish_skills.py \
  --source-root ~/projects/my-agent-skills \
  --commit <sha> \
  --skill dev \
  --skill update-dev-skills \
  --target-root ~/.agents/skills \
  --validator ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py
```

出力のresolved source SHA、targetごとの`missing` / `different` / `identical`を確認する。

## apply

同じ引数へ`--apply`を追加する。1回の実行で変更するtarget rootは1つだけにする。scriptは次を行う。

- `git archive <sha>`からskill directoryだけを抽出する。
- 全skillをvalidateしてからtargetへ触る。
- targetがgit worktree内なら、対象skillにtracked、untracked、ignoredの変更がないことを確認する。dirtyなら何も置換せず停止する。
- targetごとにstagingとbackupを作り、skill directory単位でreplaceする。
- 全targetのhash一致を確認する。
- 途中失敗時は、この実行で置換したskillだけbackupから戻す。

skills root全体を削除・同期しない。

activeへapplyした後は、active validationと必要なruntime smokeを完了させる。その後、同じsource commitとskill一覧でmirrorを別実行する。activeとmirrorを同じinvocationで変更しない。

## related files

custom agent TOMLなどskill directory外のfileは、同じsource commitから`git show <sha>:<path>`で取り出し、targetへ配備する。working treeのfileを直接コピーしない。配備後にhashまたは`cmp`で照合する。

scriptのatomic rollbackは、1回のinvocationで扱うskill directoryだけを保証する。Worker TOML、global AGENTS、方針Note、別invocationのmirror配備は同じtransactionに含まれないため、それぞれ事前backup、検証、個別rollback条件を持つ。

## mirror commit

- mirror worktreeでは同期対象skillだけをstageする。
- source commit SHAをcommit/PR本文へ記録する。
- project-localな別設定やdirtyを混ぜない。
- mirror commit後にsource archiveとのhash一致を再確認する。

## discovery check

- active実体を1箇所にする。
- `~/.codex/skills/<skill>`や`~/.claude/skills/<skill>`の対象entryをactive実体へのsymlinkにする。root directory自体は置換しない。
- 同名skillの別実体、broken symlink、走査root内archiveがないことを確認する。

## report

- source repo / branch / commit SHA
- published skill一覧
- active / mirror target
- validationとhash照合
- related fileとsymlink状態
- mirror commit / PR / CI
- rollback実施有無
