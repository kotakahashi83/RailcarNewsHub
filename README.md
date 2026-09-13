# Railcar Wire

北米貨車リース業界を中心に、鉄道業界全般・金融のオルタナ投資/インフラ投資・その他実物資産（航空機・海上コンテナ・シャーシ等のリース）のニュースを英語ソースから収集し、日本語要約付きで一覧できるダッシュボードです。

**サイトURL**: https://claude.ai/code/artifact/b178d6f5-2fc5-4b3c-b20a-af5c8d81dd9b
（Claude Codeが入っていないPCからでもリンクだけで閲覧できます）

## 仕組み
- `data/news.json` — 収集済み記事の正データ（URLで重複排除。`published_at`が分かる記事はそこから30日、不明な記事は`collected_at`から30日経過すると自動削除。表示は新しい順）
- `templates/site_template.html` — ダッシュボードのHTML/CSS/JSテンプレート
- `scripts/build_site.py` — `data/news.json` を `templates/site_template.html` に埋め込み `dist/index.html` を生成（Python3標準ライブラリのみ、依存なし）
- `dist/index.html` — 生成物。この内容をArtifactとしてpublishしている
- `docs/collection-instructions.md` — 自動収集タスク（scheduled task）のプロンプトの控えと運用メモ

## 自動更新
Claudeのスケジュールタスク `railcar-news-collect` が1日3回、**太平洋時間の05:00 / 15:00 / 21:00**（このPCのローカルタイムゾーン）に自動実行され、WebSearch/WebFetchでニュースを収集し、要約を付けて `dist/index.html` を再生成し、同じArtifact URLに再publishします。サイトの「最終更新」表示も太平洋時間（PDT/PSTは自動切替）です。詳細は [docs/collection-instructions.md](docs/collection-instructions.md) を参照してください。

スケジュールタスクはClaude Codeアプリが起動している間に発火します。アプリを閉じていた場合、次回起動時にまとめて実行されます（完全に独立したサーバー常駐ではありません）。

## 手動更新
```bash
python3 scripts/build_site.py
```
を実行後、Claude Codeのセッションで `dist/index.html` をArtifactとして
`url: https://claude.ai/code/artifact/b178d6f5-2fc5-4b3c-b20a-af5c8d81dd9b` を指定して再publishすると即座に更新できます。

## スケジュールの確認・変更
- 一覧: `mcp__scheduled-tasks__list_scheduled_tasks`
- 変更: `mcp__scheduled-tasks__update_scheduled_task`（taskId: `railcar-news-collect`）
- プロンプトの現物: `~/.claude/scheduled-tasks/railcar-news-collect/SKILL.md`
