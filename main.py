# =============================================================
# ライブラリ＆API認証情報
# =============================================================

# インポートするライブラリ
from flask import Flask, request, abort
from linebot import (
   LineBotApi, WebhookHandler
)
from linebot.exceptions import (
   InvalidSignatureError
)
from linebot.models import (
   FollowEvent, MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ButtonsTemplate, PostbackTemplateAction, MessageTemplateAction, URITemplateAction
)
import os
import re
import random
import openai
openai.organization = "org-GyrUX0PxZ501ZjT3yusFFWzl"
openai.api_key      = "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"
 
app = Flask(__name__)
 
#LINEのMessaging APIに記載してあるLINE Access Tokenと　CHANNEL SECRETを設定します。
LINE_CHANNEL_ACCESS_TOKEN = "JUEg1IV5F3xpdctl9I0zRtWNWCcDxqIbITR6X0BWxgJuxwAVMoGTVhZLcLuJrJYWtJjwPiMOFhYY8+azPWSSi+cQFvx6qdjELQbnJ8k/NslYatkj9rV0n70BWUElsKVHWj2hB3K5oI7HFK93pp1HIwdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "0f3b1f9f4b446b81ac134721127f61d6"
 
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@app.route("/callback", methods=['POST'])
def callback():
   # get X-Line-Signature header value
   signature = request.headers['X-Line-Signature']
   # get request body as text
   body = request.get_data(as_text=True)
   app.logger.info("Request body: " + body)
   # handle webhook body
   try:
       handler.handle(body, signature)
   except InvalidSignatureError:
       abort(400)
   return 'OK'
 
# MessageEvent
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text
    comment = ["えっ？なんて言ったの？", "しゃラップ", f"あなたは{event.message.text}と言ったのか？"]
    # 応答設定
    completion = openai.ChatCompletion.create(
                 model    = "gpt-3.5-turbo",     # モデルを選択
                 messages = [{
                            "role":"user",
                            "content":message,   # メッセージ 
                            }],
    
                 max_tokens  = 1024,             # 生成する文章の最大単語数
                 n           = 1,                # いくつの返答を生成するか
                 stop        = None,             # 指定した単語が出現した場合、文章生成を打ち切る
                 temperature = 0.5,              # 出力する単語のランダム性（0から2の範囲） 0であれば毎回返答内容固定
    )
    
    # 応答
    line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=completion.choices[0].message.content))


if __name__ == "__main__":
   port = int(os.getenv("PORT",5000))
   app.run(host="0.0.0.0", port=port)