import asyncio
from bot.utils.time import now
async def cleanup_worker(app,db,settings):
 while True:
  try:
   config=await settings.get()
   if config['cleanup_enabled']:
    async for item in db.cleanup_messages.find({'expiration_time':{'$lte':now()}}).limit(100):
     try: await app.delete_messages(item['user_id'],item['message_id'])
     except Exception: pass
     await db.cleanup_messages.delete_one({'_id':item['_id']})
  except Exception: pass
  await asyncio.sleep(60)
