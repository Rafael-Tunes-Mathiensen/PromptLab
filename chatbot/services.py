from __future__ import annotations

import json
import os
from typing import Iterable
from urllib import error, request


class ChatbotServiceError(Exception):
    """Raised when the AI provider request fails."""


class NemotronChatService:
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    model = "nvidia/nemotron-3-super-120b-a12b:free"
    system_prompt = (
        "Voce e um assistente util, claro e educado. "
        "Responda em portugues do Brasil com objetividade."
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
