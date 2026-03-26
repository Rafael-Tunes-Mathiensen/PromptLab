from __future__ import annotations

import re
from html import escape

FENCED_CODE_BLOCK_RE = re.compile(
    r"```(?P<language>[^\n`]*)\n(?P<code>.*?)```",
    re.DOTALL,
)
ORDERED_LIST_RE = re.compile(r"^\d+[.)]\s+")
UNORDERED_LIST_RE = re.compile(r"^[-*]\s+")


def render_chat_message(content: str) -> str:
    normalized = (content or "").replace("\r\n", "\n").strip()
    if not normalized:
        return "<p></p>"

    parts: list[str] = []
    cursor = 0

    for match in FENCED_CODE_BLOCK_RE.finditer(normalized):
        text_segment = normalized[cursor : match.start()]
        if text_segment.strip():
            parts.append(_render_text_blocks(text_segment))

        parts.append(
            _render_code_block(
                code=match.group("code").rstrip("\n"),
                language=(match.group("language") or "").strip().split(" ", 1)[0],
            )
        )
        cursor = match.end()

    trailing_segment = normalized[cursor:]
    if trailing_segment.strip():
        parts.append(_render_text_blocks(trailing_segment))

    return "".join(parts) or "<p></p>"


def _render_text_blocks(content: str) -> str:
    blocks = re.split(r"\n{2,}", content.strip())
    rendered_blocks: list[str] = []

    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue

        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        if not lines:
            continue

        if re.fullmatch(r"[-*_]{3,}", stripped):
            rendered_blocks.append('<hr class="message-divider">')
            continue

        if all(line.startswith("> ") for line in lines):
            quote = "<br>".join(_apply_inline_formatting(line[2:].strip()) for line in lines)
            rendered_blocks.append(f'<blockquote class="message-quote">{quote}</blockquote>')
            continue

        if _is_unordered_list(lines):
            items = "".join(
                f"<li>{_apply_inline_formatting(UNORDERED_LIST_RE.sub('', line, count=1))}</li>"
                for line in lines
            )
            rendered_blocks.append(f'<ul class="message-list">{items}</ul>')
            continue

        if _is_ordered_list(lines):
            items = "".join(
                f"<li>{_apply_inline_formatting(ORDERED_LIST_RE.sub('', line, count=1))}</li>"
                for line in lines
            )
            rendered_blocks.append(f'<ol class="message-list message-list-ordered">{items}</ol>')
            continue

        if stripped.startswith("### "):
            rendered_blocks.append(
                f'<h3 class="message-heading">{_apply_inline_formatting(stripped[4:].strip())}</h3>'
            )
            continue

        if stripped.startswith("## "):
            rendered_blocks.append(
                f'<h2 class="message-heading message-heading-large">{_apply_inline_formatting(stripped[3:].strip())}</h2>'
            )
            continue

        if stripped.startswith("# "):
            rendered_blocks.append(
                f'<h1 class="message-heading message-heading-xl">{_apply_inline_formatting(stripped[2:].strip())}</h1>'
            )
            continue

        paragraph = "<br>".join(_apply_inline_formatting(line) for line in lines)
        rendered_blocks.append(f"<p>{paragraph}</p>")

    return "".join(rendered_blocks)


def _render_code_block(code: str, language: str) -> str:
    language_label = escape(language or "txt")
    escaped_code = escape(code)

    return (
        '<div class="code-block">'
        '<div class="code-block-toolbar">'
        f'<span class="code-language">{language_label}</span>'
        '<button type="button" class="code-copy-button" data-action="copy-code">'
        "Copiar bloco"
        "</button>"
        "</div>"
        f"<pre><code>{escaped_code}</code></pre>"
        "</div>"
    )


def _apply_inline_formatting(text: str) -> str:
    if not text:
        return ""

    inline_code_store: list[str] = []

    def stash_inline_code(match: re.Match[str]) -> str:
        token = f"@@INLINE_CODE_{len(inline_code_store)}@@"
        inline_code_store.append(
            f'<code class="inline-code">{escape(match.group(1))}</code>'
        )
        return token

    prepared = re.sub(r"`([^`]+)`", stash_inline_code, text)
    escaped_text = escape(prepared)

    escaped_text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<strong>\1</strong>",
        escaped_text,
    )
    escaped_text = re.sub(
        r"__(.+?)__",
        r"<strong>\1</strong>",
        escaped_text,
    )

    for index, snippet in enumerate(inline_code_store):
        escaped_text = escaped_text.replace(f"@@INLINE_CODE_{index}@@", snippet)

    return escaped_text


def _is_unordered_list(lines: list[str]) -> bool:
    return all(UNORDERED_LIST_RE.match(line) for line in lines)


def _is_ordered_list(lines: list[str]) -> bool:
    return all(ORDERED_LIST_RE.match(line) for line in lines)
