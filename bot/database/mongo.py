from motor.motor_asyncio import AsyncIOMotorClient
from .indexes import create_indexes

class Mongo:
    def __init__(self, uri: str, name: str): self.client, self.db = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=8000), None; self._name=name
    async def connect(self):
        await self.client.admin.command('ping'); self.db=self.client[self._name]; await create_indexes(self.db)
    def close(self): self.client.close()
