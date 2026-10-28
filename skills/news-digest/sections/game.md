# ゲーム業界ニュース（`game`）

Slack の #game-news（チャンネル ID: `C0CBT2L7W8N`、ワークスペース Kamo-Dev）に、過去 24 時間の「ゲーム業界のニュース」を 1 件のまとめとして通知します。

- 対象: ゲーム業界の動き。企業の動き（決算・買収・スタジオ閉鎖・人員削減・人事・提携）、ハードウェアやプラットフォーム（Switch 2、PlayStation、Xbox、Steam など）の発表や方針、大型タイトルの発表・発売日決定・発売、業界イベント（Nintendo Direct、State of Play、TGS、gamescom など）、売上ランキング、ゲームと法規制・AIの話題、話題になった開発者インタビュー。
- 対象外: セール情報、グッズ・コラボカフェ・くじ、アニメ・漫画・VTuberの話題、PR記事、攻略記事、小規模なアップデート告知。

## 1. 既出のURLを控える

`slack_read_channel` で `C0CBT2L7W8N` の直近 5 件を読み、載せた URL を控えます（今回は再掲しない）。

## 2. ゲームニュースサイトから集める（WebSearch → WebFetch）

ゲームのニュースはこの手順が中心です。

- WebSearch を mode "extended" で 2 回行う。
  - 1 回目: クエリ「ゲーム 発表 <今日の日付(例: 10月24日 2026)>」、allowed_domains に ["www.4gamer.net", "www.famitsu.com", "game.watch.impress.co.jp", "automaton-media.com", "www.gamebusiness.jp", "www.inside-games.jp", "www.gamespark.jp"] を指定する。
  - 2 回目: クエリ「ゲーム業界 企業 ニュース <今日の日付>」（allowed_domains は 1 回目と同じ。失敗したら指定せずに再実行する）。
- 結果のうち、4Gamer・ファミ通・GAME Watch・AUTOMATON・GameBusiness.jp などのトップページや当日の記事一覧、個別記事を最大 4 ページ WebFetch で開き、見出し・記事URL・日時を取り出す。トップページには日時付きの新着一覧が載っていることが多い。
- 過去 24 時間の記事だけを候補にする。

## 3. 収集スクリプトで話題度を補う

`python3 skills/news-digest/scripts/collect.py game raw.json 24` を実行します。はてなブックマークの「アニメとゲーム」の人気エントリーと Hacker News のゲーム関連を集めます。はてブのこのカテゴリはアニメ・漫画の話題が多いので、対象に当てはまるゲームの話題だけを候補に加え、手順 2 と同じ出来事なら「話題になっている」印として使います。

## 4. ニュースを選ぶ

- 候補から対象に当てはまるものを最大 10 本選ぶ。企業の動きやハード・プラットフォームの話題を先に、次に大型タイトル・イベントの話題を並べる。複数のサイトが取り上げている話題を優先する。
- 同じ出来事の記事は 1 本にまとめる。
- 手順 1 で控えた URL は選ばない。

## 5. 投稿する

候補が 0 件なら投稿せずに終了します。それ以外は、`slack_send_message` で `C0CBT2L7W8N` に次の形式で 1 件だけ投稿します。

```
:video_game: **ゲーム業界 きょうのニュース**(M/D HH:MM〜M/D HH:MM、日本時間)

- [記事タイトル](URL)(4Gamer)
- [記事タイトル](URL)(ファミ通・はてブ 120users)
- [英語の記事タイトル](URL) — 日本語の短い訳(Hacker News 300pt)

候補 Web a件 + はてブ b件 / HN c件(raw.json の counts の値)から選定
```

- 出典はサイト名で書く。はてブや HN の数値があれば併記する。
- 手順 2 や 3 が失敗した場合も、取れた分で投稿し、最後に「:warning: 取得失敗: (手順と要約)」を 1 行添える。両方とも失敗して候補が 0 件なら「:warning: ゲーム業界ニュースの取得に失敗しました(M/D) — 要約1行」と投稿する。
