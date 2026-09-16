# Railcar Wire

北米貨車リース・北米鉄道業界・海上コンテナリース・欧州貨車リース・オルタナ投資のニュースを英語ソースから自動収集し、各記事に日本語の要点3点を付けて一覧表示するダッシュボードです。貨車リースとコンテナリースは各社の決算発表・人事・規制当局のリリースも収集対象です。

- 収集: 毎日 06:00 / 13:00（米国東部時間、夏時間・冬時間は自動対応）
- 実行基盤: GitHub Actions（人間の操作やPCの起動は不要。完全に無人で動作）
- 要約: Claude API（`claude-opus-5`）がWeb検索・記事本文の確認・日本語要約まで行う
- 閲覧: GitHub Pages に自動公開（任意でメール配信も可能）

## 仕組み

```
GitHub Actions (cron 06:00 / 13:00 ET)
  └─ scripts/collect_news.py   Claude API + web_search / web_fetch で収集・要約 → data/news.json に追記
  └─ scripts/build_site.py     30日より古い記事を削除し dist/index.html を生成
  └─ git commit & push         data/news.json と dist/index.html をリポジトリに保存（重複排除の基準）
  └─ GitHub Pages deploy       dist/ を公開
  └─ (任意) メール送信          .run/digest.html（その回の新規記事）を送付
```

| ファイル | 役割 |
|---|---|
| `scripts/collect_news.py` | 収集エージェント本体。カテゴリ定義・検索方針・要約ルール・出力スキーマはすべてここ |
| `scripts/build_site.py` | `data/news.json` → `dist/index.html`（標準ライブラリのみ） |
| `templates/site_template.html` | ダッシュボードのHTML/CSS/JS |
| `data/news.json` | 収集済み記事（URLで重複排除、公開日から30日で自動削除） |
| `.github/workflows/collect.yml` | スケジュール実行・公開・メールのワークフロー |
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

[docs/setup.md](docs/setup.md) を参照。必要なのは (1) GitHubリポジトリの作成とpush、(2) Anthropic APIキーをリポジトリのSecretに登録、(3) GitHub Pagesの有効化、の3点だけです。

## 手動実行・確認

- GitHub の Actions タブ →「Collect news」→「Run workflow」で即時実行できます（時刻ゲートは無視されます）。
- ローカルで試す場合:

```bash
ANTHROPIC_API_KEY=... python3 scripts/collect_news.py --category railcar_leasing && python3 scripts/build_site.py
```

（Python 3.10 以上と `pip install -r requirements.txt` が必要）

## 調整できる項目

- カテゴリ・検索対象・件数の上限: `scripts/collect_news.py` の `CATEGORIES`
- 要約ルール: 同ファイルの `SYSTEM_PROMPT`
- モデル・推論の深さ: リポジトリの Variables `NEWS_MODEL`（既定 `claude-opus-5`）、`NEWS_EFFORT`（`low`〜`max`、未設定なら既定）
- 収集時刻: `.github/workflows/collect.yml` の cron と `scripts/collect_news.py` の `RUN_HOURS_ET`

## 旧方式について

以前はClaude Codeアプリのスケジュールタスク（`railcar-news-collect`）がPC上で実行し、Claude Artifactに公開していました。GitHub Actions方式が動き始めたら、そのタスクは停止して構いません（[docs/setup.md](docs/setup.md) 参照）。
