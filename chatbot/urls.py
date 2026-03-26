from django.urls import path

from .views import chatbot_view

app_name = "chatbot"

urlpatterns = [
    path("", chatbot_view, name="home"),
]
