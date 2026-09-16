# 初回セットアップ（一度だけ）

GitHub Actions で完全無人運転にするために、以下を一度だけ行います。所要時間は10分程度です。

## 1. GitHub リポジトリを作成して push

GitHub Pages を無料プランで使うにはリポジトリを **public** にする必要があります（private で公開したい場合は GitHub Pro 以上が必要）。収集データはニュースの見出し・URL・日本語要約のみで、機密情報は含みません。

```bash
gh repo create RailcarNewsHub --public --source=. --remote=origin --push
```

## 2. Anthropic API キーを Secret に登録

[Anthropic Console](https://console.anthropic.com/settings/keys) でAPIキーを発行し（課金設定が必要）、リポジトリの Secret `ANTHROPIC_API_KEY` に登録します。

```bash
gh secret set ANTHROPIC_API_KEY
```

（プロンプトでキーを貼り付け。キーはGitHubの暗号化ストアにのみ保存され、ログにも出ません）

## 3. GitHub Pages を有効化（ソース: GitHub Actions）

```bash
gh api -X POST repos/{owner}/RailcarNewsHub/pages -f build_type=workflow
```

`{owner}` は自分のGitHubユーザー名。Web UIなら Settings → Pages → Source を「GitHub Actions」にするのと同じです。

## 4. 初回実行

```bash
gh workflow run collect.yml
```

数分後、`https://<owner>.github.io/RailcarNewsHub/` でダッシュボードが見られます。以後は毎日 06:00 / 13:00（米国東部時間）に自動更新されます。

## 5. 旧スケジュールタスクの停止（任意）

Claude Code アプリ側のタスク `railcar-news-collect` は、Claude Codeのセッションで
`mcp__scheduled-tasks__update_scheduled_task`（`taskId: railcar-news-collect`, `enabled: false`）を実行するか、アプリの Scheduled tasks 画面で無効化してください。両方を動かすとローカルの git 履歴と GitHub 側の履歴が分岐します。

## 任意: メール配信

Secret を以下のように設定すると、更新のたびにその回の新規記事（見出し・リンク・要点3点）をメールで送ります。設定がなければ何も送りません。

| Secret | 内容 |
|---|---|
| `MAIL_TO` | 宛先アドレス |
| `MAIL_FROM` | 送信元アドレス |
| `SMTP_SERVER` | 例: `smtp.gmail.com` |
| `SMTP_PORT` | 省略時 465 |
| `SMTP_USERNAME` | SMTPユーザー名（Gmailならアドレス） |
| `SMTP_PASSWORD` | Gmailの場合は「アプリパスワード」 |

## 任意: モデルとコスト

- 既定モデルは `claude-opus-5`。1回の実行（5カテゴリ）で概ね数十万トークンを消費し、目安として1回あたり1〜3ドル程度、月に数十ドル規模になります。
- コストを抑えたい場合はリポジトリの Variable `NEWS_MODEL` を `claude-sonnet-5` に設定してください（`gh variable set NEWS_MODEL --body claude-sonnet-5`）。
- 実行ログは Actions タブの各ジョブで確認でき、各ターンのトークン数を出力しています。

## 注意

- GitHub の cron は数分〜十数分遅れることがあります。時刻ゲートは「東部時間の時（hour）」で判定するので、遅延しても同じ時間帯であれば実行されます。
- リポジトリに60日間コミットがないと GitHub はスケジュール実行を止めますが、このワークフロー自体が毎回コミットするため通常は該当しません。
