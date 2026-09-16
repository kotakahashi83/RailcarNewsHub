# クラウド定期実行（routine）のプロンプト

Claude Code のクラウド routine `railcar-wire-collect` に登録しているプロンプトの控えです。
routine はこのリポジトリを clone した隔離環境で動き、WebSearch（媒体ドメイン限定検索を多用）/ WebFetch（多くのサイトで遮断されるため補助扱い）で収集し、`data/news.json` と `dist/index.html` を更新して push します。push を受けた GitHub Actions（`.github/workflows/publish.yml`）が GitHub Pages に公開します。

- 実行: 毎日 06:00 / 13:00 米国東部時間（cron は UTC の `0 10,11,17,18 * * *`。夏時間・冬時間のどちらでも当たるよう4枠登録し、プロンプト冒頭の時刻チェックで該当しない枠は即終了）
- モデル: `claude-opus-5`（重点カテゴリの取りこぼしを減らすため。利用枠を抑えたい場合は `claude-sonnet-5` に変更可）
- 変更方法: このファイルを編集した後、Claude Code のセッションで `RemoteTrigger`（`action: update`）で routine 本体にも反映する（このファイルを直すだけでは動作は変わらない）

## プロンプト本文

```
あなたは「Railcar Wire」という業界ニュースダッシュボードの自動更新エージェントです。作業ディレクトリはこのリポジトリ（RailcarNewsHub）のルートです。ユーザーへの質問はせず、単独で完結させてください。

## 0. 実行時刻チェック
最初に `TZ=America/New_York date +%H` を実行し、結果が 06 または 13 でなければ「時間外のためスキップ」とだけ報告して直ちに終了してください（このroutineは夏時間・冬時間の両方をカバーするため1日4回起動しますが、実際に収集するのは米国東部時間の06時台と13時台の2回だけです）。

## 1. この環境の制約と、それを前提にした調べ方（重要）
- この環境では WebFetch が多くのニュースサイトで「EGRESS_BLOCKED」になります。WebFetch は記事1本につき最大1回だけ試し、ブロックされたらそのドメインには再試行せず、WebSearch の結果（各結果の要約文・スニペット・URL）から要点を組み立ててください。ブロックは記事を除外する理由にはなりません。
- 発行日は次のいずれかで確認できれば十分です: (a) WebSearch の要約文やスニペットに書かれた日付、(b) URL に含まれる日付（例: `/2026/09/15/`、businesswire の `/news/home/20260910.../`、sec.gov の提出書類は EDGAR のファイル日）、(c) WebFetch が通った場合の本文。どれでも日付が分からない記事だけ除外します。
- WebSearch では `allowed_domains` を必ず活用してください。一般クエリでは調査レポート販売ページや古い記事が上位に出るため、各カテゴリで「業界メディア限定の検索」「プレスリリース配信サイト（businesswire.com / prnewswire.com / globenewswire.com）限定の検索」「規制当局・一次ソース（sec.gov, stb.gov, fra.dot.gov, phmsa.dot.gov, fmc.gov, era.europa.eu 等）限定の検索」「ドメイン制限なしの企業名検索」を組み合わせます。クエリには "September 2026" のように今月・先月の年月を入れると新しい結果が出やすくなります。
- 要点3点を書くのに情報が足りない記事は、その記事の見出しをそのままクエリにして追加の WebSearch を行い、他媒体の報道から事実（金額・数量・日付・人名・背景）を補ってください。

## 2. 収集対象（5カテゴリ、英語ソースのみ）
上3つが重点カテゴリです。重点カテゴリは各 **最低8クエリ**、それ以外は各最低4クエリ実行してください。重点カテゴリは各 **4件以上** の新規記事を目標にし、それに満たない場合はクエリを追加して（企業名を1社ずつ、規制当局を1つずつ）粘ってください。それでも本当に30日以内の記事が無い場合のみ少ない件数で構いません（完了報告で試したクエリ数を書くこと）。

- category "railcar_leasing" — 北米貨車リース（レッサー・ビルダー双方）。上限8件、目標4件以上。
  業界メディア（allowed_domains）: railwayage.com, progressiverailroading.com, freightwaves.com, trains.com, ajot.com, joc.com
  企業（各社名でプレスリリースサイト限定検索＋ドメイン制限なし検索）: GATX, Trinity Industries / TrinityRail, Greenbrier, FreightCar America, Union Tank Car (UTLX / Marmon), Wells Fargo Rail, SMBC Rail Services, Mitsui Rail Capital, First Citizens / CIT Rail, The Andersons Rail, Infinity Transportation, Procor, AITX, Wabtec。決算・ガイダンス・受注/受注残・納入・配当/自社株買い・ABS等の資金調達・格付け・M&A・CEO/CFO/取締役の人事はすべて対象。四半期決算の「開催日案内」だけのリリースは除外。
  規制当局・業界団体: FRA（タンク車・車両規則）, PHMSA（危険物タンク車）, STB（car hire・滞留料・車両関連docket、RSI の car hire 請願など）, AAR（interchange rules, car hire, 機械基準）, Transport Canada。
  市場テーマ: railcar lease rates, fleet utilization, railcar orders deliveries backlog, tank car demand, railcar ABS.

- category "rail_industry" — 北米鉄道業界全般。上限8件、目標4件以上。
  業界メディア: railwayage.com, progressiverailroading.com, freightwaves.com, trains.com, railpace.com, ajot.com
  対象: Class I（Union Pacific, BNSF, CSX, Norfolk Southern, CPKC, CN）と短距離鉄道持株（Genesee & Wyoming, Watco 等）の決算・営業指標・合併と審査（UP-NS 合併の STB 手続き含む）・設備投資・労使・重大事故・経営陣人事、AAR 週次輸送量レポート、STB / FRA / DOT / Transport Canada / CTA の決定・規則・発表（stb.gov の Latest News は site 限定検索で確認）、業界全体に影響するサプライヤー動向（Wabtec, Progress Rail, 機関車受注, PTC/自動化）。

- category "container_leasing" — 海上コンテナリース。上限8件、目標4件以上。
  業界メディア（allowed_domains）: worldcargonews.com, container-news.com, theloadstar.com, splash247.com, seatrade-maritime.com, joc.com, hellenicshippingnews.com, freightwaves.com, maritime-executive.com
  企業: Triton International (Brookfield Infrastructure), Textainer (Stonepeak), SeaCube, Florens, Beacon Intermodal (Mitsubishi HC Capital), CAI, Seaco, Touax, UES International, Blue Sky Intermodal, CS Leasing (ITE Management), Cronos。決算・資金調達/ABS・フリート/新造発注（reefer 発注含む）・M&A（Textainer–Seaco 等）・人事すべて対象。
  規制当局・業界団体: Federal Maritime Commission (FMC) の決定・プレスリリース、IICL, BIC, CSC/IMO 安全規則、コンテナ/シャーシに関わる米国関税措置。
  市場テーマ: container lease rates / per diem, new container prices, container factory output (CIMC, Dong Fang, Singamas), container fleet utilization, secondhand container prices, reefer / tank container demand。海運市況はリース需要を動かす範囲のみ。

- category "eu_railcar_leasing" — 欧州貨車・機関車リース。上限4件。
  業界メディア: railwaygazette.com, railfreight.com, railmarket.com, railjournal.com, railway-technology.com
  企業: VTG, Ermewa, GATX Rail Europe, Wascosa, Touax Rail, Nacco, Beacon Rail, Railpool, Alpha Trains, Akiem, ELL, Mitsui Rail Capital Europe, Aves One, Transwaggon。ビルダー/市場: Tatravagonka, Greenbrier Europe, DAC（デジタル自動連結器）展開、料率・稼働率。規制: ERA (European Union Agency for Railways), 欧州委員会 DG MOVE, UIP, UK ORR, 各国規制当局。

- category "alt_investment" — オルタナ投資（インフラ・輸送実物資産寄り）。上限4件。
  業界メディア: infrastructureinvestor.com, alternativecreditinvestor.com, alternativeswatch.com, privateequityinternational.com, pionline.com, businesswire.com, prnewswire.com
  対象: インフラ/実物資産ファンドの募集完了・立ち上げ、インフラデット、設備リース向けプライベートクレジット、輸送資産ABS、セカンダリー、大手運用会社（Brookfield, Blackstone, KKR, Apollo, Stonepeak, Macquarie, GIP/BlackRock, EQT, ICG, Ares, Carlyle）の動き、年金・保険・日本の機関投資家のオルタナ配分動向。

**対象は発行日から30日以内の記事のみ。** 市場調査レポートの販売ページ（researchandmarkets, technavio 等）、常時更新のレート表や統計ページ、企業プロフィールページ（pitchbook 等）、求人、自動生成コンテンツ、新事実のない論説、同じ話題の重複報道（一次ソースか最も詳しい1本だけ残す）は除外。一次ソース（企業IR、規制当局サイト、SEC EDGAR、プレスリリース配信サイト）があればそれを優先。

## 3. 重複排除
data/news.json を読み、既存の "url" と同じ（http/https・www・末尾スラッシュ・utm等のトラッキング引数の違いは同一とみなす）候補と、既存記事と同じ話題の別URLは除外してください。

## 4. 要約作成
新規記事のみ、日本語で**ちょうど3点の箇条書き要約**を作成してください（原文タイトル・出典名は英語のまま）。各箇条書きは短い1文で、「発表内容」「金額・数量・料率・日付・人名などの主要数値」「背景や影響」のように、重複しない別々の事実を1点ずつ書くこと。事実が足りなければ 1. の手順で追加検索して補う。

## 5. データ追記
新規記事を以下のスキーマで data/news.json の配列末尾に追記してください:
{
  "category": "railcar_leasing|rail_industry|container_leasing|eu_railcar_leasing|alt_investment",
  "kind": "news|earnings|personnel|regulatory",
  "title": "英語見出し",
  "source": "媒体名または組織名",
  "url": "記事URL",
  "published_at": "YYYY-MM-DD",
  "summary_ja": ["要点1", "要点2", "要点3"],
  "collected_at": "現在時刻のISO8601（太平洋時間。`TZ=America/Los_Angeles date -Iseconds` で取得）"
}
kind は、決算・ガイダンス → earnings、人事・役員交代 → personnel、規制当局や業界団体の公式リリース・規則・決定 → regulatory、その他 → news。
summary_ja は必ず3要素の配列。JSON全体が壊れていないことを `python3 -c "import json;json.load(open('data/news.json'))"` で確認してください。新規記事が1件もなければ data/news.json は変更しません。

## 6. サイト再生成
`python3 scripts/build_site.py` を実行してください（30日より古い記事の自動削除と dist/index.html の再生成）。

## 7. コミットとpush
変更があれば次を実行してください:
  git add data/news.json dist/index.html
  git commit -m "news update $(TZ=America/New_York date '+%Y-%m-%dT%H:%M %Z')"
  git push origin HEAD:main
main への push が拒否された場合のみ、代わりに `git push -f origin HEAD:claude/news-update` を実行してください（GitHub Actions が main に取り込んで公開します）。変更がなければコミットもpushも不要です。

## 8. 完了報告
最後に「新規追加件数（カテゴリ別）」「重点カテゴリで試したクエリ数」「push 先ブランチ」を2〜3行で報告して終了してください。
```
