from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class ChatbotViewTests(TestCase):
    def test_get_renders_chatbot_page(self):
        response = self.client.get(reverse("chatbot:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chatbot Django com Nemotron")

    @patch("chatbot.views.NemotronChatService.get_response")
    def test_post_stores_conversation_in_session(self, mock_get_response):
        mock_get_response.return_value = "Resposta de teste"

        response = self.client.post(
            reverse("chatbot:home"),
            {"message": "Ola, tudo bem?"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        session_history = self.client.session["chat_history"]
        self.assertEqual(len(session_history), 2)
        self.assertEqual(session_history[0]["role"], "user")
        self.assertEqual(session_history[1]["role"], "assistant")
        self.assertContains(response, "Resposta de teste")
