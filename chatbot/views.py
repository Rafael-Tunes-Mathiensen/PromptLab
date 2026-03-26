from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import ChatMessageForm
from .formatting import render_chat_message
from .services import ChatbotServiceError, NemotronChatService

SESSION_KEY = "chat_history"
MAX_HISTORY_ITEMS = 12


def chatbot_view(request):
    history = request.session.get(SESSION_KEY, [])

    if request.method == "POST":
        form = ChatMessageForm(request.POST)
        if form.is_valid():
            try:
                _process_message(request, form.cleaned_data["message"])
            except ChatbotServiceError as exc:
                messages.error(request, str(exc))

            return redirect("chatbot:home")
    else:
        form = ChatMessageForm()

    context = {
        "form": form,
        "chat_history": history,
        "model_name": NemotronChatService.model,
    }
    return render(request, "chatbot.html", context)


def chatbot_message_api_view(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Metodo nao permitido."}, status=405)

    form = ChatMessageForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"ok": False, "errors": form.errors.get_json_data()},
            status=400,
        )

    try:
        user_message, assistant_message = _process_message(
            request,
            form.cleaned_data["message"],
        )
    except ChatbotServiceError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)

    return JsonResponse(
        {
            "ok": True,
            "model_name": NemotronChatService.model,
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


def _process_message(request, raw_message: str) -> tuple[str, str]:
    history = request.session.get(SESSION_KEY, [])
    user_message = raw_message.strip()
    history.append({"role": "user", "content": user_message})

    service = NemotronChatService()
    assistant_message = service.get_response(history)

    history.append({"role": "assistant", "content": assistant_message})
    request.session[SESSION_KEY] = history[-MAX_HISTORY_ITEMS:]
    request.session.modified = True

    return user_message, assistant_message
