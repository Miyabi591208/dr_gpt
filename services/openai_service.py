from openai import OpenAI


class OpenAIService:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _run(self, instructions: str, user_input: str, max_output_tokens: int = 1800) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=user_input,
            max_output_tokens=max_output_tokens,
        )
        text = (response.output_text or "").strip()
        return text or "申し訳ありません。応答を生成できませんでした。"

    def chat(self, user_text: str) -> str:
        instructions = (
            "あなたはLINE上で応答する日本語アシスタントです。"
            "丁寧で簡潔に答えてください。"
            "必要な場合は箇条書きや見出しで整理してください。"
        )
        return self._run(instructions, user_text)

    def solve_calculation(self, domain: str, user_text: str) -> str:
        instructions = (
            "あなたは教育的な計算アシスタントです。"
            "日本語で答えてください。"
            "途中式・考え方・前提をできるだけ省略せず、順番に説明してください。"
            "数式がある場合は読める形で整形してください。"
            "最後に『要点』を短くまとめてください。"
            f"専門モード: {domain}"
        )
        return self._run(instructions, user_text, max_output_tokens=2200)

    def draft_article(self, domain: str, question: str, answer: str) -> str:
        instructions = (
            "あなたは技術記事の編集者です。"
            "日本語Markdownで、Qiitaや技術ブログに貼りやすい記事を作成してください。"
            "構成は以下の順にしてください。"
            "1. タイトル"
            "2. 背景"
            "3. 問題設定"
            "4. 解説"
            "5. 必要に応じて数式またはコード"
            "6. まとめ"
            "コードブロックはMarkdownで整えてください。"
        )
        prompt = (
            f"分野: {domain}\n\n"
            f"元の質問:\n{question}\n\n"
            f"回答内容:\n{answer}\n\n"
            "上記をもとに、読み手が理解しやすい技術記事をMarkdownで作成してください。"
        )
        return self._run(instructions, prompt, max_output_tokens=2600)