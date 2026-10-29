from datetime import datetime, time
from pymongo.errors import DuplicateKeyError
from bot.utils.time import now
class TokenService:
 def __init__(self,db): self.db=db
 async def credit_payment(self,user_id,payment_id,amount,description):
  """Credit a payment at most once, including retries after a partial failure."""
  key=f'payment:{payment_id}'
  result=await self.db.users.update_one(
   {'telegram_id':user_id,'credited_payment_ids':{'$ne':str(payment_id)}},
   {'$inc':{'balance':amount,'total_earned':amount},'$addToSet':{'credited_payment_ids':str(payment_id)}})
  if not result.matched_count and not await self.db.users.find_one({'telegram_id':user_id}):return False
  transaction={'user_id':user_id,'amount':amount,'type':'PAYMENT_PURCHASE','description':description,'reference_id':str(payment_id),'idempotency_key':key,'created_at':now()}
  try:
   await self.db.token_transactions.update_one({'idempotency_key':key},{'$setOnInsert':transaction},upsert=True)
  except DuplicateKeyError:
   # A concurrent retry may win the unique idempotency key between lookup/upsert.
   pass
  return True
 async def change(self,user_id,amount,kind,description,reference_id=None, earned=False, spent=False, extra=None):
  inc={'balance':amount};
  if earned: inc['total_earned']=amount
  if spent: inc['total_spent']=abs(amount)
  if extra: inc.update(extra)
  result=await self.db.users.update_one({'telegram_id':user_id},{'$inc':inc})
  if not result.matched_count: return False
  await self.db.token_transactions.insert_one({'user_id':user_id,'amount':amount,'type':kind,'description':description,'reference_id':reference_id,'created_at':now()}); return True
 async def spend_if_possible(self,user_id,amount,reference_id,description):
  result=await self.db.users.update_one({'telegram_id':user_id,'balance':{'$gte':amount}},{'$inc':{'balance':-amount,'total_spent':amount}})
  if not result.modified_count:return False
  await self.db.token_transactions.insert_one({'user_id':user_id,'amount':-amount,'type':'SPEND_COLLECTION','description':description,'reference_id':reference_id,'created_at':now()});return True
 async def earned_today(self,user_id,kind='EARN_SHORTENER'):
  start=datetime.combine(now().date(),time.min)
  rows=await self.db.token_transactions.find({'user_id':user_id,'type':kind,'created_at':{'$gte':start}}).to_list(None)
  return sum(row.get('amount',0) for row in rows)
