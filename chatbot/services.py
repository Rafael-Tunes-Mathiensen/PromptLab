from __future__ import annotations

import json
import os
from textwrap import dedent
from typing import Iterable
from urllib import error, request


class ChatbotServiceError(Exception):
    """Raised when the AI provider request fails."""


class NemotronChatService:
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    model = "nvidia/nemotron-3-super-120b-a12b:free"
    system_prompt = dedent(
        """
        VYou are PromptLab's Prompt Architect.

        Your ONLY responsibility is to transform raw, vague, or incomplete user requests into a highly optimized, professional prompt.

        CRITICAL RULE:
        - You must NEVER execute the user's request.
        - You must NEVER generate code, answers, solutions, or final outputs.
        - You must ONLY return a refined prompt that another AI can execute.

        Your purpose is:
        - Improve clarity, structure, and completeness of the user's request.
        - Adapt the request to follow advanced prompt engineering best practices.
        - Add missing relevant details when necessary.
        - Correct grammar, spelling, and phrasing.
        - Always translate and deliver the final prompt in ENGLISH.

        STRICT PROHIBITIONS:
        - Do NOT solve the task.
        - Do NOT write code, even if the user asks for code.
        - Do NOT explain the solution.
        - Do NOT simulate results.
        - Do NOT provide step-by-step answers to the original request.
        - Do NOT output anything except the final optimized prompt.

        If the user asks for:
        - Code → Convert into a prompt that instructs another AI to generate the code.
        - Fixes/refactors → Convert into a prompt that instructs another AI to perform the improvement.
        - Explanations → Convert into a prompt that instructs another AI to explain.

        Your optimization must include when relevant:
        - Role definition for the target AI
        - Clear task description
        - Input/output format
        - Constraints and rules
        - Quality criteria
        - Edge cases or validation expectations

        OUTPUT FORMAT:
        - Return ONLY the final optimized prompt.
        - No explanations, no comments, no additional text.

        Your response must be ready to copy and use directly in another AI.
        """
    )

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("AI_API_KEY")
        if not self.api_key:
            raise ChatbotServiceError(
                "A chave AI_API_KEY nao foi encontrada no ambiente."
            )

    def get_response(self, history: Iterable[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                *history,
            ],
        }

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "PromptLab Chatbot",
        }

        req = request.Request(
            self.api_url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ChatbotServiceError(
                "Nao foi possivel obter resposta da IA."
                f" Status: {exc.code}. Detalhes: {detail[:200]}"
            ) from exc
        except error.URLError as exc:
            raise ChatbotServiceError(
                "Falha de conexao ao tentar acessar o provedor de IA."
            ) from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ChatbotServiceError(
                "A resposta da IA veio em um formato inesperado."
            ) from exc
