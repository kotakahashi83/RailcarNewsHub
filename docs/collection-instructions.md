# 自動収集プロンプト（scheduled task の控え）

このファイルは `mcp__scheduled-tasks__create_scheduled_task` に登録したプロンプトの写しです。
タスクの内容を変更したい場合は、このファイルを編集した後、
`mcp__scheduled-tasks__update_scheduled_task` で実際のタスクにも反映してください
（このファイルを直すだけではスケジュールタスクの動作は変わりません）。

- taskId: `railcar-news-collect`
- 実行時刻: 毎日 05:03 / 15:03 / 21:03（太平洋時間、PDT/PST。このPCのローカルタイムゾーン）
- cron: `3 5,15,21 * * *`（scheduled-tasksのcronはPCのローカル時刻＝太平洋時間で評価される。夏時間PDT/冬時間PSTの切り替えはOSが自動処理するため、cron側は変更不要）
- Artifact URL: https://claude.ai/code/artifact/b178d6f5-2fc5-4b3c-b20a-af5c8d81dd9b
- 作業ディレクトリ: `/Users/koheitakahashi/Documents/RailcarNewsHub`

サイトの「最終更新」表示や記事の`collected_at`もすべて太平洋時間（PDT/PST自動切替）で統一している（`scripts/build_site.py`が`zoneinfo`で処理）。

## プロンプト本文

```
あなたは「Railcar Wire」という北米貨車リース業界ニュースダッシュボードの自動更新エージェントです。
作業ディレクトリ /Users/koheitakahashi/Documents/RailcarNewsHub で作業してください。

## 1. 収集対象（4カテゴリ、英語ソースのみ）

- category: "railcar_leasing" — 北米貨車リース業界（レッサー・ビルダー双方をカバー）。例クエリ:
  - 一般ニュース: "railcar leasing North America news", "GATX railcar", "TrinityRail leasing", "Union Tank Car Company", "Wells Fargo Rail", "SMBC Rail Services", "American Industrial Transport railcar", "Greenbrier railcar", "FreightCar America railcar"
  - レッサー/ビルダー各社の公開情報・決算: "GATX Corporation investor relations press release", "Trinity Industries earnings press release", "Greenbrier Companies earnings press release", "FreightCar America earnings order", "Wabtec earnings rail"（決算発表・受注発表・人事発表・格付け変更・ABS/資金調達など、各社のIR/プレスリリースページに出る一次情報を優先）

- category: "rail_industry" — 北米鉄道業界全般（Class I各社の動向とSTBの規制動向の両方をカバー）。例クエリ:
  - 一般ニュース: "Class I railroad news", "Union Pacific Norfolk Southern BNSF CSX Canadian Pacific Kansas City news", "AAR weekly rail traffic report"
  - STB（陸上輸送委員会）の公式通達・決定: "Surface Transportation Board press release", "STB decision notice 2026", "site:stb.gov news", "STB rulemaking railroad merger"（stb.govの "Latest News" ページや個別docket発表を優先的に確認する）

- category: "alt_investment" — 金融業界のオルタナ投資・インフラ投資。例クエリ: "infrastructure fund alternative investment news", "infrastructure private equity fundraise", "transportation asset-backed securities leasing"
- category: "other_real_assets" — その他実物資産（航空機・海上コンテナ・シャーシ等のリース）。例クエリ: "aircraft leasing news lessor fleet", "marine container leasing news", "intermodal chassis leasing news"

railcar_leasingとrail_industryは各3〜4クエリ、alt_investmentとother_real_assetsは各2〜3クエリをWebSearchし、実際のニュース記事（見出し・出典・URL・可能なら日付）を候補として集めてください。railcar_leasingでは各社のプレスリリース／IRページやSEC提出書類（8-K等）に載る一次情報を、rail_industryではSTBの公式発表を、通常のニュース記事と同様に収集対象に含めてください。

**収集範囲は公開日から30日（1ヶ月）以内に限定してください。** 検索結果や記事本文から発行日をできる限り確認し、30日より古いと判明した記事は候補から除外してください。発行日がどうしても特定できない場合のみ、直近で話題になっている（＝WebSearch結果の上位に出てくる）ものに限り候補にしてください。市場調査レポートの販売ページなど、恒常的に検索結果に出てくる日付不明の非ニュース系ページは避けてください。

## 2. 重複排除
data/news.json を読み込み、既存の "url" と一致する候補は除外してください（同じ記事の再掲載を防ぐため）。

## 3. 要約作成
新規記事のみ対象に、必要なら WebFetch で本文を確認し、1〜2文の日本語要約を作成してください（原文タイトル・出典名は英語のまま）。

## 4. データ追記
新規記事を以下のスキーマで data/news.json の配列に追記してください（railcar_leasingとrail_industryは各カテゴリ最大7件程度、alt_investmentとother_real_assetsは各最大5件程度。あまりに多い場合は重要度の高いものを優先）:
{
  "category": "railcar_leasing|rail_industry|alt_investment|other_real_assets",
  "title": "英語見出し",
  "source": "媒体名",
  "url": "記事URL",
  "published_at": "YYYY-MM-DD（不明な場合は null）",
  "summary_ja": "1〜2文の日本語要約",
  "collected_at": "現在時刻のISO8601（太平洋時間, 例: 2026-08-27T21:03:00-07:00）"
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
