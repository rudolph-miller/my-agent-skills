# my-agent-skills

このリポジトリは、Codex/AI エージェント向けのスキル集を管理します。
`SKILL.md` を中心に、手順・コマンド例・参照資料を整理します。

## 収録スキル一覧

| スキル名 | 説明 | パス |
| --- | --- | --- |
| `agent-browser` | Web テスト、フォーム入力、スクリーンショット、情報抽出などのブラウザ操作を自動化するスキル。 | `agent-browser/` |
| `gh-cli` | GitHub CLI（`gh`）の安全運用ガイド。破壊的操作は行わない。 | `gh-cli/` |
| `ui-ux-pro-max` | UI/UX スタイル・配色・フォント・UX 指針などの検索ワークフロー。 | `ui-ux-pro-max/` |
| `youtube-music-playlist-reorder` | YouTube Music のプレイリストを指定順に一括並び替えする手順。 | `youtube-music-playlist-reorder/` |
| `dev` | Claude を入口にして、Codex の inspect / plan / implement / verify を分岐させる。 | `dev/` |
| `dev-codex-inspect` | Codex にコード読解・原因調査・影響範囲確認をさせ、実装せずに構造化レポートを返させる。 | `dev-codex-inspect/` |
| `dev-codex-plan` | Codex に調査・PRD / Todo 作成・自己点検・全体設計レビューをさせる。 | `dev-codex-plan/` |
| `dev-codex-implement` | Codex に full-auto で実装または修正を依頼する。 | `dev-codex-implement/` |
| `dev-verify` | 統合済み状態を Codex で検証し、Claude が最終報告を整える。 | `dev-verify/` |
| `dev-next-action` | 次の実装計画を提案する。 | `dev-next-action/` |
