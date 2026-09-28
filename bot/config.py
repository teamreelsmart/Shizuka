from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    bot_token: str
    api_id: int
    api_hash: str
    mongo_uri: str
    database_name: str
    admin_ids: frozenset[int]
    bot_username: str
    default_daily_free_limit: int
    default_referral_reward: int
    default_checkin_reward: int
    cleanup_enabled: bool
    cleanup_after_minutes: int
    shortener_timeout: int
    storage_channel_id: int
    @classmethod
    def from_env(cls):
        ids = frozenset(int(x.strip()) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip())
        token, uri, storage = os.getenv('BOT_TOKEN',''), os.getenv('MONGO_URI',''), os.getenv('STORAGE_CHANNEL_ID','')
        api_id, api_hash = os.getenv('API_ID',''), os.getenv('API_HASH','')
        if not token or not uri or not storage or not api_id or not api_hash:
            raise RuntimeError('BOT_TOKEN, API_ID, API_HASH, MONGO_URI, and STORAGE_CHANNEL_ID are required')
        try: api_id = int(api_id)
        except ValueError as exc: raise RuntimeError('API_ID must be a numeric Telegram API ID') from exc
        try: storage_id = int(storage)
        except ValueError as exc: raise RuntimeError('STORAGE_CHANNEL_ID must be a numeric Telegram chat ID') from exc
        return cls(token, api_id, api_hash, uri, os.getenv('DATABASE_NAME','shizuka'), ids, os.getenv('BOT_USERNAME','').lstrip('@'), int(os.getenv('DEFAULT_DAILY_FREE_LIMIT','10')), int(os.getenv('DEFAULT_REFERRAL_REWARD','5')), int(os.getenv('DEFAULT_CHECKIN_REWARD','2')), os.getenv('CLEANUP_ENABLED','true').lower() == 'true', int(os.getenv('CLEANUP_AFTER_MINUTES','10')), int(os.getenv('SHORTENER_TIMEOUT','15')), storage_id)
