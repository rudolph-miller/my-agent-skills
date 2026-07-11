---
name: verify-dev-closeout
description: commit、push、PR、明示的なmerge/deploy後に、対象SHAのGitHub Actions、実際のdeploy surface、公開endpoint、DB/log/readbackを証拠付きで確認する。Vercelを全repoへ決め打ちせず、GitHub Actions、Vercel、Cloud Run、Cloudflare、GitHub Pages等を検出してsuccess/fail/N/Aでcloseoutするときに使う。
---

# Verify Dev Closeout

pushやdeployを実行するskillではない。すでに許可された変更のcloseoutをread-only証拠で確認する。

## 手順

1. repo、branch、commit SHA、PR、期待するuser-visible outcomeを確定する。
2. `scripts/detect_delivery_surfaces.py <repo>`でlocal markerから候補surfaceと根拠を収集する。この結果は候補検出であり、未検出をN/A判定に使わない。
3. `references/evidence-matrix.md`を読み、repo/workflowの実態から対象surfaceを確定する。
4. workflowまたは対象SHA runが存在する場合は、commit SHAに紐づくGitHub Actionsを`completed/success`まで確認する。workflowがなくGitHub側にもrunがなければ、根拠付きでN/Aとする。
5. 該当providerのdeploymentを同じSHAで確認する。
6. 可能な場合は公開endpoint、runtime log、DB/warehouse、HTML等でreadbackする。
7. 各surfaceを`success` / `fail` / `pending` / `N/A` / `unverifiable`で報告する。

例:

```bash
python scripts/detect_delivery_surfaces.py /path/to/repo --pretty
gh run list --commit <sha> --limit 20 --json databaseId,status,conclusion,url,workflowName,headSha
```

## 判定ルール

- GitHub Actionsはbranch最新runではなく対象SHAで照合する。
- Vercelはproject link、workflow、既知project metadataがある場合だけ確認する。
- Cloud Run/Cloudflare等もworkflowやprovider markerがある場合だけ確認する。
- markerだけではdeploy済みと断定せず、live provider evidenceを取る。
- CI failureは今回のdiffとの因果を確認する。無関係な既存failureをscope外修正しない。
- provider未ログイン、権限不足、deployment SHAを照合できない場合は成功扱いせず`unverifiable`にする。
- production deployやpromotionは、このskillから実行しない。

local markerがないproviderでも、Git integrationやprovider dashboardだけでdeployされる場合がある。`candidate: false`は`not detected locally`を意味し、`N/A`ではない。既知のproject link、remote repository settings、provider CLI/API、過去のdelivery evidenceを確認してからN/Aを決める。

## live readback

変更の性質に応じて最小十分な証拠を選ぶ。

- UI/route: browser表示、console、HTTP status、主要element
- API: status、response contract、server log
- config: revision readiness、traffic、startup log、ERROR count
- DB/warehouse: expected row、aggregation、更新時刻
- LP/CTA: live HTML、最終URL、production row

secret、token、不要なPIIを出力しない。

## report

- Commit: SHA
- Push: branch / remote
- Pull request: URL / draft or ready
- GitHub Actions: run URL / status / conclusion、またはN/A理由
- Deploy surface: provider / deployment / status、またはN/A理由
- Live readback: evidence / result
- Notes: failure対応、pending、unverifiable理由
