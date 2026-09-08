# Policy and evidence

設定はその回の依頼・既存automationから作り、走査外へ保存する。絶対pathを使う。sourceには個人の候補一覧、private差分、認証情報を保存しない。

各`--output`は新しいfile名を使う。既存file/symlinkを上書きせず、apply前にreport先を確保する。journalは専用の別pathで追記を継続する。

## policy.json

```json
{
  "version": 1,
  "repos": [
    {"path": "/ABS/REPO", "base_ref": "origin/main", "github_repo": "OWNER/REPO", "rules_checked": true}
  ],
  "allowed_roots": ["/ABS/WORKTREE-ROOT"],
  "min_age_seconds": 3600,
  "metadata_paths": [".serena", ".agent-browser"],
  "activity_ignore_components": ["node_modules", ".next", ".turbo", "coverage", "playwright-report", "test-results", ".pnpm-store", "dist", "build", ".cache"],
  "disposable_ignored_components": [],
  "protected_tokens": ["production", "release", "rc", "staging", "deploy", "migration", "infrastructure", "config", "dependency", "lockfile"]
}
```

- `rules_checked`は実際にrepo指示を読んでから設定する。各repoのbaseとremoteを特定し、fetch結果を保存する。scriptはfetchやrefの推測をしない。
- `allowed_roots`とreposの両方で候補を限定する。primary worktree、現在cwdと進行中task、locked/recentは取り込み済みでも残す。
- metadata例外はliteral pathとその配下。wildcardや部分一致ではない。例をそのまま新しい依頼の削除許可として採用しない。
- `activity_ignore_components`はmtime探索だけの除外。`disposable_ignored_components`はその依頼で破棄可能と確認した生成物だけに使う。ignoredな設定や秘密fileを一括して破棄可能にしない。指定済み生成物の内容はfingerprintに含めず、その存在と通常ファイルの差分・mtimeを確認する。
- キーワードはbranchと変更pathの区切りに一致させる。`src`を`rc`として保護しない。統合証拠のない候補の分類にだけ使う。
- indexのassume-unchanged/skip-worktreeで隠れた差分も実fileと照合する。正当なsparse省略は[Gitのcheck-rules](https://git-scm.com/docs/git-sparse-checkout)で区別し、確認不能なGit版・設定ではunknownとして残す。

## activity.json

```json
{
  "checked_at": 1788840000,
  "source": "current task inventory and scoped writer check",
  "complete": true,
  "active_paths": ["/ABS/ACTIVE/WORKTREE"]
}
```

`checked_at`は実際に情報を取得したUnix秒。5分以内のsnapshotを使い、長いrunでは再取得する。ファイルの時刻だけ書き換えて再利用しない。全対象を確認できるtask一覧、または不足候補を補完した確認から作る。取得失敗、上限到達、host不明を`complete: true`へ補完しない。task以外のwriterも候補単位で確認し、分からなければその候補はapplyしない。

## reviews.json

```json
{
  "CANDIDATE_ID": {
    "fingerprint": "FROM_MANIFEST",
    "base": "RESOLVED_BASE_SHA",
    "kind": "superseded",
    "purpose": "候補が実現しようとした要件",
    "source_paths": ["src/old.ts", "src/new.ts"],
    "base_paths": ["src/current.ts"],
    "observations": ["baseのcommit/pathと実装・検証の具体的な照合結果"],
    "index_and_untracked_reviewed": true
  }
}
```

`kind`は`exact_integrated`または`superseded`。ファイル名の存在だけで同等とせず、動作と必要な検証を確認する。`source_paths`はindex・working tree・untracked・ignoredを含む差分の全pathを覆う。metadataも実差分も同じfingerprintに結び付く。再inspectでHEAD/base/実体/差分が変われば旧reviewは無効。レビュー記録は統合証拠であり、削除の新しい承認ではない。

## 再開と記録

manifestのrun_idと候補IDを同じjournalで継続する。repoの共通gitdirに置くflockはcleanup間の同時実行を防ぐ。journalは候補外へ置き、開始行のwrite/fsyncに失敗したらremoveしない。

- `started`: 対象、fingerprint、分類、統合証拠、status、du、df beforeを記録済み。
- `command_returned`: Gitのexit codeを観測済み。
- `removed`: exit 0とpath/登録不在を確認済み。
- `already_verified`: 同じrunで削除成功を記録済み。新しい成功件数へ加算しない。
- `absent_operation_unknown`: 中断記録があり、現在path/登録がない。誰が削除したか・操作成否は未確認のまま保持する。

各applyのdu合計は今回`removed`の候補だけ。日次累計はjournalの`run_id + candidate`を重複排除して集計し、異なるrepoや追加scan対象を混同しない。`df`は同時書込みを含む実測差で、duとは別の値。
