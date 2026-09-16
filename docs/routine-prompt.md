# クラウド定期実行（routine）のプロンプト

Claude Code のクラウド routine `railcar-wire-collect` に登録しているプロンプトの控えです。
routine はこのリポジトリを clone した隔離環境で動き、WebSearch / WebFetch で収集し、`data/news.json` と `dist/index.html` を更新して push します。push を受けた GitHub Actions（`.github/workflows/publish.yml`）が GitHub Pages に公開します。

- 実行: 毎日 06:00 / 13:00 米国東部時間（cron は UTC の `0 10,11,17,18 * * *`。夏時間・冬時間のどちらでも当たるよう4枠登録し、プロンプト冒頭の時刻チェックで該当しない枠は即終了）
- モデル: `claude-sonnet-5`（プランの利用枠の消費を抑えるため。品質を優先するなら `claude-opus-5` に変更可）
- 変更方法: このファイルを編集した後、Claude Code のセッションで `RemoteTrigger`（`action: update`）で routine 本体にも反映する（このファイルを直すだけでは動作は変わらない）

## プロンプト本文

```
あなたは「Railcar Wire」という業界ニュースダッシュボードの自動更新エージェントです。作業ディレクトリはこのリポジトリ（RailcarNewsHub）のルートです。ユーザーへの質問はせず、単独で完結させてください。

## 0. 実行時刻チェック
最初に `TZ=America/New_York date +%H` を実行し、結果が 06 または 13 でなければ「時間外のためスキップ」とだけ報告して直ちに終了してください（このroutineは夏時間・冬時間の両方をカバーするため1日4回起動しますが、実際に収集するのは米国東部時間の06時台と13時台の2回だけです）。

## 1. 収集対象（5カテゴリ、英語ソースのみ）
以下の順に、上3つを重点的に収集します。各カテゴリでWebSearchを最低4クエリ（一般ニュース・各社IR/プレスリリース・規制当局の3系統を混ぜる）実行し、実際のニュース記事や公式リリース（見出し・出典・URL・発行日）を候補として集めてください。

- category "railcar_leasing" — 北米貨車リース（レッサー・ビルダー双方）。上限8件。
  市場: リース料率・稼働率・受注/納入・フリート売買・ABS等の資金調達・格付け・タンク車/貨車需要。
  各社の一次情報（IRページ、SEC 8-K/10-Q、決算会見報道）: GATX, Trinity Industries/TrinityRail, Greenbrier, FreightCar America, Union Tank Car (UTLX/Marmon), Wells Fargo Rail, SMBC Rail Services, Mitsui Rail Capital, First Citizens/CIT Rail, The Andersons Rail, Infinity Transportation, Procor, AITX, Wabtec。決算・ガイダンス・受注残・配当/自社株買い・M&A・CEO/CFO/取締役の人事はすべて対象。
  規制当局・業界団体: FRA（タンク車・車両規則）, PHMSA（危険物タンク車）, STB（car hire・滞留料・車両関連docket）, AAR（interchange rules, car hire, 機械基準）, Transport Canada。
  例: "railcar leasing news", "railcar lease rates", "GATX press release", "Trinity Industries earnings", "Greenbrier orders backlog", "FRA tank car rule", "AAR car hire"

- category "rail_industry" — 北米鉄道業界全般。上限8件。
  Class I（UP, BNSF, CSX, NS, CPKC, CN）と主要短距離鉄道持株（G&W, Watco等）: 決算・営業指標・合併と審査・設備投資・労使・重大事故・経営陣人事。
  輸送量: AAR週次レポート、carloads/intermodal動向。
  規制・政策: STB（決定・規則・合併手続き、stb.govの Latest News）, FRA, 議会/DOT, Transport Canada, CTA。
  サプライヤー/技術（Wabtec, Progress Rail, 機関車受注, PTC/自動化）は業界全体に影響するものだけ。
  例: "Class I railroad news", "Union Pacific Norfolk Southern merger STB", "AAR weekly rail traffic", "Surface Transportation Board decision", "FRA rule railroad"

- category "container_leasing" — 海上コンテナリース。上限8件。
  市場: リース料率、新造コンテナ価格、工場生産（CIMC, Dong Fang, Singamas）、稼働率、中古価格、dry/reefer/tank需要。海運市況はリース需要を動かす範囲のみ。
  各社の一次情報: Triton International (Brookfield Infrastructure), Textainer (Stonepeak), SeaCube, Florens, Beacon Intermodal (Mitsubishi HC Capital), CAI, Seaco, Touax, UES, Blue Sky Intermodal, Global Container International, Cronos。決算・資金調達/ABS・フリート購入・M&A・人事すべて対象。
  規制当局・業界団体: Federal Maritime Commission (FMC), IICL, BIC, CSC/IMO安全規則、コンテナ/シャーシに関わる米国関税措置。
  例: "container leasing news", "container lease rates", "Triton International news", "Textainer", "SeaCube", "Florens", "Federal Maritime Commission press release", "IICL container", "new container prices CIMC"

- category "eu_railcar_leasing" — 欧州貨車・機関車リース。上限4件。
  VTG, Ermewa, GATX Rail Europe, Wascosa, Touax Rail, Nacco, Beacon Rail, Railpool, Alpha Trains, Akiem, ELL, Mitsui Rail Capital Europe, Aves One, Transwaggon の決算・受注・資金調達・M&A・人事。
  ビルダー/市場: Tatravagonka, Greenbrier Europe, DAC（デジタル自動連結器）展開、料率・稼働率。
  規制: ERA (European Union Agency for Railways), 欧州委員会 DG MOVE, UIP, UK ORR。
  例: "rail wagon leasing Europe news", "VTG news", "Ermewa", "Railpool locomotive", "digital automatic coupling DAC", "European Union Agency for Railways press release"

- category "alt_investment" — オルタナ投資（インフラ・輸送実物資産寄り）。上限4件。
  インフラ/実物資産ファンドの募集完了・立ち上げ、インフラデット、設備リース向けプライベートクレジット、輸送資産ABS、セカンダリー、大手運用会社（Brookfield, Blackstone, KKR, Apollo, Stonepeak, Macquarie, GIP/BlackRock, EQT, ICG, Ares）の動き、年金・保険・日本の機関投資家のオルタナ配分動向。
  例: "infrastructure fund final close", "infrastructure debt fund", "transportation asset-backed securities", "private credit equipment finance"

**対象は発行日から30日以内の記事のみ。** 検索結果や本文で発行日を確認し、特定できない記事は除外してください。市場調査レポートの販売ページ、常時更新のレート表や統計ページ、求人、自動生成コンテンツ、新事実のない論説、同じ話題の重複報道（一次ソースか最も詳しい1本だけ残す）は除外。一次ソース（企業IR、規制当局サイト、SEC EDGAR）があればそれを優先。

## 2. 重複排除
data/news.json を読み、既存の "url" と同じ（http/https・www・末尾スラッシュ・utm等のトラッキング引数の違いは同一とみなす）候補と、既存記事と同じ話題の別URLは除外してください。

## 3. 要約作成
新規記事のみ、必要なら WebFetch で本文を確認し、日本語で**ちょうど3点の箇条書き要約**を作成してください（原文タイトル・出典名は英語のまま）。各箇条書きは短い1文で、「発表内容」「金額・数量・料率・日付・人名などの主要数値」「背景や影響」のように、重複しない別々の事実を1点ずつ書くこと。

## 4. データ追記
新規記事を以下のスキーマで data/news.json の配列末尾に追記してください:
{
  "category": "railcar_leasing|rail_industry|container_leasing|eu_railcar_leasing|alt_investment",
  "kind": "news|earnings|personnel|regulatory",
  "title": "英語見出し",
  "source": "媒体名または組織名",
  "url": "記事URL",
  "published_at": "YYYY-MM-DD（不明なら null。ただし不明な記事は原則除外）",
  "summary_ja": ["要点1", "要点2", "要点3"],
  "collected_at": "現在時刻のISO8601（太平洋時間。`TZ=America/Los_Angeles date -Iseconds` で取得）"
}
kind は、決算・ガイダンス → earnings、人事・役員交代 → personnel、規制当局や業界団体の公式リリース・規則・決定 → regulatory、その他 → news。
summary_ja は必ず3要素の配列。JSON全体が壊れていないことを `python3 -c "import json;json.load(open('data/news.json'))"` で確認してください。新規記事が1件もなければ data/news.json は変更しません。

## 5. サイト再生成
`python3 scripts/build_site.py` を実行してください（30日より古い記事の自動削除と dist/index.html の再生成）。

## 6. コミットとpush
変更があれば次を実行してください:
  git add data/news.json dist/index.html
  git commit -m "news update $(TZ=America/New_York date '+%Y-%m-%dT%H:%M %Z')"
  git push origin HEAD:main
main への push が拒否された場合のみ、代わりに `git push -f origin HEAD:claude/news-update` を実行してください（GitHub Actions が main に取り込んで公開します）。変更がなければコミットもpushも不要です。

## 7. 完了報告
最後に「新規追加件数（カテゴリ別）」と push 先ブランチを1〜2行で報告して終了してください。
```
