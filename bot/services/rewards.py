from datetime import timedelta
from bot.utils.time import now, day_key
class RewardService:
 def __init__(self,db,tokens):self.db,self.tokens=db,tokens
 async def checkin(self,user, settings):
  if user.get('last_checkin') and user['last_checkin'].date().isoformat()==day_key(): return None
  yesterday=(now()-timedelta(days=1)).date(); streak=user.get('checkin_streak',0)+1 if user.get('last_checkin') and user['last_checkin'].date()==yesterday else 1
  reward=settings['checkin_base_reward']+(streak-1)*settings['checkin_streak_bonus']
  await self.db.users.update_one({'telegram_id':user['telegram_id']},{'$set':{'last_checkin':now(),'checkin_streak':streak}})
  await self.tokens.change(user['telegram_id'],reward,'EARN_CHECKIN',f'Daily check-in streak {streak}',earned=True); return reward,streak
 async def referral(self,new_user_id,referrer_id,reward):
  if new_user_id==referrer_id or await self.db.referrals.find_one({'referred_user_id':new_user_id}) or not await self.db.users.find_one({'telegram_id':referrer_id}):return False
  await self.db.referrals.insert_one({'referrer_id':referrer_id,'referred_user_id':new_user_id,'created_at':now()})
  await self.db.users.update_one({'telegram_id':new_user_id},{'$set':{'referred_by':referrer_id}})
  await self.tokens.change(referrer_id,reward,'EARN_REFERRAL','Successful referral',str(new_user_id),earned=True,extra={'friends_referred':1});return True
