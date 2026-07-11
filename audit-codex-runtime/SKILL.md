---
name: audit-codex-runtime
description: Codexのmodel、reasoning effort、custom agent、subagent、worktree task、execution surfaceの実効状態を監査する。devのWorker routingを変更するとき、Codex更新後、TOML/configと実runtimeが一致するか確認するとき、agent roleや子モデルを保証する前に使う。
---

# Audit Codex Runtime

静的configと実runtimeを分けて確認し、観測できた事実だけを報告する。configは変更しない。

## 手順

1. `scripts/audit_runtime.py`でglobal config、custom agent TOML、session JSONLのallowlist情報を収集する。
2. `references/execution-surfaces.md`を読み、利用するsurfaceごとのisolationとmodel controlを確認する。
3. 必要なsurfaceごとに最小のread-only smoke taskを1件実行する。
4. smoke後のsession metadataを再収集し、configuredとobservedを比較する。
5. `verified` / `mismatch` / `not observable` / `unsupported`で判定する。

agent TOMLの出力は、そのfileに宣言された値だけを示す。runtimeへの登録、選択、適用を証明しない。configuredと呼べるのは対象surfaceがそのTOMLを参照することを別途確認した場合で、実効値の証明にはsession metadataを使う。明示したconfig、agent TOML、session、sessions rootが存在しない場合、scriptは黙って無視せず失敗する。

例:

```bash
python scripts/audit_runtime.py \
  --config ~/.codex/config.toml \
  --agent-config ~/.codex/agents/worker.toml \
  --session ~/.codex/sessions/YYYY/MM/DD/rollout-....jsonl \
  --pretty
```

sessionを指定しない場合は、`--sessions-root ~/.codex/sessions --limit 20`で直近候補を読む。

## smoke taskの条件

- ファイル編集、commit、push、外部送信を含めない。
- `現在のmodel、effort、agent role、cwdをruntime metadataから返す`程度の最小taskにする。
- native subagentとisolated worktree Workerを同一surfaceとして扱わない。
- model/role指定を受け付けないtoolへ、存在しないparameterを推測して渡さない。
- session JSONLのprompt、response、base instructions、secretを出力しない。

## evidenceの優先順位

1. 対象child/worktree sessionの`turn_context`と`session_meta`
2. app/task metadata
3. custom agent TOMLとglobal config
4. skill文面や過去Memory

下位証拠だけで上位のruntime事実を断定しない。

## report

- checked_atとruntime/CLI version
- surface名と起動経路
- configured model / effort / role
- observed model / effort / role / cwd
- isolationの確認方法
- verdictとfallback

観測できない場合は「設定上はX、runtimeは未確認」と明記する。mismatch時はwrite Workerを増やさず、メイン逐次実装へ戻す。
