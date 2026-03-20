from openai import OpenAI


class OpenAIService:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

        # 👇人格設定（ここが最重要）
        self.system_prompt = (
            "あなたは阿笠博士のような人格を持つAIです。"
            "ユーザーに対して親しみやすく、知的で、少しお茶目な博士として振る舞ってください。"
            "語尾には「〜じゃ」「〜なのじゃ」「〜じゃよ」などを自然に使います。"
            "ただし説明は論理的かつ分かりやすく行い、専門的内容も丁寧に解説してください。"
            "決して乱暴にならず、優しく導くように話します。"
        )

    def chat(self, user_text: str, history=None) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]

        if history:
            for h in history:
                messages.append({
                    "role": h["role"],
                    "content": h["content"]
                })

        messages.append({"role": "user", "content": user_text})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )

        return response.choices[0].message.content

    def solve_calculation(self, domain: str, user_text: str) -> str:
        prompt = (
            f"分野: {domain}\n"
            f"質問: {user_text}\n\n"
            "丁寧に論理的に解説してください。"
        )

        return self.chat(prompt)

    def draft_article(self, domain: str, question: str, answer: str) -> str:
        prompt = (
            f"以下の内容を元にQiita記事を書いてください。\n\n"
            f"分野: {domain}\n"
            f"質問: {question}\n"
            f"回答: {answer}\n\n"
            "見出し付きで読みやすく整理してください。"
        )

        return self.chat(prompt)
