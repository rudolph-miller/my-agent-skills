# PRの既定状態をReadyへ統一

## 背景・目的

- 現行dev skillはbroad/high-risk変更を指定なしでdraftにするが、ユーザーの運用方針は指定なしならready。
- 全projectで一貫するよう、global AGENTSとdev skillのPublish手順を揃える。

## Scope

- global AGENTS assetへ「draftの明示がない限りready」を追加する。
- dev skillのdraft既定を同じルールへ置き換える。
- committed sourceからactive global AGENTSとdev skillへ配備する。

## 非目標

- 既存PRのmerge、deploy、本番変更。
- ユーザーが明示したdraft運用や自動生成PR固有の方針を禁止すること。
- runtime model、Worker、他skillの変更。

## 受け入れ条件

- [x] global AGENTSに指定なしreadyの不変ルールがある。
- [x] dev skillに矛盾するdraft既定がない。
- [x] sourceのskill validatorが成功する。
- [ ] sourceをcommit・pushし、同じcommitからactiveへ配備する。
- [ ] active global AGENTSとsource assetが一致する。

## 検証・rollback

- `quick_validate.py`でdevとupdate-dev-skillsを検証する。
- `cmp`でcommitted assetとactiveを比較する。
- rollbackは直前のsource commit `3b8d870`からdev skillとglobal AGENTSを再配備する。

## Review

- 2026-07-27: 指定なしreadyをglobal invariant、具体的なPublish動作をdev skillへ置く。merge/deploy権限は変更しないため進行可。
