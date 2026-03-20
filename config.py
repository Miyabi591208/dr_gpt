import os


class Config:
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    QIITA_ACCESS_TOKEN = os.getenv("QIITA_ACCESS_TOKEN", "")

    SQLITE_PATH = os.getenv("SQLITE_PATH", "app.db")

    SHOP_RADIUS_METERS = int(os.getenv("SHOP_RADIUS_METERS", "1200"))
    SHOP_MAX_RESULTS = int(os.getenv("SHOP_MAX_RESULTS", "5"))

    PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
    PUBMED_EMAIL = os.getenv("PUBMED_EMAIL", "")
    PUBMED_TOOL_NAME = os.getenv("PUBMED_TOOL_NAME", "dr_gpt")
    PUBMED_MAX_RESULTS = int(os.getenv("PUBMED_MAX_RESULTS", "5"))

    @classmethod
    def validate(cls) -> None:
        required = {
            "LINE_CHANNEL_ACCESS_TOKEN": cls.LINE_CHANNEL_ACCESS_TOKEN,
            "LINE_CHANNEL_SECRET": cls.LINE_CHANNEL_SECRET,
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
        }

        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(
                "必須環境変数が未設定です: " + ", ".join(missing)
            )
