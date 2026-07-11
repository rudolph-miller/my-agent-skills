---
name: memory-curator
description: Codex Memoryをread-only監査し、重複Task、日次no-op、時点依存snapshot、切れたrollout参照、AGENTSやskillへ昇格すべき不変ルールを分類する。ユーザーが「メモリーを整理」「不要な記憶を減らす」「AGENTSへ上げる」「最近のログからMemoryを改善」と依頼したときに使う。
---

# Memory Curator

raw rolloutを証跡として保持し、activeな`MEMORY.md`を検索索引・不変知識中心へ保つ。既定はread-onlyとする。

## 手順

1. memory summaryと`MEMORY.md`の対象範囲を確認する。
2. `scripts/audit_memory.py`でgroup/task/rollout inventory、重複候補、snapshot密度、参照切れを集計する。script出力はgroup titleとrollout filenameをfingerprint化する。
3. `references/curation-policy.md`で`keep` / `merge` / `demote` / `remove-from-index` / `promote`へ分類する。
4. 高優先候補だけ原文とrollout summaryをspot checkする。
5. 根拠lineとrollout idを含む整理案を返す。

例:

```bash
python scripts/audit_memory.py ~/.codex/memories/MEMORY.md --format markdown --top 20
```

## write boundary

- ユーザーがMemory更新を明示しない限り、ファイルを変更しない。
- 明示依頼があっても`MEMORY.md`、`memory_summary.md`、rollout summaryを直接編集しない。
- 更新は`~/.codex/memories/extensions/ad_hoc/notes/<timestamp>-<slug>.md`へ小さいdirective noteを1件作る。
- raw rolloutを削除しない。
- live status、価格、件数、SHA、PR、revision、secret versionをdurable truthとして固定しない。

## report

- inventory件数
- 保持すべき高価値ルール
- merge候補と代表Task
- snapshotへ降格する値の種類
- active indexから外す候補
- AGENTS / skill / automation memory / project artifactへの移動先
- 実施する場合のextension note案

「削除」は原則としてactive indexから外す意味で使い、証跡削除と区別する。
