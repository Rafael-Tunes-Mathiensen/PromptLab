from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

from chatbot.formatting import render_chat_message

register = template.Library()


@register.filter(name="render_chat_message")
def render_chat_message_filter(value: str) -> str:
    return mark_safe(render_chat_message(value))
