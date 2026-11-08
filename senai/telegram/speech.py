"""Optional OpenAI speech generation; no network or credential lookup on import."""

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

__all__ = ['OpenAISpeech', 'SpeechError', 'speech_from_environment']

MAX_SPEECH_TEXT = 4000
MAX_AUDIO_BYTES = 10 * 1024 * 1024


class SpeechError(RuntimeError):
    pass


def is_mp3(content):
    return isinstance(content, bytes) and (content.startswith(b'ID3') or
            (len(content) > 1 and content[0] == 0xff and content[1] & 0xe0 == 0xe0))


class OpenAISpeech:
    def __init__(self, key, *, model='gpt-4o-mini-tts', voice='coral', opener=None):
        if not isinstance(key, str) or not key.strip() or '\n' in key or '\r' in key:
            raise SpeechError('Configure a valid OpenAI speech API key locally.')
        self._key, self.model, self.voice = key.strip(), model, voice
        self._opener = opener or urlopen

    def __call__(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_SPEECH_TEXT:
            raise SpeechError('Voice replies support at most 4000 characters; request a shorter answer.')
        request = Request('https://api.openai.com/v1/audio/speech', method='POST',
                          data=json.dumps({'model': self.model, 'voice': self.voice,
                                           'input': text, 'response_format': 'mp3'}).encode('utf-8'),
                          headers={'Authorization': 'Bearer ' + self._key, 'Content-Type': 'application/json'})
        try:
            with self._opener(request, timeout=90) as response:
                content = response.read(MAX_AUDIO_BYTES + 1)
        except (URLError, OSError, ValueError):
            raise SpeechError('Speech generation is unavailable; check local configuration and connectivity.') from None
        if len(content) > MAX_AUDIO_BYTES or not is_mp3(content):
            raise SpeechError('Speech generation did not return a supported audio reply.')
        return content


def speech_from_environment(environ=None):
    values = os.environ if environ is None else environ
    key = values.get('OPENAI_API_KEY', '').strip()
    if not key:
        return None
    return OpenAISpeech(key, model=values.get('SENAI_TTS_MODEL', 'gpt-4o-mini-tts'),
                        voice=values.get('SENAI_TTS_VOICE', 'coral'))
