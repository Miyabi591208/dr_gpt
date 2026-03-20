# dr_gpt

LINE Bot 上で動作する、対話型のマルチ機能アシスタントです。  
雑談、周辺のお店検索、数理・技術系の質問応答、記事化、Qiita 投稿までを 1 つのアプリで扱える構成になっています。

---

## 概要

`dr_gpt` は、LINE Messaging API を入口として、各種外部 API や OpenAI を組み合わせて動作する Python 製のアプリケーションです。

現時点では主に以下の用途に対応しています。

- 雑談モードでの自然な会話
- 現在地を用いた周辺のお店検索
- 数学・統計学・バイオインフォマティクスに関する質問応答
- 回答内容をもとにした Markdown 記事生成
- Qiita への記事投稿
- SQLite を用いた状態管理と会話履歴管理

---

## セットアップ

### 1. 依存関係

```
pip install -r requirements.txt
```

### 2. 環境変数

```
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
GOOGLE_MAPS_API_KEY=...
QIITA_ACCESS_TOKEN=...
SQLITE_PATH=app.db
```

### 3. 起動

```
python main.py
```

---

## 主な機能

### 雑談モード
会話履歴を保持しながら自然な対話が可能

### お店検索
位置情報 + Google Places API  
失敗時はフォールバック検索あり

### 数理計算
数学 / 統計 / バイオ系の質問対応

### 記事化
回答 → Markdown記事へ変換

### Qiita投稿
生成記事をそのまま投稿可能

---

## ディレクトリ構成

```
services/
  openai_service.py
  places_service.py
  qiita_service.py
main.py
line_ui.py
state_store.py
config.py
```

---

## 今後の拡張

- PubMed API連携
- 文献要約
- UX改善


