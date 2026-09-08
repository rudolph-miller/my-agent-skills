---
name: verify-dev-closeout
description: commit、push、PR、明示的なmerge/deploy後に、対象SHAのGitHub Actions、実際のdeploy surface、公開endpoint、DB/log/readbackを証拠付きで確認する。変更の確認範囲と未確認の結果を区別し、CI/CD・実配備・live挙動をread-onlyでcloseoutするときに使う。
---

# Verify Dev Closeout

pushやdeployを実行するskillではない。すでに許可された変更のcloseoutをread-only証拠で確認する。

## 手順

1. repo、branch、commit SHA、PR、対象環境、期待するuser-visible outcomeと今回確認する段階を確定する。
2. `scripts/detect_delivery_surfaces.py <repo>`でlocal markerから候補surfaceと根拠を収集する。この結果は候補検出であり、未検出をN/A判定に使わない。
3. `references/evidence-matrix.md`を読み、repo/workflowの実態から対象surfaceを確定する。
4. workflowまたは対象SHA runが存在する場合は、commit SHAに紐づくGitHub Actionsを`completed/success`まで確認する。workflowがなくGitHub側にもrunがなければ、根拠付きでN/Aとする。
5. 今回の承認・変更段階で該当するproviderのdeploymentを同じSHAで確認する。未実施の本番反映と、現在の変更の検証を混同しない。
6. 受け入れ条件に応じて公開endpoint、runtime log、DB/warehouse、HTML等でreadbackし、対象・取得時点・実行結果を対応付ける。
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
- timeout、取得処理の失敗、出力欠落は`unverifiable`とする。成功した取得処理と検索範囲を確認せず、空出力を削除・不在・rollback成功の証拠にしない。
- 設定fileの作成、外部登録、起動、実行、結果確認を区別し、依頼された段階まで確認する。一部の成功を全範囲へ拡張しない。
- 結果不明の外部操作は既存job/resource IDや状態・同じidempotency keyで照合する。再実行や復旧が必要なら、未確認の状態と必要な操作をdevへ返す。
- production deploy、promotion、復旧、再送はこのskillから実行しない。検証の必要性を外部書込みの許可としない。

local markerがないproviderでも、Git integrationやprovider dashboardだけでdeployされる場合がある。`candidate: false`は`not detected locally`を意味し、`N/A`ではない。既知のproject link、remote repository settings、provider CLI/API、過去のdelivery evidenceを確認してからN/Aを決める。

## live readback

変更の性質に応じて最小十分な証拠を選ぶ。

- UI/route: browser表示、console、HTTP status、主要element
- API: status、response contract、server log
- config: revision readiness、traffic、startup log、ERROR count
- DB/warehouse: expected row、aggregation、更新時刻
- LP/CTA: live HTML、最終URL、production row

secret、token、不要なPIIを出力しない。

診断中に変更した設定がある場合はNotesと現在の状態を照合し、残存理由・復旧の要否・復旧済みの証拠を確認する。説明の訂正だけで元の状態へ戻ったと扱わない。

## report

- Commit: SHA
- Push: branch / remote
- Pull request: URL / draft or ready
- GitHub Actions: run URL / status / conclusion、またはN/A理由
- Deploy surface: provider / deployment / status、またはN/A理由
- Live readback: evidence / result
- Notes: 確認済みの範囲、failure対応、pending、unverifiable理由、診断変更の残存/復旧状態
