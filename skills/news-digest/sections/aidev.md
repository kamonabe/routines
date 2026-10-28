# AI×開発ニュース（`aidev`）

Slack の #ai-dev-news（チャンネル ID: `C0CBQFGSZLY`、ワークスペース Kamo-Dev）に、過去 24 時間の「AI×開発」の新着を 1 件のまとめとして通知します。対象は次の 2 つだけです。

- AIコーディングツールの更新（Claude Code、Kiro、Cursor、GitHub Copilot、Codex CLI、Gemini CLI など）
- 開発手法・実践例（仕様駆動開発、エージェント開発、AIレビュー、テスト、チーム導入、AIツールを使う上でのセキュリティ設計など、開発の進め方に関する記事）

モデルの性能比較だけの記事、一般的なAIニュース、AI以外の技術記事、宣伝・まとめ転載・ポッドキャスト告知は対象外です。

## 1. 収集スクリプトを実行する

`python3 skills/news-digest/scripts/collect_aidev.py raw.json 24` を実行します。

## 2. ツール更新をまとめる

- raw.json の tools（npm の新バージョン、Claude Code は notes に CHANGELOG、GitHub Copilot は changelog の記事）を使う。
- pages の Kiro / Cursor は changelog ページ先頭のテキストです。日付を読み、過去 24 時間（当日と前日の日付）のエントリだけを拾う。
- 各ツールは 1 行で、変わった内容のうち主なもの 1〜2 点を日本語で短く書く。変更内容が取れないものは「新バージョン公開」とだけ書く。
- 新着がなかったツールは、「Cursor・GitHub Copilot: 新着なし」のように 1 行にまとめる。

## 3. 記事を選ぶ

- articles から「開発手法・実践例」に当てはまるものを最大 8 本選ぶ。迷ったら、仕様駆動開発・Kiro・Claude Code の実践、チームでの導入や運用、レビューやテストの仕組み化、エージェントの安全な使い方を優先する。
- src が「はてブ」の記事は、はてなブックマークのテクノロジー人気エントリー（IT全般）です。AI×開発の対象に当てはまるものだけを選び、それ以外は無視する。
- hatebu（はてブのブックマーク数）が付いている記事は「話題になっている」印です。対象に当てはまるなら、はてブ経由の記事を 2 本程度は優先して入れる。
- 前回の #ai-dev-news の投稿（`slack_read_channel` で直近数件を読む）に載せた URL は選ばない。
- 英語の記事（HN）は、該当するものがあれば 1〜2 本入れる。なければ入れなくてよい。

## 4. 投稿する

ツール更新も記事も 0 件なら投稿せずに終了します。それ以外は、`slack_send_message` で `C0CBQFGSZLY` に次の形式で 1 件だけ投稿します。

```
:newspaper: **AI×開発 きょうの新着**(M/D HH:MM〜M/D HH:MM、日本時間)

:hammer_and_wrench: **ツール更新**
- **ツール名 バージョン** — 主な変更を1行([changelog](URL))
- ○○・○○: 新着なし

:memo: **開発手法・実践例**
- [記事タイトル](URL)(Zenn / Qiita / はてブ 120users / Hacker News 23pt)

候補 記事N件(Zenn a / Qiita b / はてブ c / HN d)・ツール更新M件から選定
```

- 出典は src に従う。はてブの記事は「はてブ Nusers」、Zenn・Qiita の記事に hatebu があれば「Zenn・はてブ Nusers」のように併記する。
- 最終行の件数は raw.json の counts の値をそのまま使う。自分で数え直さない。
- 0 件のセクションは省略する。
- 記事にはタイトルと出典だけを書き、要約や感想は書かない。
