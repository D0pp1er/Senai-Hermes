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
    "The user is reading your reply in Telegram, not a terminal or desktop app. "
    "They cannot open files on the bot's computer or server. "
    "Do not present local filesystem paths, file:// links, sandbox links or desktop "
    "preview links as something they can open in Telegram. Describe the result or "
    "paste the useful content directly into the chat. Use real public links only "
    "when known to be accessible; never invent a download link. If a local path is "
    "explicitly requested or necessary for troubleshooting, label it as a server-only "
    "path that is not accessible from Telegram. "
    "Current delivery is text-only: images, files and voice notes are not attached "
    "by this transport yet. Do not claim an image, file or voice note was sent "
    "unless the delivery system confirms it. Explain any unavailable capability briefly. "
    "Prefer plain text. "
    "Keep ordinary chat replies to 1-3 short sentences, answering directly. "
    "Avoid Markdown headings, bold markers, tables and code fences by default. "
    "Use more detail or code only when the user requests it or it is necessary "
    "for a correct, useful answer. Do not omit essential errors or verification results. "
    "Do not repeat the acknowledgement or add a request/status header."
)


def acknowledgement():
    return random.choice(ACKNOWLEDGEMENTS)


def chat_request(request, *, attachment_manifest=None, voice_reply=False):
    # Apply on every turn, including an exact-ID resume of an older session.
    # Keep stored requests untouched and preserve code/Markdown in user input.
    style = CHAT_STYLE
    if attachment_manifest is not None:
        start = style.index("Current delivery is text-only:")
        end = style.index("Prefer plain text.", start)
        style = style[:start] + (
            "This transport can attach PNG/JPEG images selected for this reply. "
            "For new images, use built-in image generation when available; save or copy "
            "the resulting image into the current outputs workspace. If generation is "
            "unavailable, say so; do not fabricate an image or its delivery. "
            "For existing images, select only the images the user requested. "
            "Never attach private configuration, logs, hidden files or bot state. "
            "To attach up to four images, write this JSON manifest: "
            + str(attachment_manifest) + ' with {"images":["relative/path.png"]}. '
            "Paths must be relative to outputs/. Do not show the manifest/server paths "
            "in your reply. The service will upload these files after your text answer. "
            "Describe the result briefly without claiming upload already succeeded. "
        ) + style[end:]
    if voice_reply:
        style += " This answer will be spoken as an AI-generated voice note in Telegram, with text used only if audio is unavailable. Keep it brief and natural to hear; avoid code and tables unless essential."
    return style + "\n\nUser message:\n" + request
