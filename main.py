import logging
import re
import time

from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    FollowEvent,
    LocationMessageContent,
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)

from config import Config
from line_ui import (
    article_action_message,
    article_post_confirm_message,
    ask_area_keyword_message,
    ask_budget_message,
    ask_calc_domain_message,
    ask_shop_genre_message,
    ask_shop_search_method_message,
    main_menu_message,
    shop_results_flex_message,
    shop_summary_text,
    text_chunks_as_messages,
    top_location_message,
)
from services.openai_service import OpenAIService
from services.places_service import PlacesService
from services.pubmed_service import PubMedService
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
pubmed_service = PubMedService(
    api_key=Config.PUBMED_API_KEY or None,
    tool_name=Config.PUBMED_TOOL_NAME,
    email=Config.PUBMED_EMAIL or None,
)

CHAT_HISTORY_LIMIT_INPUT = 10
CHAT_HISTORY_LIMIT_STORE = 20
LINE_MAX_MESSAGES_PER_REQUEST = 5


def get_user_id(event) -> str:
    if hasattr(event, "source") and getattr(event.source, "user_id", None):
        return event.source.user_id
    return "anonymous"


def _normalize_messages(messages):
    if messages is None:
        return []
    if not isinstance(messages, list):
        return [messages]
    return messages


def reply(event, messages) -> None:
    messages = _normalize_messages(messages)
    if not messages:
        return

    with ApiClient(line_config) as api_client:
        api = MessagingApi(api_client)
        api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages[:LINE_MAX_MESSAGES_PER_REQUEST],
            )
        )


def push(user_id: str, messages) -> None:
    messages = _normalize_messages(messages)
    if not messages or not user_id or user_id == "anonymous":
        return

    with ApiClient(line_config) as api_client:
        api = MessagingApi(api_client)

        for i in range(0, len(messages), LINE_MAX_MESSAGES_PER_REQUEST):
            chunk = messages[i:i + LINE_MAX_MESSAGES_PER_REQUEST]
            api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=chunk,
                )
            )
            if i + LINE_MAX_MESSAGES_PER_REQUEST < len(messages):
                time.sleep(0.15)


def reply_then_push(event, user_id: str, messages, reply_count: int = 1) -> None:
    messages = _normalize_messages(messages)
    if not messages:
        return

    first = messages[:reply_count]
    rest = messages[reply_count:]

    if first:
        reply(event, first)
    if rest:
        push(user_id, rest)


def normalize_mode_text(text: str) -> str:
    return text.strip()


def extract_title_from_markdown(article_md: str, fallback: str = "技術記事") -> str:
    if not article_md:
        return fallback

    for line in article_md.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        m = re.match(r"^#{1,6}\s+(.+)$", stripped)
        if m:
            title = m.group(1).strip()
            if title:
                return title[:100]

        m2 = re.match(r"^(タイトル|title)\s*[:：]\s*(.+)$", stripped, re.IGNORECASE)
        if m2:
            title = m2.group(2).strip()
            if title:
                return title[:100]

    return fallback[:100]


def build_qiita_tags(domain: str) -> list[str]:
    tags = ["ChatGPT"]

    normalized = (domain or "").strip()
    if normalized:
        tags.append(normalized)

    if normalized == "数学":
        tags.append("数学")
    elif normalized == "統計学":
        tags.append("統計")
    elif normalized == "バイオインフォマティクス":
        tags.append("Bioinformatics")
    elif normalized == "文献検索":
        tags.append("PubMed")

    seen = set()
    unique_tags = []
    for tag in tags:
        if tag and tag not in seen:
            unique_tags.append(tag)
            seen.add(tag)

    return unique_tags[:5]


