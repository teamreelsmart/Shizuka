import asyncio
from types import SimpleNamespace

from bot.services.storage_service import StorageService


class App:
    async def get_messages(self, channel_id, message_ids):
        assert channel_id == -100123
        assert message_ids == [10, 11, 12, 13]
        return [
            SimpleNamespace(id=10, photo=SimpleNamespace(file_id='photo-id'), video=None, caption='Cover'),
            SimpleNamespace(id=11, photo=None, video=SimpleNamespace(file_id='video-id'), caption=None),
            SimpleNamespace(id=12, photo=None, video=None, caption=None, voice=SimpleNamespace(file_id='voice-id')),
            SimpleNamespace(id=13, photo=None, video=None, caption=None, animation=SimpleNamespace(file_id='gif-id')),
        ]


async def verify():
    records = await StorageService(-100123).batch(App(), 10, 13)
    assert records == [
        {'storage_message_id': 10, 'file_id': 'photo-id', 'media_type': 'photo', 'caption': 'Cover'},
        {'storage_message_id': 11, 'file_id': 'video-id', 'media_type': 'video', 'caption': ''},
        {'storage_message_id': 12, 'file_id': None, 'media_type': 'message', 'caption': ''},
        {'storage_message_id': 13, 'file_id': None, 'media_type': 'message', 'caption': ''},
    ]


asyncio.run(verify())
