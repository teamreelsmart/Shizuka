import asyncio
import sys
import types
from types import SimpleNamespace

sys.modules.setdefault('pyrogram.errors', types.SimpleNamespace(FloodWait=Exception))

from bot.services.media_service import MediaService


class Cursor:
    def sort(self, *_):
        return self

    async def to_list(self, _):
        return [
            {'storage_message_id': 10, 'media_type': 'photo'},
            {'storage_message_id': 11, 'media_type': 'message'},
            {'storage_message_id': 12, 'media_type': 'message'},
        ]


class Database:
    collection_media = SimpleNamespace(find=lambda _: Cursor())
    cleanup_messages = SimpleNamespace(insert_many=lambda _: None)


class App:
    def __init__(self):
        self.copied = []

    async def copy_message(self, chat_id, from_chat_id, message_id, protect_content=False):
        self.copied.append((chat_id, from_chat_id, message_id, protect_content))
        return SimpleNamespace(id=message_id + 100)


async def verify():
    app = App()
    delivered = await MediaService(Database(), -100123).deliver(
        app, 55, {'_id': 'collection'}, 10, False, True
    )
    assert delivered == 3
    assert app.copied == [
        (55, -100123, 10, True),
        (55, -100123, 11, True),
        (55, -100123, 12, True),
    ]


asyncio.run(verify())
