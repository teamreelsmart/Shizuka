from copy import deepcopy
DEFAULTS={'daily_free_limit':10,'default_collection_price':5,'checkin_base_reward':2,'checkin_streak_bonus':1,'referral_reward':5,'daily_shortener_earning_limit':50,'cleanup_enabled':True,'cleanup_after_minutes':10,'protected_content':False,'maintenance_mode':False,'shortener_min_seconds':30,'shortener_tolerance_seconds':10,'view_window_seconds':3600}
class SettingsService:
 def __init__(self, db, config): self.db,self.config=db,config
 async def get(self):
  doc=await self.db.settings.find_one({'_id':'global'})
  defaults=deepcopy(DEFAULTS); defaults.update({'daily_free_limit':self.config.default_daily_free_limit,'referral_reward':self.config.default_referral_reward,'checkin_base_reward':self.config.default_checkin_reward,'cleanup_enabled':self.config.cleanup_enabled,'cleanup_after_minutes':self.config.cleanup_after_minutes}); defaults.update((doc or {}).get('values',{})); return defaults
 async def set(self,key,value): await self.db.settings.update_one({'_id':'global'},{'$set':{f'values.{key}':value}},upsert=True)
