from django.urls import path

from .views import chatbot_message_api_view, chatbot_view

app_name = "chatbot"

urlpatterns = [
    path("", chatbot_view, name="home"),
    path("api/message/", chatbot_message_api_view, name="message_api"),
]
