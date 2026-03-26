from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .chat_sessions import (
    build_chat_summaries,
    create_chat,
    delete_chat,
    get_chat_by_id,
    get_chat_state,
    set_active_chat,
    store_chat_exchange,
)
from .forms import ChatMessageForm
from .formatting import render_chat_message
from .services import ChatbotServiceError, NemotronChatService

MAX_HISTORY_ITEMS = 12
AUTHOR_NAME = "Rafael Tunes Mathiensen"
AUTHOR_GITHUB_URL = "https://github.com/Rafael-Tunes-Mathiensen"


def landing_view(request):
    state = get_chat_state(request)
    active_chat = get_chat_by_id(state, state["active_chat_id"])

    context = {
        "author_name": AUTHOR_NAME,
        "github_url": AUTHOR_GITHUB_URL,
        "model_name": NemotronChatService.model,
        "chat_count": len(state["chats"]),
        "active_chat_url": reverse(
            "chatbot:chat_detail",
            kwargs={"chat_id": active_chat["id"]},
        ),
        "page_name": "landing",
    }
    return render(request, "landing.html", context)


def chat_home_view(request):
    state = get_chat_state(request)
    return redirect("chatbot:chat_detail", chat_id=state["active_chat_id"])


def create_chat_view(request):
    if request.method != "POST":
        return redirect("chatbot:chat_home")

    chat = create_chat(request)
    return redirect("chatbot:chat_detail", chat_id=chat["id"])


def delete_chat_view(request, chat_id: str):
    if request.method != "POST":
        return redirect("chatbot:chat_detail", chat_id=chat_id)

    next_chat_id = delete_chat(request, chat_id)
    return redirect("chatbot:chat_detail", chat_id=next_chat_id)


def chatbot_view(request, chat_id: str):
    state = get_chat_state(request)
    active_chat = set_active_chat(request, chat_id)
    if active_chat is None:
        return redirect("chatbot:chat_home")

    if request.method == "POST":
        form = ChatMessageForm(request.POST)
        if form.is_valid():
            try:
                _process_message(request, chat_id, form.cleaned_data["message"])
            except ChatbotServiceError as exc:
                messages.error(request, str(exc))

            return redirect("chatbot:chat_detail", chat_id=chat_id)
    else:
        form = ChatMessageForm()

    context = {
        "author_name": AUTHOR_NAME,
        "github_url": AUTHOR_GITHUB_URL,
        "page_name": "chat",
        "form": form,
        "chat_history": active_chat["messages"],
        "active_chat": active_chat,
        "chat_list": build_chat_summaries(state),
        "model_name": NemotronChatService.model,
    }
    return render(request, "chatbot.html", context)


def chatbot_message_api_view(request, chat_id: str):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Metodo nao permitido."}, status=405)

    active_chat = set_active_chat(request, chat_id)
    if active_chat is None:
        return JsonResponse({"ok": False, "error": "Chat nao encontrado."}, status=404)

    form = ChatMessageForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"ok": False, "errors": form.errors.get_json_data()},
            status=400,
        )

    try:
        user_message, assistant_message = _process_message(
            request,
            chat_id,
            form.cleaned_data["message"],
        )
    except ChatbotServiceError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)

    refreshed_state = get_chat_state(request)
    refreshed_chat = get_chat_by_id(refreshed_state, chat_id)

    return JsonResponse(
        {
            "ok": True,
            "model_name": NemotronChatService.model,
            "chat": {
                "id": chat_id,
                "title": refreshed_chat["title"],
                "message_count": len(refreshed_chat["messages"]),
            },
            "user": {
                "role": "user",
                "content": user_message,
                "html": render_chat_message(user_message),
            },
            "assistant": {
                "role": "assistant",
                "content": assistant_message,
                "html": render_chat_message(assistant_message),
            },
        }
    )


def _process_message(request, chat_id: str, raw_message: str) -> tuple[str, str]:
    state = get_chat_state(request)
    chat = get_chat_by_id(state, chat_id)
    if chat is None:
        raise ChatbotServiceError("Chat nao encontrado.")

    user_message = raw_message.strip()
    history = [*chat["messages"], {"role": "user", "content": user_message}]

    service = NemotronChatService()
    assistant_message = service.get_response(history)

    stored_chat = store_chat_exchange(
        request,
        chat_id,
        user_message,
        assistant_message,
        MAX_HISTORY_ITEMS,
    )
    if stored_chat is None:
        raise ChatbotServiceError("Nao foi possivel atualizar o chat.")

    return user_message, assistant_message