def format_pubmed_results(query: str, articles: list[dict]) -> str:
    if not articles:
        return (
            f"PubMedで文献が見つかりませんでした。\n"
            f"検索語: {query}\n\n"
            "別のキーワード、英語表現、遺伝子名、疾患名、手法名などで再検索してください。"
        )

    lines = [
        "PubMed検索結果",
        f"検索語: {query}",
        "",
    ]

    for i, article in enumerate(articles, start=1):
        lines.append(f"{i}. {article.get('title', 'タイトル不明')}")
        if article.get("authors"):
            lines.append(f"著者: {article['authors']}")
        meta_parts = []
        if article.get("journal"):
            meta_parts.append(article["journal"])
        if article.get("pubdate"):
            meta_parts.append(article["pubdate"])
        if meta_parts:
            lines.append("掲載情報: " + " / ".join(meta_parts))
        lines.append(f"PMID: {article.get('pmid', '')}")
        if article.get("doi"):
            lines.append(f"DOI: {article['doi']}")
        if article.get("url"):
            lines.append(article["url"])
        lines.append("")

    return "\n".join(lines).strip()


def start_shop_flow(user_id: str, event) -> None:
    state_store.set(user_id, "shop", "waiting_search_method", {})
    reply(event, ask_shop_search_method_message())


def start_calc_flow(user_id: str, event) -> None:
    state_store.set(user_id, "calc", "waiting_domain", {})
    reply(event, ask_calc_domain_message())


def start_chat_flow(user_id: str, event) -> None:
    state_store.set(user_id, "chat", "waiting_message", {})
    reply(
        event,
        TextMessage(
            text=(
                "雑談モードです。自由に話しかけてください。\n"
                "過去の会話文脈もある程度踏まえて返答します。\n"
                "メニューに戻る場合は「メニュー」と送ってください。"
            )
        ),
    )


def start_article_flow(user_id: str, event) -> None:
    state = state_store.get(user_id)
    data = state.get("data", {})

    if not data.get("last_question") or not data.get("last_answer") or not data.get("last_domain"):
        reply(
            event,
            TextMessage(text="記事化する元データがありません。先に数理計算モードで質問してください。"),
        )
        return

    article_md = openai_service.draft_article(
        domain=data["last_domain"],
        question=data["last_question"],
        answer=data["last_answer"],
    )

    fallback_title = f"{data['last_domain']}に関する解説"
    article_title = extract_title_from_markdown(article_md, fallback=fallback_title)

    data["last_article"] = article_md
    data["last_article_title"] = article_title
    data["article_ready_for_qiita"] = True
    data["last_qiita_post_url"] = None
    data["last_qiita_post_id"] = None

    state_store.set(user_id, "article", "waiting_qiita_confirm", data)

    messages = text_chunks_as_messages(article_md, chunk_size=4500)

    if qiita_service.is_enabled():
        messages.append(article_post_confirm_message(article_title))
    else:
        messages.append(
            TextMessage(
                text=(
                    "記事を作成しました。\n"
                    "ただし Qiita 投稿用トークンが未設定のため、自動投稿はできません。\n"
                    "必要であれば QIITA_ACCESS_TOKEN を設定してください。"
                )
            )
        )

    reply_then_push(event, user_id, messages, reply_count=1)


def post_article_to_qiita(user_id: str, event) -> None:
    state = state_store.get(user_id)
    data = state.get("data", {})

    article_md = data.get("last_article")
    article_title = data.get("last_article_title")
    last_domain = data.get("last_domain")

    if not article_md or not article_title:
        reply(
            event,
            [
                TextMessage(text="投稿対象の記事データが見つかりません。先に「記事化」を実行してください。"),
                main_menu_message(),
            ],
        )
        return

    if not qiita_service.is_enabled():
        reply(
            event,
            TextMessage(text="QIITA_ACCESS_TOKEN が未設定のため、Qiitaへ投稿できません。"),
        )
        return

    if data.get("last_qiita_post_url"):
        reply(
            event,
            [
                TextMessage(
                    text=(
                        "この記事はすでにQiitaへ投稿済みです。\n"
                        f"{data['last_qiita_post_url']}"
                    )
                ),
                main_menu_message(),
            ],
        )
        return

    tags = build_qiita_tags(last_domain)

    try:
        result = qiita_service.create_item(
            title=article_title,
            body_markdown=article_md,
            tags=tags,
            private=False,
        )
    except Exception as e:
        app.logger.exception("Qiita post failed: %s", e)
        reply(
            event,
            TextMessage(
                text=(
                    "Qiita投稿でエラーが発生しました。\n"
                    "トークン権限、タグ、本文サイズ、Qiita側ステータスをご確認ください。"
                )
            ),
        )
        return

    data["last_qiita_post_url"] = result.get("url")
    data["last_qiita_post_id"] = result.get("id")
    data["article_ready_for_qiita"] = False

    state_store.set(user_id, "calc", "waiting_question", data)

    messages = [
        TextMessage(
            text=(
                "Qiitaへ投稿しました。\n"
                f"タイトル: {article_title}"
            )
        )
    ]

    if result.get("url"):
        messages.append(TextMessage(text=result["url"]))

    messages.append(main_menu_message())
    reply(event, messages)


