from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from chatbot.formatting import render_chat_message
from chatbot.views import SESSION_KEY


class ChatFormattingTests(TestCase):
    def test_render_chat_message_supports_headings_lists_and_code_blocks(self):
        html = render_chat_message(
            "### Diagnostico\n\n- Falta contexto\n- Falta formato\n\n```python\nprint('oi')\n```"
        )

        self.assertIn('class="message-heading"', html)
        self.assertIn('class="message-list"', html)
        self.assertIn('class="code-block"', html)
        self.assertIn("Copiar bloco", html)


class ChatbotViewTests(TestCase):
    def test_home_page_renders_main_interface(self):
        response = self.client.get(reverse("chatbot:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PromptLab")
        self.assertContains(response, "data-chat-endpoint")

    @patch("chatbot.views.NemotronChatService")
    def test_message_api_returns_rendered_payload_and_updates_session(self, service_cls):
        service_cls.model = "mock-model"
        service_cls.return_value.get_response.return_value = (
            "### Prompt otimizado\n\n```python\nprint('oi')\n```"
        )

        response = self.client.post(
            reverse("chatbot:message_api"),
            {"message": "Crie um prompt para uma API Django"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["model_name"], "mock-model")
        self.assertIn('class="code-block"', payload["assistant"]["html"])

        history = self.client.session[SESSION_KEY]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    @patch("chatbot.views.NemotronChatService")
    def test_sync_post_fallback_redirects_and_persists_history(self, service_cls):
        service_cls.return_value.get_response.return_value = (
            "### Diagnostico do prompt original\n\n- Pedido muito aberto"
        )

        response = self.client.post(
            reverse("chatbot:home"),
            {"message": "Transforme este pedido em prompt para uma landing page"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("chatbot:home"))
        self.assertEqual(len(self.client.session[SESSION_KEY]), 2)
