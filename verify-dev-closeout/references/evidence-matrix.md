# Closeout evidence matrix

## GitHub Actions

- Marker: `.github/workflows/*.yml|yaml`
- Primary key: pushed commit SHA
- Evidence: run URL、status、conclusion、job breakdown
- N/A: workflowが存在せず、GitHub側にも対象SHA runがない

## Vercel

- Marker: `.vercel/project.json`、`vercel.json`、Vercel workflow
- Primary key: `githubCommitSha`
- Evidence: project/scope、deployment URL、Ready/Error、alias
- Readback: preview/production URLのGET、対象route
- 注意: default scopeで0件ならproject/team scopeを確認する

## Cloud Run

- Marker: deploy-cloudrun action、`gcloud run deploy`、Cloud Run service config
- Primary key: image digest / commit label / revision
- Evidence: revision Ready、traffic、startup log、ERROR count
- Readback: service URLの期待status。認証保護時は401/403の意味を明記する

## Cloudflare Workers / Pages

- Marker: `wrangler.toml|json|jsonc`、wrangler workflow
- Primary key: deployment version / commit metadata
- Evidence: deployment status、route/domain、provider log
- Readback: authoritative DNSが関係する場合はauthoritative → recursive resolver → HTTPSの順

## GitHub Pages

- Marker: pages action / pages configuration
- Primary key: workflow runとdeployed artifact
- Evidence: deploy-pages job、公開URL
- Readback: GET statusと期待content

## N/Aとunverifiable

- detectorの`candidate: false`はlocal marker未検出であり、単独では`N/A`の根拠にならない。
- `N/A`: local marker、remote integration、既知project metadata、対象SHAのprovider evidenceを確認し、repoのdelivery surfaceではない根拠がある。
- `unverifiable`: 対象だがauth、権限、metadata不足で証拠を取得できない。
- `pending`: run/deploymentが進行中。

空欄をsuccessとして扱わない。

## 観測対象と完了範囲

| 観測したこと | この証拠だけでは未確認のこと |
| --- | --- |
| HTTP応答・page表示 | 音声agentの準備、入力から送信までの操作、全画面の動作 |
| API smoke・unit test成功 | 実際に変換/送信するpayloadの契約、関連repo・状態遷移の全経路 |
| 設定file作成・localのversion選択 | serviceへの登録、実プロセスの読込、対象環境への反映 |
| 検索結果が空 | 取得失敗や検索範囲の誤りがある場合の不在・削除完了 |
| 比較した一部repo・期間の結果 | 別repo・別期間・異なる粒度/定義での一致 |

必要な受け入れ条件だけを観測する。結果にはrepo/環境、SHAまたはresource/version、対象経路、取得時点、処理の成否を対応付ける。十分な既存検証を再利用し、無関係な全E2Eを増やさない。

結果不明の外部操作は、既存IDや状態をread-onlyで照合する。新しい操作として再送したり、空出力を根拠にrollback成功と報告したりしない。
