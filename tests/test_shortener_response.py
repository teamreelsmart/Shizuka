import sys
import types
from datetime import datetime, timezone

sys.modules.setdefault('aiohttp', types.SimpleNamespace())
from bot.services.shortener_service import ShortenerService
from bot.utils.time import as_utc

assert ShortenerService._url_from_response({'status': 'success', 'shortened url': 'https://short.example/abc'}, '') == 'https://short.example/abc'
assert ShortenerService._url_from_response(None, 'https://short.example/text-link\n') == 'https://short.example/text-link'
assert ShortenerService._url_from_response({'url': 'not-a-url'}, 'invalid') is None
assert ShortenerService._url_from_response({'status': 'success', 'data': {'shortenedUrl': 'https://short.example/nested'}}, '') == 'https://short.example/nested'
assert ShortenerService._url_from_response({'result': [{'link': 'https://short.example/list'}]}, '') == 'https://short.example/list'
assert ShortenerService._api_endpoint({'api_url': 'https://arolinks.com/member/tools/api#developers-api'}) == 'https://arolinks.com/api'
assert ShortenerService._api_endpoint({'api_url': 'https://arolinks.com/api?api=old-token&url=example.com'}) == 'https://arolinks.com/api'
assert ShortenerService._api_endpoint({'api_url': 'https://short.example/api'}) == 'https://short.example/api'
assert ShortenerService._error_from_response({'status': 'error', 'message': 'Invalid API token'}) == 'Invalid API token'
assert ShortenerService._request_params('private-token', 'https://t.me/example?start=task', 'custom123') == {'api': 'private-token', 'url': 'https://t.me/example?start=task', 'alias': 'custom123'}
assert 'format' not in ShortenerService._request_params('private-token', 'https://t.me/example?start=task')
assert as_utc(datetime(2026, 1, 1)).tzinfo == timezone.utc
assert as_utc(datetime(2026, 1, 1, tzinfo=timezone.utc)).tzinfo == timezone.utc
