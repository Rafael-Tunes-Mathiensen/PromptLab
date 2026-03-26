from django.urls import path

from .views import (
    chatbot_message_api_view,
    chatbot_view,
    chat_home_view,
    create_chat_view,
    delete_chat_view,
    landing_view,
)

app_name = "chatbot"

urlpatterns = [
    path("", landing_view, name="landing"),
    path("chat/", chat_home_view, name="chat_home"),
    path("chat/new/", create_chat_view, name="chat_create"),
    path("chat/<str:chat_id>/", chatbot_view, name="chat_detail"),
    path("chat/<str:chat_id>/delete/", delete_chat_view, name="chat_delete"),
    path("api/chat/<str:chat_id>/message/", chatbot_message_api_view, name="message_api"),
]
