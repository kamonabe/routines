# AIニュース（`ai`）

Slack の #ai-news（チャンネル ID: `C0CBWTUR1H7`、ワークスペース Kamo-Dev）に、過去 24 時間の「AIに関するニュース」を 1 件のまとめとして通知します。

- 対象: AI全般のニュース。モデルの発表・公開、AI企業（OpenAI、Anthropic、Google、Meta、xAI、Microsoft、NVIDIA、中国勢など）の動き、提携・資金調達・買収、規制・法律・訴訟、AIによる事件や社会への影響、企業でのAI導入、注目の研究。
- 対象外: AIコーディングツール（Claude Code、Kiro、Cursor、Copilot など）の更新や、開発手法・実践例の記事（#ai-dev-news が担当）、宣伝・PR・セミナー告知、一般論のコラム。

## 1. 既出のURLを控える

`slack_read_channel` で `C0CBWTUR1H7` の直近 5 件を読み、載せた URL を控えます（今回は再掲しない）。#ai-dev-news（`C0CBQFGSZLY`）の直近 3 件も読み、そこに載った URL も選ばないようにします。

## 2. 収集スクリプトを実行する

`python3 skills/news-digest/scripts/collect.py ai raw.json 24` を実行します。はてなブックマークの人気エントリーと Hacker News から AI 関連を集めます。

## 3. ニュースサイトから補う（WebSearch → WebFetch）

- WebSearch を mode "extended" で 2 回行う。クエリには今日の日付を入れる（例: 「生成AI ニュース 2026年10月24日」「AI news October 24, 2026」）。
- 結果のうち、ITmedia AI+、日経、Impress Watch、ZDNET Japan、各社の公式発表（OpenAI、Anthropic、Google、Meta など）、The Verge、TechCrunch、Reuters などの、当日の記事一覧やトップページ、個別記事を最大 3 ページ WebFetch で開き、見出し・記事URL・日時を取り出す。
- 過去 24 時間の記事だけを候補にする。

## 4. 記事を選ぶ

- 手順 2・3 の候補から、対象に当てはまるものを最大 10 本選ぶ。はてブのブックマーク数（users）や HN のポイント（points）が多いもの、複数の出典で取り上げられているもの、主要企業の公式発表を優先する。
- 同じ出来事の記事は 1 本にまとめる（公式発表か日本語の記事を優先）。
- 手順 1 で控えた URL は選ばない。

## 5. 投稿する

候補が 0 件なら投稿せずに終了します。それ以外は、`slack_send_message` で `C0CBWTUR1H7` に次の形式で 1 件だけ投稿します。

```
:robot_face: **AI きょうのニュース**(M/D HH:MM〜M/D HH:MM、日本時間)

- [記事タイトル](URL)(はてブ 120users)
- [英語の記事タイトル](URL) — 日本語の短い訳(Hacker News 300pt)
- [記事タイトル](URL)(ITmedia AI+)

候補 はてブ a件 / HN b件(raw.json の counts の値)+ Web c件から選定
```

- 出典はサイト名で書く。はてブや HN の数値があれば併記する（例: 「日経・はてブ 85users」）。
- 手順 2 や 3 が失敗した場合も、取れた分で投稿し、最後に「:warning: 取得失敗: (手順と要約)」を 1 行添える。両方とも失敗して候補が 0 件なら「:warning: AIニュースの取得に失敗しました(M/D) — 要約1行」と投稿する。
