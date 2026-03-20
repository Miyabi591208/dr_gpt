import json
from typing import Sequence

from linebot.v3.messaging import (
    FlexContainer,
    FlexMessage,
    LocationAction,
    LocationMessage,
    MessageAction,
    QuickReply,
    QuickReplyItem,
    TextMessage,
)

LINE_TEXT_HARD_LIMIT = 5000
LINE_TEXT_SAFE_LIMIT = 4500


def main_menu_message() -> TextMessage:
    return TextMessage(
        text=(
            "よう来てくれたのう！🔬✨\n"
            "わしは DrGPT じゃよ 👨‍🔬\n\n"
            "📚 メニューはこちらじゃ！\n"
            "・雑談 💬\n"
            "・おすすめの店 🍜\n"
            "・数理計算 📐\n"
            "・記事化 ✍️\n\n"
            "やりたいことを選ぶのじゃ〜！🚀"
        ),
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="雑談", text="雑談")),
                QuickReplyItem(action=MessageAction(label="おすすめの店", text="おすすめの店")),
                QuickReplyItem(action=MessageAction(label="数理計算", text="数理計算")),
                QuickReplyItem(action=MessageAction(label="記事化", text="記事化")),
                QuickReplyItem(action=MessageAction(label="キャンセル", text="キャンセル")),
            ]
        ),
    )


def ask_shop_search_method_message() -> TextMessage:
    return TextMessage(
        text=(
            "ふむ、お店探しじゃな 🍽️\n"
            "探し方を選ぶのじゃよ！\n\n"
            "📍 位置情報を送る\n"
            "🗺️ 駅名やエリア名で探す"
        ),
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=LocationAction(label="位置情報を送る")),
                QuickReplyItem(action=MessageAction(label="エリア名で探す", text="エリア名で探す")),
                QuickReplyItem(action=MessageAction(label="キャンセル", text="キャンセル")),
            ]
        ),
    )


def ask_area_keyword_message() -> TextMessage:
    return TextMessage(
        text=(
            "駅名・エリア名・住所を送ってほしいのじゃ 🗺️✨\n"
            "たとえば、こんな感じじゃよ。\n\n"
            "・柏駅\n"
            "・新宿\n"
            "・東京都千代田区丸の内"
        ),
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="キャンセル", text="キャンセル")),
            ]
        ),
    )


def ask_shop_genre_message() -> TextMessage:
    return TextMessage(
        text="どんなジャンルのお店を探すのじゃ？ 🍜☕🍣",
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="ラーメン", text="ラーメン")),
                QuickReplyItem(action=MessageAction(label="カフェ", text="カフェ")),
                QuickReplyItem(action=MessageAction(label="焼肉", text="焼肉")),
                QuickReplyItem(action=MessageAction(label="和食", text="和食")),
                QuickReplyItem(action=MessageAction(label="居酒屋", text="居酒屋")),
                QuickReplyItem(action=MessageAction(label="寿司", text="寿司")),
                QuickReplyItem(action=MessageAction(label="キャンセル", text="キャンセル")),
            ]
        ),
    )


def ask_budget_message() -> TextMessage:
    return TextMessage(
        text="予算帯はどのくらいを考えておるかのう？ 💴",
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="〜1000円", text="〜1000円")),
                QuickReplyItem(action=MessageAction(label="1000〜3000円", text="1000〜3000円")),
                QuickReplyItem(action=MessageAction(label="3000円以上", text="3000円以上")),
                QuickReplyItem(action=MessageAction(label="こだわらない", text="こだわらない")),
                QuickReplyItem(action=MessageAction(label="キャンセル", text="キャンセル")),
            ]
        ),
    )


def ask_calc_domain_message() -> TextMessage:
    return TextMessage(
        text=(
            "よし、数理や知識の相談じゃな 📚✨\n"
            "どの分野で答えるのがよいか、選ぶのじゃよ。"
        ),
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="数学", text="数学")),
                QuickReplyItem(action=MessageAction(label="統計学", text="統計学")),
                QuickReplyItem(action=MessageAction(label="バイオインフォマティクス", text="バイオインフォマティクス")),
                QuickReplyItem(action=MessageAction(label="文献検索", text="文献検索")),
                QuickReplyItem(action=MessageAction(label="キャンセル", text="キャンセル")),
            ]
        ),
    )


def article_action_message() -> TextMessage:
    return TextMessage(
        text=(
            "直前の回答をもとに記事へまとめられるのじゃ ✍️✨\n"
            "このまま記事化してみるかのう？"
        ),
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="記事化する", text="記事化する")),
                QuickReplyItem(action=MessageAction(label="メニュー", text="メニュー")),
            ]
        ),
    )


