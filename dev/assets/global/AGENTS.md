# グローバルAGENTS.md

すべてのprojectでAIが従うglobal invariantを定義する。project固有の手順とskill内部の工程を重複して書かない。

## 言語と日時

- チャット、途中進捗、最終報告は日本語で行う。
- ユーザーが別timezoneを明示しない限り、日時はAsia/Tokyo / JSTとして扱う。

## コア原則

- 変更を可能な限り単純かつ局所的にし、根本原因を解決する。
- 依頼外のrefactor、整形、dead code削除、隣接改善を行わない。
- ユーザーや他agentの既存差分を保持し、巻き戻さない。
- 実環境で証拠を取れる事柄は推測で埋めず、DB、log、CI、deployment、live HTML等で確認する。

## 依頼と権限

- 仮定を明示する。安全に進められる不明点は保守的な仮定で進め、materialな仕様判断だけ確認する。
- より単純な代替案がある場合は、理由とtradeoffを示す。
- `実装して`、`修正して`は、依頼scopeのlocal編集と検証を許可する。
- `すすめて`、`すべてすすめて`、`PR作成まで`は、宣言済みscopeの実装・検証・必要なcommit/push/PR作成までを許可する。
- `すすめて`、`すべて対応する`、`PR作成まですすめて`を、GitHub PR merge、deploy、本番変更の承認として扱わない。明示指示がなければPRがgreenになった時点で止める。
- devの`Integrate`はローカル差分統合であり、GitHub PR mergeを意味しない。
- 破壊的git操作、本番データ変更、deploy、外部送信、ambiguous cleanupは別の明示承認を必要とする。

## コード変更

- 変更行をユーザー依頼へ直接結び付ける。
- 壊れていないものをrefactorしない。
- 既存dead codeは依頼がない限り削除せず、報告に留める。
- 自分の変更で孤立したimport、変数、関数だけ除去する。
- required config追加は、code、fixture、local/prd config、secret反映順、後方互換性、startup readbackを一つの受け入れ条件として扱う。

## 開発フロー

- コード、設定、テスト、ビルド、技術設計、PRD/Todo、CI/CD、runtime障害の調査・実装は`dev`を入口にする。
- 原因未解明の障害は直ちに調査し、原因と期待動作を確認してから実装する。
- 具体的な分類、成果物、worktree、review、verify工程は`dev` skillをsource of truthとし、AGENTSへ再掲しない。
- `dev`フロー自体を変えるときは`update-dev-skills`を使う。
- 新しい定型workflowは、単発commandではなくskillと必要なscript/referenceとして作る。

## subagentとworktree

- 独立したread-only調査、検索、比較、reviewはsubagentへ積極的に委譲する。1 agent 1 taskにする。
- shared filesystemのsubagentには原則writeを委譲しない。
- 並列writeは分離されたworktree、明示write scope、受け入れ条件、検証commandがある場合だけ行う。
- custom Workerのmodel/effort/roleは静的TOMLだけで確定扱いせず、最初のWorkerのruntime metadataで確認する。想定外ならメイン逐次実装へ戻す。

## 完了前の検証

- 依頼を再現可能なtest、validation、readbackへ変換する。
- 変更に近いtestから始め、影響範囲に応じてlint、typecheck、build、UI確認へ広げる。
- 既存baseline failureと今回起因のfailureを分ける。
- mainまたはbaseとのdiffを確認し、scope外変更を除外する。
- 動作確認なしに完了扱いしない。

## push後のcloseout

- pushしたcommit SHAに紐づくGitHub Actionsを確認する。workflowが存在する場合は対象runが`completed/success`になるまで完了報告せず、workflowがなくGitHub側にも対象SHA runがない場合は根拠付きでN/Aとする。
- repo、workflow、remote integration、既知project metadataから実際のdeploy surfaceを確定する。local marker未検出だけでN/Aとせず、Vercel、Cloud Run、Cloudflare等は該当する場合だけ確認する。
- CI/CD failureは今回のdiffとの因果を確認する。今回起因なら修正して再実行し、無関係ならscope外として証拠を示す。
- 権限不足、未login、SHA照合不能は成功扱いせず`unverifiable`と理由を報告する。
- live readback可能な変更は、公開endpoint、DB、log、HTML等で確認する。

報告には次を含める。

- Commit: SHA
- Push: branch / remote
- Pull request: URL / draft or ready
- GitHub Actions: run URL / status / conclusion、またはN/A理由
- Deploy surface: provider / deployment / status、またはN/A理由
- 備考: failure対応、pending、unverifiable、残リスク

## Memoryと自己改善

- session開始時に関連projectの教訓を確認する。
- recurring runの各回結果はautomation memoryまたはdated reportへ保存し、global Memoryには不変手順、状態遷移、再発防止だけを残す。
- 日次no-op、run id、件数snapshotをglobal Memoryの新しいTaskとして増やさない。
- Memory更新はユーザーが明示した場合だけ行い、指定されたextension note経路を使う。
- 同じ失敗が繰り返されたら、AGENTS、skill、project docs、testのうち最も適切なsource of truthへ再発防止を置く。

## cleanup

- cleanup前にcandidate、判定根拠、real diffの有無を確認する。
- metadata-only、already integrated、real diffを区別する。
- ambiguous dirtyを削除しない。
- cleanup後は残存path/worktreeと、求められた場合は容量差を再確認する。
