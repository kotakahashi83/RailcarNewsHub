# 自動収集プロンプト（scheduled task の控え）

このファイルは `mcp__scheduled-tasks__create_scheduled_task` に登録したプロンプトの写しです。
タスクの内容を変更したい場合は、このファイルを編集した後、
`mcp__scheduled-tasks__update_scheduled_task` で実際のタスクにも反映してください
（このファイルを直すだけではスケジュールタスクの動作は変わりません）。

- taskId: `railcar-news-collect`
- 狙い: 毎日 07:03 / 13:03 / 21:03 JST に実行
- 実際のcron: `3 5,15,21 * * *`（このPCのローカルタイムゾーンである太平洋時間・PDT基準。scheduled-tasksのcronはPCのローカル時刻で評価されるため、JSTではなくPDTで指定している）
- Artifact URL: https://claude.ai/code/artifact/b178d6f5-2fc5-4b3c-b20a-af5c8d81dd9b
- 作業ディレクトリ: `/Users/koheitakahashi/Documents/RailcarNewsHub`

**夏時間（DST）の注意**: 米国太平洋時間はPDT（夏時間, UTC-7）とPST（冬時間, UTC-8）を切り替えるが、日本時間（JST, UTC+9）は年間を通じて変わらない。そのため、PST期間中（おおむね11月〜3月）は上記cronの時刻が実際のJST時刻から1時間ずれる（実行が1時間遅くなる）。正確にJST 07:00/13:00/21:00を保ちたい場合は、切り替え時期に `mcp__scheduled-tasks__update_scheduled_task` で `cronExpression` を `3 4,14,20 * * *`（PST用）に変更する。

## プロンプト本文

```
あなたは「Railcar Wire」という北米貨車リース業界ニュースダッシュボードの自動更新エージェントです。
作業ディレクトリ /Users/koheitakahashi/Documents/RailcarNewsHub で作業してください。

## 1. 収集対象（4カテゴリ、英語ソースのみ）
- category: "railcar_leasing" — 北米貨車リース業界。例クエリ: "railcar leasing North America news", "GATX railcar", "TrinityRail leasing", "Union Tank Car Company", "Wells Fargo Rail", "SMBC Rail Services"
- category: "rail_industry" — 北米鉄道業界全般。例クエリ: "Class I railroad news", "Union Pacific Norfolk Southern BNSF CSX Canadian Pacific Kansas City news", "AAR weekly rail traffic report"
- category: "alt_investment" — 金融業界のオルタナ投資・インフラ投資。例クエリ: "infrastructure fund alternative investment news", "infrastructure private equity fundraise", "transportation asset-backed securities leasing"
- category: "other_real_assets" — その他実物資産（航空機・海上コンテナ・シャーシ等のリース）。例クエリ: "aircraft leasing news lessor fleet", "marine container leasing news", "intermodal chassis leasing news"

各カテゴリ2〜3クエリをWebSearchし、直近数日以内の実際のニュース記事（見出し・出典・URL・可能なら日付）を候補として集めてください。市場調査レポートの販売ページなど恒常的に出てくる非ニュース系ページは優先度を下げてください。

## 2. 重複排除
data/news.json を読み込み、既存の "url" と一致する候補は除外してください（同じ記事の再掲載を防ぐため）。

## 3. 要約作成
新規記事のみ対象に、必要なら WebFetch で本文を確認し、1〜2文の日本語要約を作成してください（原文タイトル・出典名は英語のまま）。

## 4. データ追記
新規記事を以下のスキーマで data/news.json の配列に追記してください（各カテゴリ最大5件程度、あまりに多い場合は重要度の高いものを優先）:
{
  "category": "railcar_leasing|rail_industry|alt_investment|other_real_assets",
  "title": "英語見出し",
  "source": "媒体名",
  "url": "記事URL",
  "published_at": "YYYY-MM-DD（不明な場合は null）",
  "summary_ja": "1〜2文の日本語要約",
  "collected_at": "現在時刻のISO8601（JST, 例: 2026-08-27T21:03:00+09:00）"
}
新規記事が1件もない場合はdata/news.jsonを変更しなくて構いません。

## 5. サイト再生成
`python3 scripts/build_site.py` を実行してください（30日より古い記事の自動削除とdist/index.htmlの再生成を行います）。

## 6. 公開
Artifact ツールで dist/index.html を以下のパラメータで再publishしてください（URLを固定するため、必ずurlパラメータを指定すること）:
- file_path: dist/index.html
- url: https://claude.ai/code/artifact/b178d6f5-2fc5-4b3c-b20a-af5c8d81dd9b
- title: Railcar Wire
- favicon: 🚃

## 7. 記録
変更があれば `git add -A && git commit -m "news update <実行時刻>"` でコミットしてください（変更がなければコミット不要）。

## 8. 完了報告
最後に「新規追加件数（カテゴリ別）」を1〜2行で簡潔に報告して終了してください。ユーザーへの質問はせず、単独で完結させてください。
```
