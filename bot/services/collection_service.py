from pymongo import ReturnDocument
from bot.utils.time import now
class CollectionService:
 def __init__(self,db,tokens): self.db,self.tokens=db,tokens
 async def get(self,id):
  from bson import ObjectId
  try:return await self.db.collections.find_one({'_id':ObjectId(id),'active':True})
  except Exception:return None
 async def latest(self,category_id=None):
  q={'active':True};
  if category_id:q['category_id']=category_id
  return await self.db.collections.find_one(q,sort=[('created_at',-1)])
 async def adjacent(self,c,direction):
  op='$lt' if direction=='prev' else '$gt'; order=-1 if direction=='prev' else 1
  q={'active':True,'created_at':{op:c['created_at']}}
  if c.get('category_id'):q['category_id']=c['category_id']
  return await self.db.collections.find_one(q,sort=[('created_at',order)])
 async def unlock(self,user_id,c):
  from pymongo.errors import DuplicateKeyError
  try:
   await self.db.unlocked_collections.insert_one({'user_id':user_id,'collection_id':c['_id'],'unlocked_at':now()})
  except DuplicateKeyError:return 'already'
  if not await self.tokens.spend_if_possible(user_id,c['price'],str(c['_id']),f'Unlocked {c["title"]}'):
   await self.db.unlocked_collections.delete_one({'user_id':user_id,'collection_id':c['_id']}); return 'insufficient'
  await self.db.collections.update_one({'_id':c['_id']},{'$inc':{'unlock_count':1}});return 'unlocked'
 async def toggle_save(self,user_id,cid):
  exists=await self.db.saved_collections.find_one({'user_id':user_id,'collection_id':cid})
  if exists: await self.db.saved_collections.delete_one({'_id':exists['_id']});return False
  await self.db.saved_collections.insert_one({'user_id':user_id,'collection_id':cid,'saved_at':now()});return True
 async def viewed(self,user_id,c,window):
  cutoff=now().timestamp()-window
  old=await self.db.collection_views.find_one({'user_id':user_id,'collection_id':c['_id']})
  if not old or old['viewed_at'].timestamp()<cutoff:
   await self.db.collection_views.update_one({'user_id':user_id,'collection_id':c['_id']},{'$set':{'viewed_at':now()}},upsert=True);await self.db.collections.update_one({'_id':c['_id']},{'$inc':{'views':1}})
