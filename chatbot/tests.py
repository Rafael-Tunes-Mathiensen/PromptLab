from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from chatbot.chat_sessions import SESSION_CHATS_KEY
from chatbot.formatting import render_chat_message


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
    def test_landing_page_renders_author_and_primary_actions(self):
        response = self.client.get(reverse("chatbot:landing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rafael Tunes Mathiensen")
        self.assertContains(response, "Abrir workspace")

    def test_chat_home_redirects_to_active_chat(self):
        response = self.client.get(reverse("chatbot:chat_home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/chat/", response.headers["Location"])

    def test_create_and_delete_chat_updates_session_store(self):
        self.client.get(reverse("chatbot:chat_home"))
        initial_state = self.client.session[SESSION_CHATS_KEY]
        initial_chat_id = initial_state["active_chat_id"]

        create_response = self.client.post(reverse("chatbot:chat_create"))
        self.assertEqual(create_response.status_code, 302)

        updated_state = self.client.session[SESSION_CHATS_KEY]
        self.assertEqual(len(updated_state["chats"]), 2)
        self.assertNotEqual(updated_state["active_chat_id"], initial_chat_id)

        delete_response = self.client.post(
            reverse("chatbot:chat_delete", args=[updated_state["active_chat_id"]])
        )
        self.assertEqual(delete_response.status_code, 302)

        final_state = self.client.session[SESSION_CHATS_KEY]
        self.assertEqual(len(final_state["chats"]), 1)
        self.assertEqual(final_state["active_chat_id"], initial_chat_id)

    @patch("chatbot.views.NemotronChatService")
    def test_message_api_returns_rendered_payload_and_updates_active_chat(self, service_cls):
        service_cls.model = "mock-model"
        service_cls.return_value.get_response.return_value = (
            "### Prompt otimizado\n\n```python\nprint('oi')\n```"
        )

        chat_home_response = self.client.get(reverse("chatbot:chat_home"))
        active_chat_url = chat_home_response.headers["Location"]
        chat_id = active_chat_url.rstrip("/").split("/")[-1]

        response = self.client.post(
            reverse("chatbot:message_api", args=[chat_id]),
            {"message": "Crie um prompt para uma API Django"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["model_name"], "mock-model")
        self.assertIn('class="code-block"', payload["assistant"]["html"])
        self.assertEqual(payload["chat"]["id"], chat_id)

        state = self.client.session[SESSION_CHATS_KEY]
        self.assertEqual(state["active_chat_id"], chat_id)
        self.assertEqual(len(state["chats"][0]["messages"]), 2)

    @patch("chatbot.views.NemotronChatService")
    def test_sync_post_fallback_redirects_to_same_chat(self, service_cls):
        service_cls.return_value.get_response.return_value = (
            "### Diagnostico do prompt original\n\n- Pedido muito aberto"
        )

        chat_home_response = self.client.get(reverse("chatbot:chat_home"))
        active_chat_url = chat_home_response.headers["Location"]
        chat_id = active_chat_url.rstrip("/").split("/")[-1]

        response = self.client.post(
            reverse("chatbot:chat_detail", args=[chat_id]),
            {"message": "Transforme este pedido em prompt para uma landing page"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            reverse("chatbot:chat_detail", args=[chat_id]),
        )
