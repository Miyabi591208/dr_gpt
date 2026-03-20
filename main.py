# =============================================================
# LINE Bot + OpenAI + Flask (Render production-ready, LINE SDK v3)
# main.py
# =============================================================

import logging
import os

from dotenv import load_dotenv
from flask import Flask, abort, request
from openai import OpenAI

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# -------------------------------------------------------------
# .env 読み込み（ローカル開発用）
# Render本番ではダッシュボードの Environment Variables が使われる
# -------------------------------------------------------------
load_dotenv()

# -------------------------------------------------------------
# 環境変数
# -------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# -------------------------------------------------------------
# 必須設定チェック
# -------------------------------------------------------------
missing_envs = []
if not OPENAI_API_KEY:
    missing_envs.append("OPENAI_API_KEY")
if not LINE_CHANNEL_ACCESS_TOKEN:
    missing_envs.append("LINE_CHANNEL_ACCESS_TOKEN")
if not LINE_CHANNEL_SECRET:
    missing_envs.append("LINE_CHANNEL_SECRET")

if missing_envs:
    raise RuntimeError(
        "必要な環境変数が未設定です: " + ", ".join(missing_envs)
    )

# -------------------------------------------------------------
# Flask / OpenAI / LINE 初期化
# -------------------------------------------------------------
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

openai_client = OpenAI(api_key=OPENAI_API_KEY)

line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# -------------------------------------------------------------
# OpenAI 応答生成
# -------------------------------------------------------------
def ask_gpt(user_message: str) -> str:
    """
    ユーザーのテキストを OpenAI Responses API に送り、
    返信テキストを返す。
    """
    try:
        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            reasoning={"effort": "low"},
            instructions=(
                "あなたはLINE上で丁寧かつ簡潔に回答するアシスタントです。"
                "日本語で自然に回答してください。"
                "必要以上に長くなりすぎず、相手に伝わりやすく答えてください。"
            ),
            input=user_message,
            max_output_tokens=1024,
        )

        reply_text = (response.output_text or "").strip()

        if not reply_text:
            return "申し訳ありません。うまく応答を生成できませんでした。"

        # LINEの返信文字数が過度に長くなりすぎるのを軽減
        return reply_text[:4900]

    except Exception as e:
        app.logger.exception("OpenAI API error: %s", e)
        return (
            "申し訳ありません。現在応答の生成中にエラーが発生しました。"
            "少し時間をおいて再度お試しください。"
        )

# -------------------------------------------------------------
# Health check
# -------------------------------------------------------------
@app.route("/", methods=["GET"])
def healthcheck():
    return "OK", 200

# -------------------------------------------------------------
# LINE Webhook
# -------------------------------------------------------------
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    app.logger.info("Webhook body: %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid signature.")
        abort(400)
    except Exception as e:
        app.logger.exception("Webhook handling error: %s", e)
        abort(500)

    return "OK"

# -------------------------------------------------------------
# テキストメッセージ受信
# -------------------------------------------------------------
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_message = (event.message.text or "").strip()

    if not user_message:
        reply_text = "メッセージが空のようです。文字を入力して送ってください。"
    else:
        reply_text = ask_gpt(user_message)

    try:
        with ApiClient(line_config) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )
    except Exception as e:
        app.logger.exception("LINE reply error: %s", e)

# -------------------------------------------------------------
# ローカル起動用
# Render本番では gunicorn main:app を使う
# -------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
