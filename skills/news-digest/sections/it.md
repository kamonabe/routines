# IT業界ニュース（`it`）

Slack の #it-news（チャンネル ID: `C0CBDKQBZ0F`、ワークスペース Kamo-Dev）に、過去 24 時間の「IT業界全体のニュース」を 1 件のまとめとして通知します。

- 対象: IT業界の動き。企業の動き（決算・買収・人員削減・提携）、製品・サービスの発表、クラウド・OS・ブラウザ・半導体・通信、規制や訴訟、大規模障害、情報漏えいやサイバー攻撃などのセキュリティ事件、話題になった技術記事。
- 対象外: AIそのものの話題（モデル発表、AI企業の動きなど。#ai-news が担当）、AIコーディングツールや開発手法（#ai-dev-news が担当）、宣伝・PR・セール情報。

## 1. 既出のURLを控える

`slack_read_channel` で `C0CBDKQBZ0F` の直近 5 件を読み、載せた URL を控えます（今回は再掲しない）。

## 2. 収集スクリプトを実行する

`python3 skills/news-digest/scripts/collect.py it raw.json 24` を実行します。はてなブックマークの人気エントリーと Hacker News の上位を集めます。

## 3. ニュースサイトから補う（WebSearch → WebFetch）

- WebSearch を mode "extended" で 2 回行う。クエリには今日の日付を入れる（例: 「IT ニュース 2026年10月24日」「テクノロジー 企業 発表 10月24日」）。
- 結果のうち、ITmedia NEWS、Impress Watch、Publickey、日経クロステック、ZDNET Japan、GIGAZINE、The Verge、Ars Technica などの、当日の記事一覧やトップページ、個別記事を最大 3 ページ WebFetch で開き、見出し・記事URL・日時を取り出す。
- 過去 24 時間の記事だけを候補にする。

## 4. 記事を選ぶ

- 手順 2・3 の候補から、対象に当てはまるものを最大 10 本選ぶ。はてブのブックマーク数（users）や HN のポイント（points）が多いもの、複数の出典で取り上げられているものを優先する。
- 同じ出来事の記事は 1 本にまとめる（日本語の記事を優先）。
- 手順 1 で控えた URL は選ばない。

## 5. 投稿する

候補が 0 件なら投稿せずに終了します。それ以外は、`slack_send_message` で `C0CBDKQBZ0F` に次の形式で 1 件だけ投稿します。

```
:computer: **IT業界 きょうのニュース**(M/D HH:MM〜M/D HH:MM、日本時間)

- [記事タイトル](URL)(はてブ 120users)
- [英語の記事タイトル](URL) — 日本語の短い訳(Hacker News 300pt)
- [記事タイトル](URL)(ITmedia NEWS)

候補 はてブ a件 / HN b件(raw.json の counts の値)+ Web c件から選定
```

- 出典はサイト名で書く。はてブや HN の数値があれば併記する（例: 「Publickey・はてブ 85users」）。
- 手順 2 や 3 が失敗した場合も、取れた分で投稿し、最後に「:warning: 取得失敗: (手順と要約)」を 1 行添える。両方とも失敗して候補が 0 件なら「:warning: IT業界ニュースの取得に失敗しました(M/D) — 要約1行」と投稿する。