def chat_with_history(user_id: str, user_text: str) -> str:
    history = state_store.get_chat_history(user_id, limit=CHAT_HISTORY_LIMIT_INPUT)

    answer = openai_service.chat(
        user_text=user_text,
        history=history,
    )

    state_store.append_chat_message(user_id, "user", user_text)
    state_store.append_chat_message(user_id, "assistant", answer)
    state_store.trim_chat_history(user_id, keep_last=CHAT_HISTORY_LIMIT_STORE)

    return answer


def handle_shop_search_and_reply(event, user_id: str, data: dict) -> None:
    genre = data.get("genre", "和食")
    budget = data.get("budget", "こだわらない")

    try:
        if data.get("location"):
            location = data["location"]
            places = places_service.search_nearby_shops(
                latitude=location["lat"],
                longitude=location["lng"],
                genre=genre,
                budget=budget,
                radius_meters=Config.SHOP_RADIUS_METERS,
                max_results=5,
            )
            origin_lat = location["lat"]
            origin_lng = location["lng"]
            area_label = location.get("address") or location.get("title") or None
        elif data.get("area_query"):
            places, center = places_service.search_nearby_shops_from_area(
                area_query=data["area_query"],
                genre=genre,
                budget=budget,
                radius_meters=Config.SHOP_RADIUS_METERS,
                max_results=5,
            )
            origin_lat = center["lat"]
            origin_lng = center["lng"]
            area_label = data["area_query"]
        else:
            reply(
                event,
                TextMessage(text="位置情報またはエリア名が必要です。"),
            )
            return

    except Exception as e:
        app.logger.exception("Shop search failed: %s", e)
        state_store.clear(user_id)
        reply(
            event,
            [
                TextMessage(
                    text=(
                        "お店検索で候補を取得できませんでした。\n"
                        "位置情報が使えない場合は、駅名やエリア名で再度お試しください。"
                    )
                ),
                ask_shop_search_method_message(),
            ],
        )
        return

    if not places:
        state_store.clear(user_id)
        reply(event, [shop_summary_text([]), main_menu_message()])
        return

    state_store.clear(user_id)

    messages = []
    if places[0].get("source") == "osm_fallback":
        messages.append(
            TextMessage(
                text=(
                    "Google Maps API から候補を取得できなかったため、"
                    "代替検索で周辺候補を表示しています。"
                    "評価や価格帯は十分に取得できない場合があります。"
                )
            )
        )

    messages.extend(
        [
            shop_summary_text(places, area_label=area_label),
            shop_results_flex_message(
                places=places,
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                build_directions_url=places_service.build_directions_url,
            ),
        ]
    )

    top = places[0]
    if top.get("lat") is not None and top.get("lng") is not None:
        messages.append(top_location_message(top))

    reply(event, messages)


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

    if state.get("mode") == "shop" and state.get("step") in {"waiting_search_method", "waiting_location"}:
        data = state.get("data", {})
        data["location"] = {
            "lat": event.message.latitude,
            "lng": event.message.longitude,
            "address": getattr(event.message, "address", ""),
            "title": getattr(event.message, "title", ""),
        }
        data.pop("area_query", None)
        state_store.set(user_id, "shop", "waiting_genre", data)
        reply(event, ask_shop_genre_message())
        return

    reply(
        event,
        TextMessage(text="位置情報を受け取りました。店探しを始める場合は「おすすめの店」を選んでください。"),
    )


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

    if text in {"履歴削除", "会話履歴削除", "雑談履歴削除"}:
        state_store.clear_chat_history(user_id)
        reply(event, TextMessage(text="雑談の会話履歴を削除しました。"))
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

    if text in {"記事化", "記事化する"}:
        start_article_flow(user_id, event)
        return

    if text == "Qiitaに投稿する":
        post_article_to_qiita(user_id, event)
        return

    if mode == "shop":
        if step == "waiting_search_method":
            if text == "エリア名で探す":
                state_store.set(user_id, "shop", "waiting_area_query", data)
                reply(event, ask_area_keyword_message())
                return
            else:
                reply(event, ask_shop_search_method_message())
                return

        if step == "waiting_area_query":
            data["area_query"] = text
            data.pop("location", None)
            state_store.set(user_id, "shop", "waiting_genre", data)
            reply(event, ask_shop_genre_message())
            return

        if step == "waiting_genre":
            data["genre"] = text
            state_store.set(user_id, "shop", "waiting_budget", data)
            reply(event, ask_budget_message())
            return

        if step == "waiting_budget":
            data["budget"] = text
            state_store.set(user_id, "shop", "searching", data)
            handle_shop_search_and_reply(event, user_id, data)
            return

    if mode == "calc":
        if step == "waiting_domain":
            data["last_domain"] = text
            state_store.set(user_id, "calc", "waiting_question", data)

            if text == "文献検索":
                reply(
                    event,
                    TextMessage(
                        text=(
                            "PubMed文献検索モードです。\n"
                            "検索したいキーワードを送ってください。\n"
                            "例: single cell RNA-seq kidney fibrosis"
                        )
                    ),
                )
            else:
                reply(event, TextMessage(text=f"{text}モードです。質問文を送ってください。"))
            return

        if step == "waiting_question":
            domain = data.get("last_domain", "数学")

            if domain == "文献検索":
                try:
                    articles = pubmed_service.search_articles(
                        query=text,
                        retmax=Config.PUBMED_MAX_RESULTS,
                        sort="relevance",
                    )
                except Exception as e:
                    app.logger.exception("PubMed search failed: %s", e)
                    reply(
                        event,
                        TextMessage(
                            text=(
                                "PubMed検索でエラーが発生しました。\n"
                                "検索語を短くするか、英語キーワードで再度お試しください。"
                            )
                        ),
                    )
                    return

                result_text = format_pubmed_results(text, articles)
                data["last_question"] = text
                data["last_answer"] = result_text
                state_store.set(user_id, "calc", "waiting_question", data)

                messages = text_chunks_as_messages(result_text, chunk_size=4500)
                if len(messages) <= 4:
                    messages.append(article_action_message())

                reply_then_push(event, user_id, messages, reply_count=1)
                return

            answer = openai_service.solve_calculation(domain=domain, user_text=text)
            data["last_question"] = text
            data["last_answer"] = answer
            state_store.set(user_id, "calc", "waiting_question", data)

            messages = text_chunks_as_messages(answer, chunk_size=4500)
            if len(messages) <= 4:
                messages.append(article_action_message())

            reply_then_push(event, user_id, messages, reply_count=1)
            return

    if mode == "article" and step == "waiting_qiita_confirm":
        reply(
            event,
            article_post_confirm_message(data.get("last_article_title", "技術記事")),
        )
        return

    if mode == "chat":
        answer = chat_with_history(user_id, text)
        messages = text_chunks_as_messages(answer, chunk_size=4500)
        reply_then_push(event, user_id, messages, reply_count=1)
        return

    answer = openai_service.chat(text)
    messages = text_chunks_as_messages(answer, chunk_size=4500)
    reply_then_push(event, user_id, messages, reply_count=1)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
