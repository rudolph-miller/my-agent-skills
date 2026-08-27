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
