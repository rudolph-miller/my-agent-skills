以下の inspect request をもとに、実装は行わず、コード読解と原因調査だけを行ってください。

必須ルール:
- コードを読んで事実を確認すること
- 実装やファイル編集は行わないこと
- PRD / Todo は作らないこと
- 些末な推測ではなく、確認できた事実を優先すること
- 最後に必ず `Recommended Next Action` を `answer-only` / `safe-small-fix` / `plan-needed` のいずれかで示すこと

判定基準:
- `answer-only`: 説明だけで目的が達成される
- `safe-small-fix`: 原因が局所的で、期待動作が明確で、既存パターンに沿って小さく直せる
- `plan-needed`: 複数ファイルにまたがる、設計判断がある、比較や検証計画が必要

出力形式は `references/inspect-template.md` に従ってください。
