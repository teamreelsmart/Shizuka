import sys
import types

sys.modules.setdefault('aiohttp', types.SimpleNamespace())
from bot.services.shortener_service import ShortenerService

assert ShortenerService._url_from_response({'status': 'success', 'shortened url': 'https://short.example/abc'}, '') == 'https://short.example/abc'
assert ShortenerService._url_from_response(None, 'https://short.example/text-link\n') == 'https://short.example/text-link'
assert ShortenerService._url_from_response({'url': 'not-a-url'}, 'invalid') is None
assert ShortenerService._url_from_response({'status': 'success', 'data': {'shortenedUrl': 'https://short.example/nested'}}, '') == 'https://short.example/nested'
assert ShortenerService._url_from_response({'result': [{'link': 'https://short.example/list'}]}, '') == 'https://short.example/list'
