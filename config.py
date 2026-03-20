import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
    QIITA_ACCESS_TOKEN = os.getenv("QIITA_ACCESS_TOKEN")

    APP_BASE_URL = os.getenv("APP_BASE_URL", "").rstrip("/")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "bot_state.db")

    SHOP_RADIUS_METERS = int(os.getenv("SHOP_RADIUS_METERS", "1200"))
    SHOP_MAX_RESULTS = int(os.getenv("SHOP_MAX_RESULTS", "5"))

    @classmethod
    def validate(cls) -> None:
        missing = []
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not cls.LINE_CHANNEL_ACCESS_TOKEN:
            missing.append("LINE_CHANNEL_ACCESS_TOKEN")
        if not cls.LINE_CHANNEL_SECRET:
            missing.append("LINE_CHANNEL_SECRET")

        if missing:
            raise RuntimeError(f"必要な環境変数が未設定です: {', '.join(missing)}")