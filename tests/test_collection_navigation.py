import asyncio
from types import SimpleNamespace

from bot.services.collection_service import CollectionService


class Cursor:
    def __init__(self, values): self.values = values
    def sort(self, ordering):
        assert ordering == [('created_at', 1), ('_id', 1)]
        return self
    async def to_list(self, _): return self.values


class Collections:
    def __init__(self):
        self.values = [{'_id': 'oldest'}, {'_id': 'middle'}, {'_id': 'newest'}]
    def find(self, query):
        assert query == {'active': True}
        return Cursor(self.values)


async def verify():
    service = CollectionService(SimpleNamespace(collections=Collections()), None)
    assert (await service.adjacent({'_id': 'newest'}, 'prev'))['_id'] == 'middle'
    assert (await service.adjacent({'_id': 'middle'}, 'next'))['_id'] == 'newest'
    assert (await service.adjacent({'_id': 'newest'}, 'next'))['_id'] == 'oldest'
    assert (await service.adjacent({'_id': 'oldest'}, 'prev'))['_id'] == 'newest'
    assert await service.adjacent({'_id': 'missing'}, 'next') is None


asyncio.run(verify())
