# Railcar Wire

北米貨車リース・北米鉄道業界・海上コンテナリース・欧州貨車リース・オルタナ投資のニュースを英語ソースから自動収集し、各記事に日本語の要点3点を付けて一覧表示するダッシュボードです。貨車リースとコンテナリースは各社の決算発表・人事・規制当局のリリースも収集対象です。

- 収集: 毎日 06:00 / 13:00（米国東部時間、夏時間・冬時間は自動対応）
- 実行基盤: Claude Code のクラウド定期実行（routine）。お使いのClaudeプランの範囲で動き、PCの起動も追加課金も不要
- 公開: GitHub Pages（無料）。push を受けた GitHub Actions が自動デプロイ
- 表示: 各記事に日本語の要点3点、見出しクリックで原文へ。決算・人事・規制当局の記事にはバッジ

## 仕組み

```
GitHub Actions (.github/workflows/collect-candidates.yml, 1日4回)
  └─ scripts/collect_candidates.py
       業界メディアRSS・Google News検索・SEC EDGAR 8-K・Federal Register から
       発行日付きの候補記事を集め、本文抜粋を付けて data/candidates.json にコミット
Claude Code routine (cloud, 06:00 / 13:00 ET)
  ├─ このリポジトリを clone、scripts/list_candidates.py で候補を確認
  ├─ 候補（＋補助的に WebSearch）から選別し、日本語の要点3点を作成 → data/news.json に追記
  ├─ python3 scripts/build_site.py → dist/index.html
  └─ git push origin main（拒否時は claude/news-update ブランチ）
GitHub Actions (.github/workflows/publish.yml)
  └─ push を検知 → main を同期 → dist/ を GitHub Pages に公開
```

収集元をAIの検索任せにせず、GitHub Actions 側で決定的に集める理由は、クラウド routine の環境では多くのニュースサイトへの直接アクセスが遮断され、検索エンジン経由だけでは貨車リース・コンテナリースのような専門分野の新着記事を取りこぼすためです。

| ファイル | 役割 |
|---|---|
| `docs/routine-prompt.md` | routine に登録しているプロンプトの控え（カテゴリ・選別方針・要約ルールはここ） |
| `scripts/collect_candidates.py` | 候補記事の収集（RSS / Google News / EDGAR / Federal Register の一覧と検索クエリはここ） |
| `scripts/list_candidates.py` | 候補の一覧表示（routine が最初に実行） |
| `data/candidates.json` | 直近30日の候補記事（発行日・カテゴリ目安・本文抜粋）。Actions が自動更新 |
| `.github/workflows/collect-candidates.yml` | 候補収集ワークフロー（UTC 03:15 / 09:15 / 16:15 / 21:15） |
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
- 候補だけ今すぐ集め直す: Actions タブ →「Collect candidates」→「Run workflow」
- サイトだけ再公開: Actions タブ →「Publish site」→「Run workflow」
- ローカルで再生成: `python3 scripts/build_site.py`

## 調整できる項目

- 収集元（RSS・検索クエリ・対象企業のCIK）: `scripts/collect_candidates.py` の `RSS_FEEDS` / `GNEWS_QUERIES` / `EDGAR_COMPANIES`
- カテゴリ・件数の上限・要約ルール: `docs/routine-prompt.md` を編集し、routine 本体にも反映
- モデル: routine の `session_context.model`（既定 `claude-opus-5`。利用枠を抑えたい場合は `claude-sonnet-5`）
- 収集時刻: routine の cron（UTC）と、プロンプト冒頭の時刻チェック
