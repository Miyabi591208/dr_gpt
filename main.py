import logging

from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import FollowEvent, LocationMessageContent, MessageEvent, PostbackEvent, TextMessageContent

from config import Config
from line_ui import (
    article_action_message,
    ask_budget_message,
    ask_calc_domain_message,
    ask_location_message,
    ask_shop_genre_message,
    main_menu_message,
    shop_results_flex_message,
    shop_summary_text,
    text_chunks_as_messages,
    top_location_message,
)
from services.openai_service import OpenAIService
from services.places_service import PlacesService
from services.qiita_service import QiitaService
from state_store import StateStore

Config.validate()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)
line_config = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)

state_store = StateStore(Config.SQLITE_PATH)
openai_service = OpenAIService(Config.OPENAI_API_KEY, Config.OPENAI_MODEL)
places_service = PlacesService(Config.GOOGLE_MAPS_API_KEY)
qiita_service = QiitaService(Config.QIITA_ACCESS_TOKEN)


def get_user_id(event) -> str:
    if hasattr(event, "source") and getattr(event.source, "user_id", None):
        return event.source.user_id
    return "anonymous"


def reply(event, messages) -> None:
    if not isinstance(messages, list):
        messages = [messages]

    with ApiClient(line_config) as api_client:
        api = MessagingApi(api_client)
        api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages[:5],
            )
        )


def normalize_mode_text(text: str) -> str:
    return text.strip()


def start_shop_flow(user_id: str, event) -> None:
    state_store.set(user_id, "shop", "waiting_location", {})
    reply(event, ask_location_message())


def start_calc_flow(user_id: str, event) -> None:
    state_store.set(user_id, "calc", "waiting_domain", {})
    reply(event, ask_calc_domain_message())


def start_chat_flow(user_id: str, event) -> None:
    state_store.set(user_id, "chat", "waiting_message", {})
    reply(event, TextMessage(text="雑談モードです。自由に話しかけてください。メニューに戻る場合は「メニュー」と送ってください。"))


def start_article_flow(user_id: str, event) -> None:
    state = state_store.get(user_id)
    data = state.get("data", {})
    if not data.get("last_question") or not data.get("last_answer") or not data.get("last_domain"):
        reply(event, TextMessage(text="記事化する元データがありません。先に数理計算モードで質問してください。"))
        return
    article_md = openai_service.draft_article(
        domain=data["last_domain"],
        question=data["last_question"],
        answer=data["last_answer"],
    )
    data["last_article"] = article_md
    state_store.set(user_id, state.get("mode"), state.get("step"), data)

    messages = text_chunks_as_messages(article_md)
    if qiita_service.is_enabled():
        messages.append(TextMessage(text="Qiita連携用トークンが設定されています。必要ならこのMarkdownを元に別処理で投稿できます。"))
    reply(event, messages[:5])


@app.route("/", methods=["GET"])
def healthcheck():
    return "OK", 200


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    app.logger.info("Webhook body: %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        app.logger.exception("Webhook handling error: %s", e)
        abort(500)

    return "OK"


@handler.add(FollowEvent)
def handle_follow(event):
    reply(event, [TextMessage(text="友だち追加ありがとうございます。"), main_menu_message()])


@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = get_user_id(event)
    data = getattr(event.postback, "data", "") or ""

    mapping = {
        "mode=shop": "おすすめの店",
        "mode=calc": "数理計算",
        "mode=chat": "雑談",
        "mode=article": "記事化",
        "mode=menu": "メニュー",
    }

    text = mapping.get(data)
    if text:
        class DummyMessage:
            pass
        event.message = DummyMessage()
        event.message.text = text
        handle_text_message(event)


@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    user_id = get_user_id(event)
    state = state_store.get(user_id)

    if state.get("mode") == "shop" and state.get("step") == "waiting_location":
        data = state.get("data", {})
        data["location"] = {
            "lat": event.message.latitude,
            "lng": event.message.longitude,
            "address": getattr(event.message, "address", ""),
            "title": getattr(event.message, "title", ""),
        }
        state_store.set(user_id, "shop", "waiting_genre", data)
        reply(event, ask_shop_genre_message())
        return

    reply(event, TextMessage(text="位置情報を受け取りました。店探しを始める場合は「おすすめの店」を選んでください。"))


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = get_user_id(event)
    text = normalize_mode_text(event.message.text)
    state = state_store.get(user_id)
    mode = state.get("mode")
    step = state.get("step")
    data = state.get("data", {})

    if text in {"メニュー", "menu", "MENU"}:
        state_store.clear(user_id)
        reply(event, main_menu_message())
        return

    if text == "キャンセル":
        state_store.clear(user_id)
        reply(event, [TextMessage(text="キャンセルしました。"), main_menu_message()])
        return

    if text == "おすすめの店":
        start_shop_flow(user_id, event)
        return

    if text == "数理計算":
        start_calc_flow(user_id, event)
        return

    if text == "雑談":
        start_chat_flow(user_id, event)
        return

    if text == "記事化":
        start_article_flow(user_id, event)
        return

    if text == "記事化する":
        start_article_flow(user_id, event)
        return

    if mode == "shop":
        if step == "waiting_genre":
            data["genre"] = text
            state_store.set(user_id, "shop", "waiting_budget", data)
            reply(event, ask_budget_message())
            return

        if step == "waiting_budget":
            data["budget"] = text
            location = data.get("location")
            if not location:
                state_store.set(user_id, "shop", "waiting_location", data)
                reply(event, ask_location_message())
                return

            try:
                places = places_service.search_nearby_shops(
                    latitude=location["lat"],
                    longitude=location["lng"],
                    genre=data.get("genre", "和食"),
                    budget=data.get("budget", "こだわらない"),
                    radius_meters=Config.SHOP_RADIUS_METERS,
                    max_results=Config.SHOP_MAX_RESULTS,
                )
            except Exception as e:
                app.logger.exception("Shop search failed: %s", e)
                reply(event, TextMessage(text="店舗検索でエラーが発生しました。Google Maps API設定をご確認ください。"))
                return

            if not places:
                state_store.clear(user_id)
                reply(event, [shop_summary_text([]), main_menu_message()])
                return

            state_store.clear(user_id)
            messages = [
                shop_summary_text(places),
                shop_results_flex_message(
                    places=places,
                    origin_lat=location["lat"],
                    origin_lng=location["lng"],
                    build_directions_url=places_service.build_directions_url,
                ),
            ]

            top = places[0]
            if top.get("lat") is not None and top.get("lng") is not None:
                messages.append(top_location_message(top))
            reply(event, messages[:5])
            return

    if mode == "calc":
        if step == "waiting_domain":
            data["last_domain"] = text
            state_store.set(user_id, "calc", "waiting_question", data)
            reply(event, TextMessage(text=f"{text}モードです。質問文を送ってください。"))
            return

        if step == "waiting_question":
            domain = data.get("last_domain", "数学")
            answer = openai_service.solve_calculation(domain=domain, user_text=text)
            data["last_question"] = text
            data["last_answer"] = answer
            state_store.set(user_id, "calc", "waiting_question", data)

            messages = text_chunks_as_messages(answer)
            if len(messages) <= 4:
                messages.append(article_action_message())
            reply(event, messages[:5])
            return

    if mode == "chat":
        answer = openai_service.chat(text)
        reply(event, text_chunks_as_messages(answer))
        return

    answer = openai_service.chat(text)
    reply(event, text_chunks_as_messages(answer))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)