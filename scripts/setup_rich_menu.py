import os

from dotenv import load_dotenv
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    RichMenuArea,
    RichMenuBounds,
    RichMenuRequest,
    PostbackAction,
)

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
if not CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN が未設定です。")


def main():
    configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

    rich_menu = RichMenuRequest(
        size={"width": 2500, "height": 843},
        selected=True,
        name="Main menu",
        chat_bar_text="メニュー",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=625, height=843),
                action=PostbackAction(label="雑談", data="mode=chat", display_text="雑談"),
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=625, y=0, width=625, height=843),
                action=PostbackAction(label="おすすめの店", data="mode=shop", display_text="おすすめの店"),
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=625, height=843),
                action=PostbackAction(label="数理計算", data="mode=calc", display_text="数理計算"),
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1875, y=0, width=625, height=843),
                action=PostbackAction(label="記事化", data="mode=article", display_text="記事化"),
            ),
        ],
    )

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        res = api.create_rich_menu(rich_menu)
        print("rich_menu_id =", res.rich_menu_id)
        print("この後、別途リッチメニュー画像をアップロードし、デフォルト設定してください。")


if __name__ == "__main__":
    main()