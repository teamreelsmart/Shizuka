import asyncio
from datetime import timedelta
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from pyrogram.errors import FloodWait
from bot.utils.time import now

class MediaService:
 def __init__(self,db,storage_channel_id):self.db,self.storage_channel_id=db,storage_channel_id
 async def deliver(self,app,user_id,collection,cleanup_minutes,cleanup_enabled,protected_content=False):
  media=await self.db.collection_media.find({'collection_id':collection['_id']}).sort('order',1).to_list(None); sent=[]
  for i in range(0,len(media),10):
   batch=media[i:i+10]
   try: stored=await app.get_messages(self.storage_channel_id,[m['storage_message_id'] for m in batch])
   except Exception: continue
   group=[]
   # Build each album from files re-read from permanent Telegram storage, not server files.
   for record,message in zip(batch,stored):
    if not message: continue
    item=message.photo or message.video
    if not item: continue
    group.append(InputMediaPhoto(item.file_id,caption=record.get('caption')) if record['media_type']=='photo' else InputMediaVideo(item.file_id,caption=record.get('caption')))
   if not group: continue
   try: msgs=await app.send_media_group(user_id,group,protect_content=protected_content)
   except FloodWait as e: await asyncio.sleep(e.value);msgs=await app.send_media_group(user_id,group,protect_content=protected_content)
   except Exception: continue
   sent.extend(msgs); await asyncio.sleep(.25)
  if cleanup_enabled and sent:
   await self.db.cleanup_messages.insert_many([{'user_id':user_id,'message_id':m.id,'collection_id':collection['_id'],'expiration_time':now()+timedelta(minutes=cleanup_minutes)} for m in sent])
  return len(sent)
