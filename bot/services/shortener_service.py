import aiohttp, secrets, re
from datetime import timedelta
from bot.utils.time import now, seconds_human

class ShortenerService:
 def __init__(self,db,config,tokens):self.db,self.config,self.tokens=db,config,tokens
 @staticmethod
 def _url_from_response(payload, text):
  """Accept common JSON keys or a plain-text short URL without exposing secrets."""
  if isinstance(payload,dict):
   for key in ('shortenedUrl','shortened_url','shortened url','shorturl','url'):
    value=payload.get(key)
    if isinstance(value,str) and value.startswith(('https://','http://')): return value
  match=re.search(r'https?://[^\s"\\]+',text.replace('\\/','/'))
  return match.group(0) if match else None
 async def create(self,user_id,shortener,settings):
  latest=await self.db.shortener_tasks.find_one({'user_id':user_id,'shortener_id':shortener['_id'],'completed_at':{'$exists':True}},sort=[('completed_at',-1)])
  if latest:
   remain=(latest['completed_at']+timedelta(hours=shortener['cooldown_hours'])-now()).total_seconds()
   if remain>0:return None, f'⏳ This task is available again after {seconds_human(remain)}.'
  token=secrets.token_urlsafe(18); destination=f'https://t.me/{self.config.bot_username}?start=task_{token}'
  # `format=text` works with common shortener APIs while ignored safely by JSON-only providers.
  params={'api':shortener['api_key'],'url':destination,'format':'text'}
  if shortener.get('alias_enabled'):params['alias']=f"{shortener.get('alias_prefix','')}{secrets.token_hex(4)}"
  try:
   timeout=aiohttp.ClientTimeout(total=self.config.shortener_timeout)
   async with aiohttp.ClientSession(timeout=timeout) as s:
    async with s.get(shortener['api_url'],params=params) as r:
     raw=await r.text()
     if r.status >= 400: raise ValueError(f'HTTP {r.status}')
     try: payload=await r.json(content_type=None)
     except Exception: payload=None
     url=self._url_from_response(payload,raw)
     if not url: raise ValueError('response has no short URL')
  except Exception:return None,'❌ The sponsor task is temporarily unavailable. Please try another task.'
  doc={'token':token,'user_id':user_id,'shortener_id':shortener['_id'],'created_at':now(),'expires_at':now()+timedelta(hours=1),'min_verify_at':now()+timedelta(seconds=settings['shortener_min_seconds']),'url':url}
  await self.db.shortener_tasks.insert_one(doc);return doc,None
 async def verify(self,user_id,token,settings):
  task=await self.db.shortener_tasks.find_one({'token':token,'user_id':user_id,'completed_at':{'$exists':False}})
  if not task:return 'expired',None
  if now()<task['min_verify_at']-timedelta(seconds=settings['shortener_tolerance_seconds']):
   await self.db.suspicious_activity.insert_one({'user_id':user_id,'task_id':task['_id'],'shortener_id':task['shortener_id'],'reason':'verification_too_early','timestamp':now()})
   await self.db.users.update_one({'telegram_id':user_id},{'$set':{'is_banned':True,'ban_reason':'Suspicious shortener verification','banned_at':now()}});return 'banned',None
  s=await self.db.shorteners.find_one({'_id':task['shortener_id'],'enabled':True})
  if not s:return 'expired',None
  result=await self.db.shortener_tasks.update_one({'_id':task['_id'],'completed_at':{'$exists':False}},{'$set':{'completed_at':now()}})
  if not result.modified_count:return 'expired',None
  await self.tokens.change(user_id,s['reward_tokens'],'EARN_SHORTENER',f'Sponsor task: {s["name"]}',str(task['_id']),earned=True,extra={'tasks_completed':1});return 'ok',s['reward_tokens']
