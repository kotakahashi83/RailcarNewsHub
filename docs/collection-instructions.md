# （旧）自動収集プロンプトの控え

このファイルは Claude Code アプリのスケジュールタスク `railcar-news-collect`（PC上で実行、Artifactに公開）用のプロンプトの控えでした。

現在の収集ロジックは GitHub Actions で動く [`scripts/collect_news.py`](../scripts/collect_news.py) に移行しています。カテゴリ定義（`CATEGORIES`）と要約ルール（`SYSTEM_PROMPT`）はそのファイルを直接編集してください。セットアップ手順は [setup.md](setup.md) を参照。

旧プロンプトの本文が必要な場合は git 履歴（コミット `5170125` 以前）を参照してください。