def article_post_confirm_message(title: str) -> TextMessage:
    safe_title = (title or "無題").strip()[:80]
    return TextMessage(
        text=(
            "記事ができあがったのじゃ！📝✨\n"
            f"タイトル案: {safe_title}\n\n"
            "Qiitaへ投稿してみるかのう？"
        ),
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="Qiitaに投稿する", text="Qiitaに投稿する")),
                QuickReplyItem(action=MessageAction(label="メニュー", text="メニュー")),
                QuickReplyItem(action=MessageAction(label="キャンセル", text="キャンセル")),
            ]
        ),
    )


def top_location_message(place: dict) -> LocationMessage:
    return LocationMessage(
        title=place["name"][:100],
        address=place["address"][:100],
        latitude=float(place["lat"]),
        longitude=float(place["lng"]),
    )


def shop_results_flex_message(
    places: Sequence[dict],
    origin_lat: float,
    origin_lng: float,
    build_directions_url,
) -> FlexMessage:
    bubbles = []

    for place in places[:5]:
        directions_url = build_directions_url(
            origin_lat,
            origin_lng,
            place["lat"],
            place["lng"],
        )
        maps_url = place.get("google_maps_uri") or directions_url

        rating_text = "評価なし"
        if place.get("rating") is not None:
            rating_text = f"★ {place['rating']} ({place.get('reviews', 0)}件)"

        distance_text = ""
        if place.get("distance_m") is not None:
            distance_text = f"距離: 約{int(place['distance_m'])}m"

        body_contents = [
            {
                "type": "text",
                "text": place["name"],
                "weight": "bold",
                "size": "lg",
                "wrap": True,
            },
            {
                "type": "text",
                "text": rating_text,
                "size": "sm",
                "color": "#666666",
                "wrap": True,
            },
        ]

        if distance_text:
            body_contents.append(
                {
                    "type": "text",
                    "text": distance_text,
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True,
                }
            )

        body_contents.append(
            {
                "type": "text",
                "text": place["address"],
                "size": "sm",
                "wrap": True,
                "color": "#666666",
            }
        )

        bubble = {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": body_contents,
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "最短経路を開く",
                            "uri": directions_url,
                        },
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "Google Mapsで見る",
                            "uri": maps_url,
                        },
                    },
                ],
            },
        }
        bubbles.append(bubble)

    carousel = {"type": "carousel", "contents": bubbles}
    return FlexMessage(
        alt_text="周辺のお店候補です",
        contents=FlexContainer.from_json(json.dumps(carousel, ensure_ascii=False)),
    )


def shop_summary_text(places: Sequence[dict], area_label: str | None = None) -> TextMessage:
    if not places:
        return TextMessage(text="候補が見つからなかったのじゃ…条件を変えてもう一度試してほしいのう。")

    title = "候補が見つかったのじゃ！上位候補はこちらじゃよ 🍽️"
    if area_label:
        title = f"{area_label} 周辺で候補が見つかったのじゃ！上位候補はこちらじゃよ 🍽️"

    lines = [title]
    for idx, p in enumerate(places[:5], start=1):
        rating = p.get("rating")
        distance = p.get("distance_m")
        suffix = []
        if rating is not None:
            suffix.append(f"★{rating}")
        if distance is not None:
            suffix.append(f"約{int(distance)}m")

        if suffix:
            lines.append(f"{idx}. {p['name']} / " + " / ".join(suffix))
        else:
            lines.append(f"{idx}. {p['name']}")

    return TextMessage(text="\n".join(lines))


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _slice_by_utf16_limit(text: str, limit: int) -> tuple[str, str]:
    if _utf16_len(text) <= limit:
        return text, ""

    current = []
    current_len = 0

    for ch in text:
        ch_len = _utf16_len(ch)
        if current_len + ch_len > limit:
            break
        current.append(ch)
        current_len += ch_len

    head = "".join(current)
    tail = text[len(head):]
    return head, tail


def text_chunks_as_messages(text: str, chunk_size: int = LINE_TEXT_SAFE_LIMIT) -> list[TextMessage]:
    text = (text or "").strip()
    if not text:
        return [TextMessage(text="")]

    chunks: list[str] = []
    current = ""

    for line in text.splitlines(keepends=True):
        if _utf16_len(line) > chunk_size:
            if current:
                chunks.append(current)
                current = ""

            remaining = line
            while remaining:
                head, remaining = _slice_by_utf16_limit(remaining, chunk_size)
                chunks.append(head)
            continue

        candidate = current + line
        if current and _utf16_len(candidate) > chunk_size:
            chunks.append(current)
            current = line
        else:
            current = candidate

    if current:
        chunks.append(current)

    safe_messages: list[TextMessage] = []
    for chunk in chunks:
        remaining = chunk
        while remaining:
            head, remaining = _slice_by_utf16_limit(remaining, LINE_TEXT_HARD_LIMIT)
            safe_messages.append(TextMessage(text=head))

    return safe_messages
