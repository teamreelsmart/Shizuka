import asyncio
from types import SimpleNamespace

from bot.services.storage_service import StorageService


class App:
    async def get_messages(self, channel_id, message_ids):
        assert channel_id == -100123
        assert message_ids == [10, 11]
        return [
            SimpleNamespace(id=10, photo=SimpleNamespace(file_id='photo-id'), video=None, caption='Cover'),
            SimpleNamespace(id=11, photo=None, video=SimpleNamespace(file_id='video-id'), caption=None),
        ]


async def verify():
    records = await StorageService(-100123).batch(App(), 10, 11)
    assert records == [
        {'storage_message_id': 10, 'file_id': 'photo-id', 'media_type': 'photo', 'caption': 'Cover'},
        {'storage_message_id': 11, 'file_id': 'video-id', 'media_type': 'video', 'caption': ''},
    ]


asyncio.run(verify())
