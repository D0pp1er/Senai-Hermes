"""Plain-text splitting below Telegram limits, including supplementary Unicode."""


def split_message(text, limit=3500):
    if not 2 <= limit <= 4096:
        raise ValueError('Message limit must be between 2 and 4096 UTF-16 units.')
    if not text:
        return ['(empty response)']
    parts, current, units = [], [], 0
    for character in text:
        width = 2 if ord(character) > 0xffff else 1
        if units + width > limit:
            parts.append(''.join(current))
            current, units = [], 0
        current.append(character)
        units += width
    if current:
        parts.append(''.join(current))
    return parts
