from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import ChatMessageForm
from .services import ChatbotServiceError, NemotronChatService

SESSION_KEY = "chat_history"
MAX_HISTORY_ITEMS = 12


def chatbot_view(request):
    history = request.session.get(SESSION_KEY, [])

    if request.method == "POST":
        form = ChatMessageForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data["message"].strip()
            history.append({"role": "user", "content": user_message})

            try:
                service = NemotronChatService()
                assistant_message = service.get_response(history)
            except ChatbotServiceError as exc:
                messages.error(request, str(exc))
            else:
                history.append({"role": "assistant", "content": assistant_message})
                request.session[SESSION_KEY] = history[-MAX_HISTORY_ITEMS:]
                request.session.modified = True

            return redirect("chatbot:home")
    else:
        form = ChatMessageForm()

    context = {
        "form": form,
        "chat_history": history,
        "model_name": NemotronChatService.model,
    }
    return render(request, "chatbot.html", context)
