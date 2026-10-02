import asyncio
import sys
import types
sys.modules.setdefault('pymongo', types.SimpleNamespace(ReturnDocument=types.SimpleNamespace(AFTER='after')))
from types import SimpleNamespace
from bot.services.user_service import UserService

class Users:
    def __init__(self): self.update = None
    async def update_one(self, query, update, upsert=False): self.update = update
    async def find_one(self, query): return {'telegram_id': query['telegram_id']}

async def verify():
    users = Users()
    service = UserService(SimpleNamespace(users=users))
    await service.ensure(SimpleNamespace(id=42, username='name', first_name='First', last_name=None))
    assert not (set(users.update['$set']) & set(users.update['$setOnInsert']))
    assert users.update['$set']['username'] == 'name'

asyncio.run(verify())
