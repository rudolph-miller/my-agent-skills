---
name: config-rollout-guard
description: required config、環境変数、secret、feature flag、schema-backed設定を追加・変更するときに、code・fixture・local/prd config・secret反映順・後方互換性・startup readback・rollbackを一体で検証する。config不足による起動失敗、revision panic、deploy順事故を防ぐ計画・実装・release確認で使う。
---

# Config Rollout Guard

設定変更をcodeだけで完了扱いせず、旧revisionから新revisionまで安全に遷移できるか確認する。

## authorization

- code/config fileの実装はユーザーの開発scopeに従う。
- secret作成・更新、deploy、traffic変更、本番操作は明示承認がある場合だけ行う。
- 承認がない場合も、read-only inventoryと具体的な反映計画までは進める。

## 手順

1. 変更するkey、型、default、required/optional、consumerと既存のconfig管理/loaderを特定し、同じ管理経路へ合わせる。
2. 今回の対象環境と承認された段階を定め、`references/rollout-checklist.md`の該当するmatrixを確認する。既存brief等を使い、非該当項目のために変更を増やさない。
3. 旧code × 新config、新code × 旧config、新code × 新configの互換性を評価する。
4. secret/configとcodeの安全な反映順を決める。
5. 今回差分に必要なfixture、対象環境のconfig/template、validation、docsを実装する。secretやmigrationの必要性、更新する環境も今回のconsumerから判断する。
6. focused test、config parse、対象環境のstartup testを実行する。最終payloadやloaderを通る契約を確認し、設定値を写すだけのtestで済ませない。
7. deployが承認されている場合だけ反映し、revision readiness、traffic、startup log、ERROR count、HTTP probeを確認する。
8. rollback手順とcompensating actionを確認する。

## required configの原則

- 既存revisionが読むshared secretへ新required keyを追加する場合、先にconfigを後方互換な形で配る。
- 新codeだけが読むkeyでも、secret/version rolloutとdeploy順を明示する。
- defaultを置けない理由を説明できないrequired化を避ける。
- validation errorはkey pathと修正方法が分かる形にする。
- production payloadそのものを成果物やログへ転載しない。
- 設定fileに値があることと実プロセスが読み込んだことを区別する。実行中の版・接続先・選択config/versionを秘密値を出さず確認する。
- 既存の起動script等が担う設定読込を、根拠なく別componentへ重複実装しない。テーブル名や環境差も既存の設定管理に合わせる。

## completion criteria

今回の対象環境・承認された段階に必要な次の条件を確認する。未承認の本番操作をlocal変更の完了条件にせず、残る反映段階を分けて報告する。

- code consumerとvalidation
- test fixtureと対象test
- 対象環境のconfig
- productionが対象の場合のconfig/secret反映計画または実施証拠
- compatibility判定
- startup/readiness readback
- deployを実施した場合のcurrent trafficとerror確認
- rollback条件

deploy未承認の場合は、`code ready / production rollout pending`として明確に分ける。

## report

- keyとrequired/optional
- touchpoint matrix
- safe rollout order
- test結果
- production actionの実施/未実施
- runtime readback
- rollbackと残リスク
