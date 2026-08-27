# Skill deployment contract

## 必須条件

- sourceはgit commitで指定する。
- source working treeのdirtyは公開内容へ影響させない。
- skill folder名とfrontmatter `name`を一致させる。
- validator指定を必須とし、全source skillをvalidateしてからtargetを変更する。
- targetはskill directory単位で扱う。
- activeとmirrorは同じsource commitから生成する。
- git worktree内のtarget skillにtracked、untracked、ignoredの変更があれば置換しない。
- activeとmirrorは別invocationで配備し、間にactive validationとruntime smokeを置く。

## 禁止

- skills root全体への`rsync --delete`
- activeやmirrorをmasterとして編集
- 未commit fileの直接copy
- 既存dirtyのstage/revert
- 走査対象root内へのarchive配置

## rollback

publish scriptのbackupは実行中だけ保持する。apply完了後のrollbackが必要なら、直前のknown-good commitを指定して同じscriptを再実行する。

rollback時もskills root全体や他skillを巻き戻さない。

## commit order

1. source edit / validate
2. source commit
3. committed SHAからactive publish
4. active validation / runtime smoke
5. 同じSHAからmirror publish
6. mirror commit
7. push / PR / CI verify
