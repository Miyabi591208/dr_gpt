from __future__ import annotations

from typing import Sequence

from openai import OpenAI


class OpenAIService:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _create_response(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()

    def chat(
        self,
        user_text: str,
        history: Sequence[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": system_prompt
                or (
                    "あなたは親切で分かりやすい会話アシスタントです。"
                    "過去の会話文脈が与えられている場合は、それを踏まえて自然につながる返答をしてください。"
                    "ただし、事実が不明な点は断定せず、必要に応じて不確実性を明示してください。"
                ),
            }
        ]

        if history:
            for item in history:
                role = item.get("role", "").strip()
                content = item.get("content", "").strip()
                if role in {"user", "assistant", "system"} and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_text})

        return self._create_response(messages, temperature=0.7)

    def solve_calculation(self, domain: str, user_text: str) -> str:
        system_prompt = (
            "あなたは数理計算を支援する専門アシスタントです。"
            "解答は正確性を重視し、途中式や考え方を分かりやすく整理してください。"
            "不明な前提は勝手に補わず、必要に応じて仮定を明示してください。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"分野: {domain}\n"
                    f"質問: {user_text}\n\n"
                    "上記に対して、できるだけ丁寧かつ分かりやすく回答してください。"
                ),
            },
        ]

        return self._create_response(messages, temperature=0.2)

    def draft_article(self, domain: str, question: str, answer: str) -> str:
        system_prompt = (
            "あなたは技術記事の編集者です。"
            "与えられた質問と回答をもとに、Qiita等へ投稿しやすいMarkdown記事を作成してください。"
            "冗長すぎず、見出し構成を明確にし、読み手が理解しやすい形に整えてください。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"分野: {domain}\n"
                    f"元の質問:\n{question}\n\n"
                    f"元の回答:\n{answer}\n\n"
                    "上記をもとに、Markdown形式の読みやすい記事を作成してください。"
                    "先頭にタイトルとなる見出し（# タイトル）を入れてください。"
                ),
            },
        ]

        return self._create_response(messages, temperature=0.5)
