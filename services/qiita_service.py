import requests


class QiitaService:
    def __init__(self, access_token: str | None) -> None:
        self.access_token = access_token

    def is_enabled(self) -> bool:
        return bool(self.access_token)

    def create_item(self, title: str, body_markdown: str, tags: list[str], private: bool = False) -> dict:
        if not self.access_token:
            raise RuntimeError("QIITA_ACCESS_TOKEN が未設定です。")

        url = "https://qiita.com/api/v2/items"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "title": title,
            "body": body_markdown,
            "private": private,
            "tags": [{"name": t, "versions": []} for t in tags if t],
        }

        response = requests.post(url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()