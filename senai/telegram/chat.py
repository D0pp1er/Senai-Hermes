"""Telegram-only acknowledgement choices and model response-style instructions."""

import random

ACKNOWLEDGEMENTS = (
    "Got it, I’m on it.",
    "Let me check that.",
    "Okay, give me a moment.",
    "I’ll take a look.",
    "Working on it.",
)

CHAT_STYLE = (
    "Reply for a Telegram messenger conversation. Prefer plain text. "
    "Keep ordinary chat replies to 1-3 short sentences, answering directly. "
    "Avoid Markdown headings, bold markers, tables and code fences by default. "
    "Use more detail or code only when the user requests it or it is necessary "
    "for a correct, useful answer. Do not omit essential errors or verification results. "
    "Do not repeat the acknowledgement or add a request/status header."
)


def acknowledgement():
    return random.choice(ACKNOWLEDGEMENTS)


def chat_request(request):
    # Apply on every turn, including an exact-ID resume of an older session.
    # Keep stored requests untouched and preserve code/Markdown in user input.
    return CHAT_STYLE + "\n\nUser message:\n" + request
