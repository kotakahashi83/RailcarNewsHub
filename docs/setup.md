# 初回セットアップ（一度だけ）

追加課金なしで完全無人運転にするための手順です。所要時間は10分程度です。

## 1. GitHub リポジトリを作成して push

GitHub Pages を無料で使うにはリポジトリを **public** にします。収集データはニュースの見出し・URL・日本語要約のみで、機密情報は含みません。

```bash
gh repo create RailcarNewsHub --public --source=. --remote=origin --push
```

## 2. Claude の GitHub 連携でこのリポジトリを許可

https://claude.ai/code を開き、GitHub アカウントを接続して `RailcarNewsHub` へのアクセスを許可します（Claude GitHub App のインストール）。これで routine がリポジトリを clone・push できるようになります。

## 3. GitHub Pages を有効化（ソース: GitHub Actions）

```bash
gh api -X POST repos/kotakahashi83/RailcarNewsHub/pages -f build_type=workflow
```

Web UI なら Settings → Pages → Source を「GitHub Actions」にするのと同じです。有効化後、Actions タブの「Publish site」を一度 Run workflow すると初回公開されます。

## 4. routine の登録

Claude Code のセッションで「routine を登録して」と依頼すると `railcar-wire-collect` が作成されます。routine 本体には「`docs/routine-prompt.md` の『プロンプト本文』を読んでその通り実行せよ」という短い指示だけを登録してあるため、**収集ルールの変更はこのファイルを編集して push するだけ**で反映されます。

- cron: `0 13,14,20,21 * * *`（UTC。06:00 / 13:00 米国太平洋時間を夏時間・冬時間の両方でカバー）
- リポジトリ: `https://github.com/kotakahashi83/RailcarNewsHub`
- モデル: `claude-opus-5`
- ツール: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch

登録後、一度「Run now」で通し実行し、`https://kotakahashi83.github.io/RailcarNewsHub/` が更新されることを確認してください。

## 5. 旧スケジュールタスクの停止

Claude Code アプリ側のタスク `railcar-news-collect`（PC上で実行、Artifactに公開）は、routine が動き始めたら無効化してください。両方を動かすとローカルの git 履歴と GitHub 側の履歴が分岐します。

## 費用と利用枠

- GitHub: public リポジトリの Actions と Pages は無料（public リポジトリの Actions は分数制限なし）。候補収集は1回5〜15分、公開は1分程度。
- Claude: routine の実行はお使いのプランの利用枠を消費します（追加請求はなし）。1回の収集は数分〜10分程度のセッションで、1日2回＋時間外の即終了2回です。利用枠が気になる場合はモデルを `claude-sonnet-5` のまま運用してください。

## 注意

- routine は UTC の cron で1日4回起動し、米国太平洋時間の06時台・13時台でない2回はプロンプト冒頭のチェックで数秒で終了します。
- リポジトリに60日間コミットがないと GitHub はスケジュール系のワークフローを止めますが、この構成は push 起動なので影響しません。
