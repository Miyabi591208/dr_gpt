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
    if re.search('水の呼吸',event.message.text) or re.search('みずのこきゅう',event.message.text):
        if re.search('壱',event.message.text) or re.search('いち',event.message.text):
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text="水面斬り"))
        elif re.search('弐', event.message.text) or re.search('に', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="水車")
            )
        elif re.search('参', event.message.text) or re.search('さん', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="流流舞い")
            )
        elif re.search('肆ノ型', event.message.text) or re.search('し', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="打ち潮")
            )
        elif re.search('伍ノ型', event.message.text) or re.search('ご', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="干天の慈雨")
            )
        elif re.search('陸ノ型', event.message.text) or re.search('ろく', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ねじれ渦")
            )
        elif re.search('漆ノ型', event.message.text) or re.search('しち', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="雫波紋突き")
            )
        elif re.search('捌ノ型', event.message.text) or re.search('はち', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="滝壺")
            )
        elif re.search('玖ノ型', event.message.text) or re.search('くの', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="水流飛沫・乱")
            )
        elif re.search('拾ノ型', event.message.text) or re.search('じゅう', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="生生流転")
            )
        elif re.search('拾壱ノ型', event.message.text) or re.search('じゅういち', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="凪")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="そんなのないよ")
            )
    elif re.search('火の呼吸', event.message.text) or re.search('ひのこきゅう', event.message.text):
        if re.search('壱',event.message.text) or re.search('いち',event.message.text):
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text="火の神神楽"))

    elif re.search('煉獄さん', event.message.text) or re.search('れんごくさん', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="心を燃やせ！！！"))

    elif re.search('禰󠄀豆子', event.message.text) or re.search('ねずこ', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ねずこーーーー！！！"))

    elif re.search('ねずみ', event.message.text) or re.search('筋肉', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ムキ！！！"))

    elif re.search('白鳥', event.message.text) or re.search('ハクチョウ', event.message.text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="クワっ！！！"))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"あなたは{event.message.text}と言ったのか？")
        )
if __name__ == "__main__":
   port = int(os.getenv("PORT",5000))
   app.run(host="0.0.0.0", port=port)