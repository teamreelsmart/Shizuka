import asyncio
from datetime import timedelta
from pyrogram.errors import FloodWait
from bot.utils.time import now

class MediaService:
 def __init__(self,db,storage_channel_id):self.db,self.storage_channel_id=db,storage_channel_id
 async def deliver(self,app,user_id,collection,cleanup_minutes,cleanup_enabled,protected_content=False):
  media=await self.db.collection_media.find({'collection_id':collection['_id']}).sort('order',1).to_list(None); sent=[]
  # copy_message preserves every Telegram message type (including GIFs,
  # voice messages, documents, stickers, and plain text).  Media groups
  # cannot represent those types, so copying each stored message is both more
  # reliable and compatible with mixed batches.
  for record in media:
   try: message=await app.copy_message(user_id,self.storage_channel_id,record['storage_message_id'],protect_content=protected_content)
   except FloodWait as e:
    await asyncio.sleep(e.value)
    try: message=await app.copy_message(user_id,self.storage_channel_id,record['storage_message_id'],protect_content=protected_content)
    except Exception: continue
   except Exception: continue
   sent.append(message)
  if cleanup_enabled and sent:
   await self.db.cleanup_messages.insert_many([{'user_id':user_id,'message_id':m.id,'collection_id':collection['_id'],'expiration_time':now()+timedelta(minutes=cleanup_minutes)} for m in sent])
  return len(sent)
