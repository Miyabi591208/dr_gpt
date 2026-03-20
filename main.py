# =============================================================
# LINE Bot + OpenAI (latest Responses API)
# main.py
# =============================================================

import os
import logging

from flask import Flask, request, abort
from openai import OpenAI

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# =============================================================
# 環境変数
# =============================================================
# 事前に以下を設定してください
# export OPENAI_API_KEY="..."
# export LINE_CHANNEL_ACCESS_TOKEN="..."
# export LINE_CHANNEL_SECRET="..."
# 任意:
# export OPENAI_MODEL="gpt-5.4"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# =============================================================
# 必須設定チェック
# =============================================================
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

# =============================================================
# 初期化
# =============================================================
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

openai_client = OpenAI(api_key=OPENAI_API_KEY)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# =============================================================
# OpenAIへ問い合わせる関数
# =============================================================
def ask_gpt(user_message: str) -> str:
    """
    LINEで受信したテキストを最新のOpenAI Responses APIへ送信し、
    返答テキストを返す。
    """
    try:
        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            reasoning={"effort": "low"},
            instructions=(
                "あなたはLINE上で丁寧かつ簡潔に回答するアシスタントです。"
                "日本語で自然に回答してください。"
                "必要以上に長くせず、相手に伝わりやすい表現にしてください。"
            ),
            input=user_message,
            max_output_tokens=1024,
        )

        reply_text = (response.output_text or "").strip()

        if not reply_text:
            return "申し訳ありません。うまく応答を生成できませんでした。"

        return reply_text

    except Exception as e:
        app.logger.exception("OpenAI API error: %s", e)
        return (
            "申し訳ありません。現在応答の生成中にエラーが発生しました。"
            "少し時間をおいて再度お試しください。"
        )

# =============================================================
# LINE Webhook
# =============================================================
@app.route("/callback", methods=["POST"])
def callback():
    # X-Line-Signature を取得
    signature = request.headers.get("X-Line-Signature", "")

    # リクエストボディ取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: %s", body)

    # LINE署名検証 + イベント処理
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid signature.")
        abort(400)
    except Exception as e:
        app.logger.exception("Webhook handling error: %s", e)
        abort(500)

    return "OK"

# =============================================================
# テキストメッセージ受信時
# =============================================================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = (event.message.text or "").strip()

    if not user_message:
        reply_text = "メッセージが空のようです。文字を入力して送ってください。"
    else:
        reply_text = ask_gpt(user_message)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# =============================================================
# 起動
# =============================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
