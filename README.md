# my-agent-skills

このリポジトリは、Codex/AI エージェント向けのスキル集を管理します。
`SKILL.md` を中心に、手順・コマンド例・参照資料を整理します。

## 収録スキル一覧

| スキル名 | 説明 | パス |
| --- | --- | --- |
| `agent-browser` | Web テスト、フォーム入力、スクリーンショット、情報抽出などのブラウザ操作を自動化するスキル。 | `agent-browser/` |
| `agent-browser-google-auth` | localhostのGoogleログイン状態を保存・復元してブラウザテストを行う。 | `agent-browser-google-auth/` |
| `audit-codex-runtime` | Codexのmodel・effort・agent roleをruntime証拠で監査する。 | `audit-codex-runtime/` |
| `config-rollout-guard` | 対象環境の設定管理・実consumerと契約、互換性、反映順、起動確認を検証する。 | `config-rollout-guard/` |
| `dev` | 元の要件・承認・指摘を保持し、必要な差分の実装から検証・PR作成まで進めるCodex開発フロー。 | `dev/` |
| `gh-cli` | GitHub CLI（`gh`）の安全運用ガイド。破壊的操作は行わない。 | `gh-cli/` |
| `memory-curator` | Codex Memoryを重複・snapshot・不変知識に分類して整理提案する。 | `memory-curator/` |
| `publish-agent-skills` | committed SHAからskillをactiveとmirrorへ安全に配備・照合する。 | `publish-agent-skills/` |
| `ui-ux-pro-max` | UI/UX スタイル・配色・フォント・UX 指針などの検索ワークフロー。 | `ui-ux-pro-max/` |
| `update-dev-skills` | dev自体と関連スキル・global指示を更新/配備し、実consumerが読む版まで照合する。 | `update-dev-skills/` |
| `verify-dev-closeout` | 対象SHAのCI/CD・実配備・live挙動を確認し、検証範囲と未確認の結果を区別する。 | `verify-dev-closeout/` |
| `youtube-music-playlist-reorder` | YouTube Music のプレイリストを指定順に一括並び替えする手順。 | `youtube-music-playlist-reorder/` |
