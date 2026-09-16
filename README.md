# Railcar Wire

北米貨車リース・北米鉄道業界・海上コンテナリース・欧州貨車リース・オルタナ投資のニュースを英語ソースから自動収集し、各記事に日本語の要点3点を付けて一覧表示するダッシュボードです。貨車リースとコンテナリースは各社の決算発表・人事・規制当局のリリースも収集対象です。

- 収集: 毎日 06:00 / 13:00（米国東部時間、夏時間・冬時間は自動対応）
- 実行基盤: Claude Code のクラウド定期実行（routine）。お使いのClaudeプランの範囲で動き、PCの起動も追加課金も不要
- 公開: GitHub Pages（無料）。push を受けた GitHub Actions が自動デプロイ
- 表示: 各記事に日本語の要点3点、見出しクリックで原文へ。決算・人事・規制当局の記事にはバッジ

## 仕組み

```
Claude Code routine (cloud, 06:00 / 13:00 ET)
  ├─ このリポジトリを clone
  ├─ WebSearch / WebFetch で収集・要約 → data/news.json に追記
  ├─ python3 scripts/build_site.py → dist/index.html
  └─ git push origin main（拒否時は claude/news-update ブランチ）
GitHub Actions (.github/workflows/publish.yml)
  └─ push を検知 → main を同期 → dist/ を GitHub Pages に公開
```

| ファイル | 役割 |
|---|---|
| `docs/routine-prompt.md` | routine に登録しているプロンプトの控え（カテゴリ・検索方針・要約ルールはここ） |
| `scripts/build_site.py` | `data/news.json` → `dist/index.html`（標準ライブラリのみ） |
| `templates/site_template.html` | ダッシュボードのHTML/CSS/JS |
| `data/news.json` | 収集済み記事（URLで重複排除、公開日から30日で自動削除） |
| `.github/workflows/publish.yml` | GitHub Pages への公開ワークフロー（Secret不要） |
| `docs/setup.md` | 初回セットアップ手順（一度だけ必要な操作） |

記事1件のスキーマ:

```json
{
  "category": "railcar_leasing | rail_industry | container_leasing | eu_railcar_leasing | alt_investment",
  "kind": "news | earnings | personnel | regulatory",
  "title": "英語見出し", "source": "媒体名", "url": "記事URL",
  "published_at": "YYYY-MM-DD または null",
  "summary_ja": ["要点1", "要点2", "要点3"],
  "collected_at": "ISO8601（太平洋時間）"
}
```

## 初回セットアップ

[docs/setup.md](docs/setup.md) を参照。必要なのは (1) GitHubリポジトリの作成とpush、(2) Claude の GitHub 連携でこのリポジトリを許可、(3) GitHub Pages の有効化、(4) routine の登録、の4点です。

## 手動更新

- routine を今すぐ動かす: https://claude.ai/code/routines で「Run now」（時間外チェックがあるので、手動実行時は「時間外でも実行」と一言添えたプロンプトで動かすか、Claude Code のセッションで `RemoteTrigger` の `run` を使う）
- サイトだけ再公開: GitHub の Actions タブ →「Publish site」→「Run workflow」
- ローカルで再生成: `python3 scripts/build_site.py`

## 調整できる項目

- カテゴリ・検索対象・件数の上限・要約ルール: `docs/routine-prompt.md` を編集し、routine 本体にも反映
- モデル: routine の `session_context.model`（既定 `claude-sonnet-5`）
- 収集時刻: routine の cron（UTC）と、プロンプト冒頭の時刻チェック
