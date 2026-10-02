from pymongo import ReturnDocument
from bot.utils.time import now, day_key

class UserService:
 def __init__(self,db): self.db=db
 async def ensure(self,u):
  # Fields refreshed for every interaction must not also appear in $setOnInsert:
  # MongoDB rejects updates which modify the same path through two operators.
  base={'telegram_id':u.id,'balance':0,'total_earned':0,'total_spent':0,'tasks_completed':0,'friends_referred':0,'daily_watch_count':0,'daily_watch_reset_date':day_key(),'checkin_streak':0,'last_checkin':None,'referred_by':None,'is_banned':False,'created_at':now()}
  profile={'username':u.username,'first_name':u.first_name or 'Friend','last_name':u.last_name,'last_active':now()}
  await self.db.users.update_one({'telegram_id':u.id},{'$setOnInsert':base,'$set':profile},upsert=True)
  return await self.db.users.find_one({'telegram_id':u.id})
 async def daily_view(self,user_id,limit):
  today=day_key(); result=await self.db.users.find_one_and_update({'telegram_id':user_id,'$or':[{'daily_watch_reset_date':{'$ne':today}},{'daily_watch_count':{'$lt':limit}}]},{'$set':{'daily_watch_reset_date':today},'$inc':{'daily_watch_count':1}},return_document=ReturnDocument.AFTER)
  return result is not None
