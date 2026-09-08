---
name: cleanup-worktrees
description: マージ済み・取り込み済み・後続実装に置換済みのGit worktreeを、依頼された範囲で調査・削除するときに使う。定期cleanupと単発cleanupで同じscriptを使い、active除外、実差分と統合証拠の再照合、同時実行防止、削除結果と容量の記録を行う。
---

# Cleanup Worktrees

定期実行と単発依頼の共通入口。skillの存在やmanifestは削除権限を意味しない。対象repo/path、例外、削除、必要なPR/mergeの権限は現在の依頼・automationから引き継ぐ。通常のdev完了時に自動では呼ばない。

## Inspect

1. 現在の依頼・automationを読み、対象repo、追加scan root、比較ref、活動除外、metadata例外、容量報告、PRの扱いを確定する。scriptの既定値から削除範囲を拡大しない。
2. `scripts/cleanup_worktrees.py discover --repo <repo> --root <追加root>`で候補を列挙する。repo/rootは繰り返し指定できる。登録されたprimary worktreeは削除対象にしない。
3. 各repoのAGENTS・remote・default/base refを確認し、許可されているfetchを行う。既存automationが`origin/main`を指定し、そのrefがない場合はそのrepoを要確認として残す。別refへ無断で置き換えない。他repoの確認は続ける。
4. [policyと証拠の形式](references/policy-and-evidence.md)に従い、今回のpolicyとactive-task snapshotを走査外のdated report先に保存する。現在cwd、進行中task、locked worktreeを保護する。task一覧が不完全なら未掲載をinactiveとせず、範囲を満たす取得または候補ごとの確認を行う。
5. 共通scriptでinspectする。

```bash
python3 scripts/cleanup_worktrees.py inspect \
  --policy <policy.json> --activity <activity.json> --output <manifest.json>
```

HEAD時刻と実ファイルmtimeに基づくrecent除外を最初に行う。生成物のmtime除外と内容を捨てる許可は別の設定として扱う。未登録、base解決失敗、Git/PR取得失敗はunknownであり、空差分や未統合の証拠にしない。

## 残る差分の比較

- `eligible`は取得した証拠で取り込みを確認できた候補。保護キーワードだけを理由に統合済み候補を残さない。
- `review_required` / `protected`は未統合と確定した件数ではない。依頼が詳細比較を含む場合はclean/dirtyの両方について、変更目的、HEAD/index/working tree/untracked/ignored、base側の実装を比較する。単純なhash不一致で作業を終えない。
- GitHub PRは現在HEADと`headRefOid`、merge commitのbaseへの包含を確認する。branch名とMERGED状態だけでは、PR後の追加commitを捨てない。
- exactは追加・変更内容、削除pathの不在、renameの両path、indexの独自変更を確認する。supersededはbaseの該当path、置換された要件、実装・依存・必要な検証から同等以上の動作を確認し、古い差分の再適用が不要となる根拠を記録する。
- 根拠が揃った場合だけreviewsへ書き、`--reviews <reviews.json>`付きで再inspectする。曖昧な実差分は保持する。PR化が必要ならdevへ戻り、現在の承認条件とCIを満たす。cleanup scriptはPR作成・merge・deployを行わない。

## Applyとreadback

1. policyが現在の許可範囲と一致し、active snapshotが有効で、同じworktreeに別のwriterがいないことを確認する。repo lockはcleanup同士の排他であり、通常のeditorや別agentの書込みを止めるlockではない。並行writeがある、または停止を確認できない候補にはapplyしない。
2. 既に削除が承認された候補IDだけ指定する。既存の同じscopeの承認を再度求めない。

```bash
python3 scripts/cleanup_worktrees.py apply \
  --policy <policy.json> --activity <activity.json> --manifest <manifest.json> \
  --candidate <id> --journal <走査外run.jsonl> --output <result.json> --allow-delete
```

`--candidate`は繰り返し指定できる。reviewによる候補は同じ`--reviews`も指定する。scriptはrepoごとのlock内で登録・realpath・HEAD/base・index/実差分・活動状況・許可policyを再照合し、`du`と開始記録を永続化してから削除する。cleanは通常remove、確認済みmetadata/実差分だけforceを使う。変更された候補は再inspectへ戻す。root/branchの削除、skills root等の一括削除、無条件のforceは行わない。

3. 中断・timeout・結果欠落があれば同じmanifest/journalを保持し、`--resume`で現存pathと登録を照合する。`absent_operation_unknown`は「消失を確認、操作結果不明」であり、削除成功件数へ補完しない。journalが壊れている場合は自動再送せず、既存記録と実体を照合する。
4. 削除後は登録とpathの不在を確認する。既存指示がpruneを含む場合はdry-runで対象を確認し、今回確認できたstale登録だけ処理する。実差分を含む別pathへcleanupを拡張しない。
5. policyとactive情報を更新して再inspectし、安全確認済みの残存を説明する。errorやreview待ちを0件・完了に読み替えない。

## 報告

repo別に、実際の削除件数と分類、残したrecent/active/review/unknown、必要なPRとCIを報告する。容量は記録済みdu合計とdf実測差を分け、同時書込み等で一致しなくても削除量へ補正しない。追加scan対象・一時probeは通常集計と区別し、realpath/候補IDで重複計上しない。journal、manifest、結果のpathを残す。
