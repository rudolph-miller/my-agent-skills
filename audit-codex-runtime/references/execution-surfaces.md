# Execution surface evidence

## 判定表

| Surface | Isolation | Model control | 主用途 |
| --- | --- | --- | --- |
| Main thread | 現在のworktree | global/thread config | 統合判断、逐次実装、fallback |
| Collaboration subagent | shared filesystemの場合がある | schemaにmodel/role指定がなければ親継承を想定 | read-only調査、review |
| Worktree task / custom Worker | task固有worktreeを期待 | runtimeがrole選択を受け付ける場合だけ | 独立write group |
| Explicit CLI worker | process/cwdで分離 | CLI flag/configが対応する場合だけ | runtimeが明示指定を保証できる作業 |

## runtimeで確認するfield

- `session_meta.payload.thread_source`
- `session_meta.payload.source.subagent.thread_spawn.agent_role`
- `session_meta.payload.agent_role`（存在するruntimeのみ）
- `session_meta.payload.cwd`
- `session_meta.payload.cli_version`
- 最後の`turn_context.payload.model`
- 最後の`turn_context.payload.effort`
- `turn_context.payload.multi_agent_version`

fieldがない場合は`null`と`未確認`を区別する。

`cwd`は期待するtask固有worktreeの絶対pathと照合する。model、effort、roleが一致しても、通常のmain worktreeを指しているならroutingだけがverifiedで、filesystem isolationはmismatchまたは未確認と判定する。

## mismatch時の扱い

- config値を実効値として言い換えない。
- write taskを新しいchildへ追加しない。
- 既存childの成果はwrite scopeとdiffをreviewする。
- メイン逐次実装、model指定可能な別task、または作業停止から選ぶ。
- runtime update後に再監査する。
