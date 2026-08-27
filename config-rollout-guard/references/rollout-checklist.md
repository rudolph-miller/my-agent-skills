# Config rollout checklist

## Touchpoint matrix

| Surface | 確認内容 | Evidence |
| --- | --- | --- |
| Type / schema | key、型、nullable、default | source path / schema diff |
| Validation | required条件、error message | unit test |
| Consumer | startup時かrequest時か、fallback | source path |
| Test fixture | valid / missing / malformed | test result |
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

1. failed/current revisionの状態
2. new revision readiness
3. traffic split
4. secret/config version freshness
5. startup success log
6. checked windowのERROR count
7. authを考慮したHTTP probe
8. rollback可能なprevious revision

HTTP 401/403でも、認証保護されたendpointならprocess aliveの補助証拠になりうる。期待statusと区別して報告する。
