import aiohttp, logging, secrets, re
from datetime import timedelta
from urllib.parse import urlsplit, urlunsplit
from bot.utils.time import now, seconds_human

log = logging.getLogger(__name__)

class ShortenerService:
 def __init__(self,db,config,tokens):self.db,self.config,self.tokens=db,config,tokens
 @staticmethod
 def _url_from_response(payload, text):
  """Extract a short URL from common (including nested) JSON API responses."""
  keys=('shortenedUrl','shortened_url','shortened url','shorturl','short_url','url','link')
  if isinstance(payload,dict):
   for key in keys:
    value=payload.get(key)
    if isinstance(value,str) and value.startswith(('https://','http://')): return value
   for value in payload.values():
    url=ShortenerService._url_from_response(value,'')
    if url:return url
  elif isinstance(payload,list):
   for value in payload:
    url=ShortenerService._url_from_response(value,'')
    if url:return url
  match=re.search(r'https?://[^\s"\\]+',text.replace('\\/','/'))
  return match.group(0) if match else None
 @staticmethod
 def _api_endpoint(shortener):
  """Correct the Arolinks documentation URL commonly pasted into API settings."""
  endpoint=shortener['api_url']
  parts=urlsplit(endpoint)
  if parts.hostname and parts.hostname.lower() in ('arolinks.com','www.arolinks.com') and parts.path.rstrip('/').lower() in ('/api','/member/tools/api'):
   return urlunsplit((parts.scheme or 'https',parts.netloc,'/api','',''))
  return endpoint
 @staticmethod
 def _error_from_response(payload):
  """Return a short provider error for admin diagnostics, never the raw response."""
  if not isinstance(payload,dict): return None
  for key in ('message','error','errors','description'):
   value=payload.get(key)
   if isinstance(value,str): return value.replace('\n',' ')[:180]
  return None
 @staticmethod
 def _request_params(api_key,destination,alias=None):
  """Arolinks returns JSON by default; `format=text` is its only format option."""
  params={'api':api_key,'url':destination}
  if alias:params['alias']=alias
  return params
 async def create(self,user_id,shortener,settings):
  latest=await self.db.shortener_tasks.find_one({'user_id':user_id,'shortener_id':shortener['_id'],'completed_at':{'$exists':True}},sort=[('completed_at',-1)])
  if latest:
   remain=(latest['completed_at']+timedelta(hours=shortener['cooldown_hours'])-now()).total_seconds()
   if remain>0:return None, f'⏳ This task is available again after {seconds_human(remain)}.', None
  token=secrets.token_urlsafe(18); destination=f'https://t.me/{self.config.bot_username}?start=task_{token}'
  # Arolinks returns JSON when no format is specified. `format=json` is not part
  # of its documented API; only `format=text` is an optional override.
  alias=f"{shortener.get('alias_prefix','')}{secrets.token_hex(4)}" if shortener.get('alias_enabled') else None
  params=self._request_params(shortener['api_key'],destination,alias)
  try:
   timeout=aiohttp.ClientTimeout(total=self.config.shortener_timeout)
   async with aiohttp.ClientSession(timeout=timeout) as s:
    endpoint=self._api_endpoint(shortener)
    async with s.get(endpoint,params=params) as r:
     raw=await r.text()
     if r.status >= 400: raise ValueError(f'HTTP {r.status}')
     try: payload=await r.json(content_type=None)
     except Exception: payload=None
     url=self._url_from_response(payload,raw)
     if not url: raise ValueError(f'response has no short URL{": " + self._error_from_response(payload) if self._error_from_response(payload) else ""}')
  except Exception as exc:
   # Do not put API keys, generated task URLs, or response bodies in logs.
   log.exception('shortener request failed provider=%s endpoint=%s error=%s',shortener.get('name','unknown'),self._api_endpoint(shortener).split('?')[0],exc)
   return None,'❌ The sponsor task is temporarily unavailable. Please try another task.', f'{type(exc).__name__}: {exc}'
  doc={'token':token,'user_id':user_id,'shortener_id':shortener['_id'],'created_at':now(),'expires_at':now()+timedelta(hours=1),'min_verify_at':now()+timedelta(seconds=settings['shortener_min_seconds']),'url':url}
  await self.db.shortener_tasks.insert_one(doc);return doc,None,None
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
