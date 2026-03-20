import mimetypes
import os
import requests

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

# Rich Menu画像パス
# 例: assets/richmenu_2500x843.png
RICH_MENU_IMAGE_PATH = os.getenv("RICH_MENU_IMAGE_PATH", "assets/richmenu_2500x843.png")


def create_rich_menu(api: MessagingApi) -> str:
    """
    4分割のRich Menuを作成し、rich_menu_idを返す
    """
    rich_menu = RichMenuRequest(
        size={"width": 2500, "height": 843},
        selected=True,
        name="Dr_GPT Main Menu",
        chat_bar_text="メニュー",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=625, height=843),
                action=PostbackAction(
                    label="雑談",
                    data="mode=chat",
                    display_text="雑談",
                ),
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=625, y=0, width=625, height=843),
                action=PostbackAction(
                    label="おすすめの店",
                    data="mode=shop",
                    display_text="おすすめの店",
                ),
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=625, height=843),
                action=PostbackAction(
                    label="数理計算",
                    data="mode=calc",
                    display_text="数理計算",
                ),
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1875, y=0, width=625, height=843),
                action=PostbackAction(
                    label="記事化",
                    data="mode=article",
                    display_text="記事化",
                ),
            ),
        ],
    )

    response = api.create_rich_menu(rich_menu)
    return response.rich_menu_id


def upload_rich_menu_image(rich_menu_id: str, image_path: str) -> None:
    """
    Rich Menu画像をアップロード
    SDKでも可能ですが、ここでは公式エンドポイントへ直接PUTしています。
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"画像が見つかりません: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type not in {"image/png", "image/jpeg"}:
        raise ValueError("Rich Menu画像は PNG または JPEG にしてください。")

    url = f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content"
    headers = {
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
        "Content-Type": mime_type,
    }

    with open(image_path, "rb") as f:
        response = requests.post(url, headers=headers, data=f, timeout=30)

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"画像アップロード失敗: status={response.status_code}, body={response.text}"
        )


def set_default_rich_menu(api: MessagingApi, rich_menu_id: str) -> None:
    """
    作成したRich Menuをデフォルトに設定
    """
    api.set_default_rich_menu(rich_menu_id)


def main() -> None:
    configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)

        rich_menu_id = create_rich_menu(api)
        print(f"[OK] rich_menu_id = {rich_menu_id}")

        upload_rich_menu_image(rich_menu_id, RICH_MENU_IMAGE_PATH)
        print("[OK] 画像アップロード完了")

        set_default_rich_menu(api, rich_menu_id)
        print("[OK] デフォルトのRich Menuに設定完了")

        print("LINEアプリを開き直すか、トーク画面を再表示して確認してください。")


if __name__ == "__main__":
    main()
