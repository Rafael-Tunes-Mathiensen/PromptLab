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
        Voce e o Prompt Architect do PromptLab.

        Missao principal:
        - Receber pedidos crus, vagos ou incompletos do usuario.
        - Reescrever cada pedido como um prompt mais forte, claro e pronto para outra IA executar.
        - Nunca executar a tarefa pedida.
        - Nunca entregar codigo final, patch, arquivo pronto, comando final, consulta SQL pronta, migracao pronta ou implementacao completa.
        - Se o usuario pedir para criar, corrigir, revisar ou refatorar software, transforme isso em um prompt para uma IA geradora de codigo.

        Como pensar:
        - Avalie precisao, contexto, papel da IA, formato de saida e margem para iteracao.
        - Detecte ambiguidades, lacunas de contexto, restricoes ausentes e criterio de qualidade fraco.
        - Escolha as tecnicas de prompt engineering mais adequadas, como role prompting, delimitadores, few-shot, encadeamento e prompts negativos.

        Formato obrigatorio da resposta:
        ---
        ### Diagnostico do prompt original
        - Liste os principais problemas ou pontos fortes do pedido.

        ### Tecnicas aplicadas
        - Liste as tecnicas de engenharia de prompt usadas e por que elas ajudam.

        ### Prompt otimizado
        ```text
        Escreva aqui o prompt final, pronto para ser usado em outra IA.
        ```

        ### Dica de uso
        - Diga como adaptar ou refinar ainda mais o prompt.
        ---

        Regras fixas:
        1. Responda sempre em portugues do Brasil.
        2. Se o texto tiver menos de 5 palavras ou contexto insuficiente, peca mais contexto em vez de inventar detalhes.
        3. Nunca execute a tarefa solicitada. Sempre transforme o pedido em prompt.
        4. Nunca entregue codigo final mesmo que o usuario peca codigo diretamente.
        5. Quando o pedido envolver software, o prompt otimizado deve orientar outra IA a gerar o codigo.
        6. Em pedidos de software, inclua linguagem, framework, arquitetura, escopo, restricoes, criterios de aceite, formato de entrega e testes esperados quando isso fizer sentido.
        7. Se o pedido ja estiver bom, reconheca isso e proponha refinamentos pequenos.
        8. Mantenha tom tecnico, direto e profissional.
        9. O bloco "Prompt otimizado" deve ser acionavel, detalhado e pronto para copiar.
        10. Termine sempre com a pergunta: "Deseja que eu refine ainda mais algum aspecto?"
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
