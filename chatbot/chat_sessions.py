from __future__ import annotations

from typing import Any
from uuid import uuid4

from django.utils import timezone

SESSION_CHATS_KEY = "chat_sessions"
DEFAULT_CHAT_TITLE = "Novo chat"


def get_chat_state(request) -> dict[str, Any]:
    state = request.session.get(SESSION_CHATS_KEY)
    needs_save = False

    if not isinstance(state, dict):
        state = {"active_chat_id": None, "chats": []}
        needs_save = True

    chats = state.get("chats")
    if not isinstance(chats, list):
        chats = []
        needs_save = True

    normalized_chats = [_normalize_chat(chat) for chat in chats if isinstance(chat, dict)]
    if len(normalized_chats) != len(chats):
        needs_save = True

    state = {
        "active_chat_id": state.get("active_chat_id"),
        "chats": normalized_chats,
    }

    if not state["chats"]:
        chat = _build_chat()
        state["chats"].append(chat)
        state["active_chat_id"] = chat["id"]
        needs_save = True

    if not any(chat["id"] == state["active_chat_id"] for chat in state["chats"]):
        state["active_chat_id"] = state["chats"][0]["id"]
        needs_save = True

    if needs_save:
        save_chat_state(request, state)

    return state


def save_chat_state(request, state: dict[str, Any]) -> None:
    request.session[SESSION_CHATS_KEY] = state
    request.session.modified = True


def create_chat(request, title: str | None = None) -> dict[str, Any]:
    state = get_chat_state(request)
    chat = _build_chat(title=title)
    state["chats"].insert(0, chat)
    state["active_chat_id"] = chat["id"]
    save_chat_state(request, state)
    return chat


def get_chat_by_id(state: dict[str, Any], chat_id: str) -> dict[str, Any] | None:
    for chat in state["chats"]:
        if chat["id"] == chat_id:
            return chat
    return None


def set_active_chat(request, chat_id: str) -> dict[str, Any] | None:
    state = get_chat_state(request)
    chat = get_chat_by_id(state, chat_id)
    if chat is None:
        return None

    if state["active_chat_id"] != chat_id:
        state["active_chat_id"] = chat_id
        save_chat_state(request, state)

    return chat


def delete_chat(request, chat_id: str) -> str:
    state = get_chat_state(request)
    state["chats"] = [chat for chat in state["chats"] if chat["id"] != chat_id]

    if not state["chats"]:
        replacement_chat = _build_chat()
        state["chats"] = [replacement_chat]
        state["active_chat_id"] = replacement_chat["id"]
    elif state["active_chat_id"] == chat_id:
        state["active_chat_id"] = state["chats"][0]["id"]

    save_chat_state(request, state)
    return state["active_chat_id"]


def store_chat_exchange(
    request,
    chat_id: str,
    user_message: str,
    assistant_message: str,
    max_history_items: int,
) -> dict[str, Any] | None:
    state = get_chat_state(request)
    chat = get_chat_by_id(state, chat_id)
    if chat is None:
        return None

    chat["messages"].append({"role": "user", "content": user_message})
    chat["messages"].append({"role": "assistant", "content": assistant_message})
    chat["messages"] = chat["messages"][-max_history_items:]
    chat["updated_at"] = _timestamp()

    if chat["title"] == DEFAULT_CHAT_TITLE:
        chat["title"] = build_chat_title(user_message)

    state["active_chat_id"] = chat_id
    save_chat_state(request, state)
    return chat


def build_chat_title(message: str) -> str:
    compact = " ".join(message.split())
    if not compact:
        return DEFAULT_CHAT_TITLE

    if len(compact) <= 44:
        return compact

    return f"{compact[:41].rstrip()}..."


def build_chat_summaries(state: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for chat in state["chats"]:
        summaries.append(
            {
                "id": chat["id"],
                "title": chat["title"],
                "message_count": len(chat["messages"]),
            }
        )

    return summaries


def _build_chat(title: str | None = None) -> dict[str, Any]:
    return {
        "id": uuid4().hex,
        "title": title or DEFAULT_CHAT_TITLE,
        "messages": [],
        "updated_at": _timestamp(),
    }


def _normalize_chat(chat: dict[str, Any]) -> dict[str, Any]:
    messages = chat.get("messages")
    normalized_messages = messages if isinstance(messages, list) else []

    return {
        "id": str(chat.get("id") or uuid4().hex),
        "title": str(chat.get("title") or DEFAULT_CHAT_TITLE),
        "messages": [
            {
                "role": str(message.get("role", "")),
                "content": str(message.get("content", "")),
            }
            for message in normalized_messages
            if isinstance(message, dict)
        ],
        "updated_at": str(chat.get("updated_at") or _timestamp()),
    }


def _timestamp() -> str:
    return timezone.now().isoformat()
