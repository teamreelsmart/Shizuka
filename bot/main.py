import asyncio, logging, os
from dotenv import load_dotenv
from pyrogram import Client, idle
from bot.config import Config
from bot.database.mongo import Mongo
from bot.services.user_service import UserService
from bot.services.token_service import TokenService
from bot.services.collection_service import CollectionService
from bot.services.rewards import RewardService
from bot.services.shortener_service import ShortenerService
from bot.services.media_service import MediaService
from bot.services.settings_service import SettingsService
from bot.services.storage_service import StorageService
from bot.services.app_service import AppService
from bot.workers.cleanup_worker import cleanup_worker
from bot.handlers.common import register_common
from bot.health import start_health_server
async def run():
 load_dotenv(); logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'),format='%(asctime)s %(levelname)s %(name)s: %(message)s')
 config=Config.from_env(); health_runner=await start_health_server(); mongo=Mongo(config.mongo_uri,config.database_name);await mongo.connect()
 app=Client('shizuka_bot', api_id=config.api_id, api_hash=config.api_hash, bot_token=config.bot_token, in_memory=True)
 tokens=TokenService(mongo.db);settings=SettingsService(mongo.db,config)
 service=AppService(app,mongo.db,config,UserService(mongo.db),CollectionService(mongo.db,tokens),tokens,RewardService(mongo.db,tokens),ShortenerService(mongo.db,config,tokens),MediaService(mongo.db,config.storage_channel_id),settings,StorageService(config.storage_channel_id))
 register_common(app,service);await app.start(); logging.info('Bot started')
 worker=asyncio.create_task(cleanup_worker(app,mongo.db,settings))
 try:await idle()
 finally:
  worker.cancel(); await app.stop(); mongo.close(); await health_runner.cleanup()
if __name__=='__main__':asyncio.run(run())
