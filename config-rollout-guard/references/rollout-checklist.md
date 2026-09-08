# Config rollout checklist

## Touchpoint matrix

今回のconsumerと対象環境に該当する項目を、既存brief等で確認する。非該当の環境・secret・migrationまで変更対象へ増やさない。

| Surface | 確認内容 | Evidence |
| --- | --- | --- |
| Type / schema | key、型、nullable、default | source path / schema diff |
| Validation | required条件、error message | unit test |
| Consumer | 既存loader/設定管理、startup時かrequest時か、fallback | source path |
| Test fixture | valid / missing / malformed、最終payloadの必須項目 | 実際の変換/loader経路を通るtest result |
| Local config | developer起動に必要か | parse/startup result |
| Production template | encrypted/config sourceとの対応 | path / version metadata |
| Secret manager | key存在、version、enabled | metadataのみ |
| Deploy workflow | secret refreshとimage deploy順 | workflow path |
| Runtime | readiness、traffic、startup log | live evidence |
| Rollback | old revision/configとの互換性 | rollback command/condition |

## Compatibility matrix

| Code | Config | Expected |
| --- | --- | --- |
| old | old | 現状維持 |
| old | new | 旧codeが未知keyを無視できる |
| new | old | required key不足時の挙動を明示 |
| new | new | 期待動作 |

`new code × old config`が起動不能なら、config先行または段階的optional化を使う。

## Runtime closeout

以下は今回反映する環境で該当するものを確認する。localだけの変更ではlocalのparse/startupと期待動作を確認し、本番traffic確認を必須にしない。fileの存在と実プロセスの読込を区別し、実行中の版・選択config/versionを照合する。

1. failed/current revisionの状態
2. new revision readiness
3. traffic split
4. secret/config version freshness
5. startup success log
6. checked windowのERROR count
7. authを考慮したHTTP probe
8. rollback可能なprevious revision

HTTP 401/403でも、認証保護されたendpointならprocess aliveの補助証拠になりうる。期待statusと区別して報告する。
