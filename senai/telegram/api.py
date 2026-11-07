"""Small Telegram Bot API client; request URLs and tokens never enter errors."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TelegramError(RuntimeError):
    def __init__(self, message, *, status=None, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class BotAPI:
    def __init__(self, token, *, opener=None):
        self._token = token
        self._opener = opener or urlopen

    def redact(self, value):
        return str(value).replace(self._token, '[redacted]')

    def call(self, method, payload=None, *, timeout=30):
        request = Request(
            f'https://api.telegram.org/bot{self._token}/{method}',
            data=json.dumps(payload or {}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST',
        )
        status = None
        try:
            try:
                with self._opener(request, timeout=timeout) as response:
                    content = response.read()
            except HTTPError as error:
                status = error.code
                content = error.read()
            data = json.loads(content)
        except (URLError, OSError, ValueError):
            raise TelegramError(f'Telegram {method} request failed; check connectivity or credentials.', status=status) from None
        if not isinstance(data, dict) or data.get('ok') is not True:
            code = data.get('error_code', status) if isinstance(data, dict) else status
            parameters = data.get('parameters', {}) if isinstance(data, dict) else {}
            delay = parameters.get('retry_after') if isinstance(parameters, dict) else None
            delay = delay if type(delay) is int and delay > 0 else None
            raise TelegramError(f'Telegram {method} failed (status {code or "unknown"}).', status=code, retry_after=delay)
        return data.get('result')

    def get_me(self):
        return self.call('getMe')

    def get_webhook_info(self):
        return self.call('getWebhookInfo')

    def get_updates(self, offset=None, *, timeout=10):
        payload = {'timeout': timeout, 'limit': 100, 'allowed_updates': ['message']}
        if offset is not None:
            payload['offset'] = offset
        result = self.call('getUpdates', payload, timeout=timeout + 15)
        if not isinstance(result, list):
            raise TelegramError('Telegram getUpdates returned an invalid update list.')
        return result

    def send_message(self, chat_id, text):
        return self.call('sendMessage', {
            'chat_id': chat_id, 'text': text,
            'link_preview_options': {'is_disabled': True},
        })
