from bson import ObjectId
from pyrogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as K
from bot.keyboards import user as kb
from bot.keyboards.admin import main as admin_kb
from bot.utils.formatting import collection_text
from bot.utils.pagination import page_data
from bot.utils.time import now
import logging

log=logging.getLogger(__name__)
class AppService:
 def __init__(self,app,db,config,users,collections,tokens,rewards,shorteners,media,settings,storage): self.app,self.db,self.config,self.users,self.collections,self.tokens,self.rewards,self.shorteners,self.media,self.settings,self.storage=app,db,config,users,collections,tokens,rewards,shorteners,media,settings,storage
 def admin_ok(self,id):return id in self.config.admin_ids
 async def notify_admins(self,context,error,**details):
  """Send a concise, secret-free operational error report to each admin."""
  values='\n'.join(f'<b>{key}:</b> <code>{str(value)[:180]}</code>' for key,value in details.items() if value is not None)
  message=f'⚠️ <b>Bot error</b>\n<b>Where:</b> <code>{context}</code>\n<b>Error:</b> <code>{type(error).__name__}: {str(error)[:300]}</code>'
  if values:message+=f'\n{values}'
  for admin_id in self.config.admin_ids:
   try:await self.app.send_message(admin_id,message)
   except Exception:log.exception('could not notify admin_id=%s about %s',admin_id,context)
 async def guarded(self,u):
  user=await self.users.ensure(u); s=await self.settings.get()
  return user, (user['is_banned'] or (s['maintenance_mode'] and not self.admin_ok(u.id)))
 async def edit(self,q,text,markup):
  try:
   if q.message.photo: await q.message.edit_caption(text,reply_markup=markup)
   else: await q.message.edit_text(text,reply_markup=markup)
  except Exception: await q.message.reply_text(text,reply_markup=markup)
 async def start(self,m):
  user,blocked=await self.guarded(m.from_user)
  args=m.command[1] if len(m.command)>1 else ''
  if args.startswith('task_'):
   settings=await self.settings.get(); state,reward=await self.shorteners.verify(m.from_user.id,args[5:],settings)
   if state=='ok':
    updated=await self.db.users.find_one({'telegram_id':m.from_user.id})
    earned=await self.tokens.earned_today(m.from_user.id)
    limit=settings.get('daily_shortener_earning_limit',50)
    await m.reply_text(f'🎉 <b>Reward Credited</b>\n\n💰 +{reward} Tokens added to your wallet.\n🪙 Balance: {updated["balance"]} tokens\n📊 Today\'s Earnings: {earned}/{limit} tokens\n\nEnjoy your media stream!')
   else: await m.reply_text('🚫 Suspicious verification detected; your account was restricted.' if state=='banned' else '❌ This sponsor session is expired or unavailable.')
   return
  if blocked: await m.reply_text('🚫 Your account is currently restricted.' if user['is_banned'] else '🛠 Bot is currently under maintenance.');return
  if args.isdigit() and user.get('referred_by') is None:
   reward=(await self.settings.get())['referral_reward']; referrer_id=int(args)
   if await self.rewards.referral(m.from_user.id,referrer_id,reward):
    try:await self.app.send_message(referrer_id,f'🎉 <b>New Referral!</b>\n\nHey! {user["first_name"]} joined using your referral link.\n💰 +{reward} Tokens have been added to your wallet.')
    except Exception:log.exception('could not notify referrer_id=%s',referrer_id)
  await m.reply_text(await self.welcome(user),reply_markup=kb.menu())
 async def welcome(self,u):
  unlocked=await self.db.unlocked_collections.count_documents({'user_id':u['telegram_id']});saved=await self.db.saved_collections.count_documents({'user_id':u['telegram_id']})
  return f'🎀 Welcome, {u["first_name"]}!\n\n👛 Token Balance: {u["balance"]}\n📦 Unlocked Collections: {unlocked}\n🔖 Saved Collections: {saved}'
 async def checkin(self,m):
  u,blocked=await self.guarded(m.from_user)
  if blocked:return
  got=await self.rewards.checkin(u,await self.settings.get());await m.reply_text(f'🎁 Check-in claimed: +{got[0]} Tokens! Streak: {got[1]} day(s).' if got else '⏳ You have already claimed today.')
 async def callback(self,q):
  u,blocked=await self.guarded(q.from_user)
  if blocked:await q.answer('Account unavailable.',show_alert=True);return
  p=q.data.split(':'); action=p[0]
  if action=='noop':return
  if action=='style': return await q.answer('Styled keyboard test button received.')
  if action=='menu': return await self.menu(q,p[1],u)
  if action=='nav':
   c=await self.collections.get(p[2]); n=await self.collections.adjacent(c,p[1]) if c else None
   if not n: await q.answer('You are already viewing the '+('oldest.' if p[1]=='prev' else 'latest.'),show_alert=True)
   else: await self.show_collection(q,u,n)
  elif action=='col': await self.collection_action(q,u,p)
  elif action=='cat':
   c=await self.collections.latest(p[1]); await self.show_collection(q,u,c) if c else await q.answer('No active collections in this category.',show_alert=True)
  elif action=='task': await self.task(q,u,p[1])
  elif action=='vault': await self.vault(q,u,p[1],int(p[2]))
  elif action=='admin': await self.admin_callback(q,p[1:])
 async def menu(self,q,which,u):
  if which=='home':return await self.edit(q,await self.welcome(u),kb.menu())
  if which=='profile':
   a=await self.db.unlocked_collections.count_documents({'user_id':u['telegram_id']});b=await self.db.saved_collections.count_documents({'user_id':u['telegram_id']})
   t=f'👤 <b>USER PROFILE</b>\n\nAccount ID: <code>{u["telegram_id"]}</code>\nBalance: {u["balance"]} Tokens\n\nCollections:\n📦 Unlocked: {a}\n🔖 Saved: {b}\n\nEconomy Telemetry:\n💰 Total Earned Tokens: {u["total_earned"]}\n💸 Total Spent Tokens: {u["total_spent"]}\n🧩 Tasks Solved: {u["tasks_completed"]}\n👥 Friends Referred: {u["friends_referred"]}\n🎬 Daily Free Usage: {u["daily_watch_count"]} / {(await self.settings.get())["daily_free_limit"]}'
   return await self.edit(q,t,kb.profile())
  if which=='help':return await self.edit(q,"🎀 <b>CUTE ASSISTANT'S GUIDE & MANUAL</b> (⁄ ⁄•⁄ω⁄•⁄ ⁄)✨\n━━━━━━━━━━━━━━━━━━━━\n<i>U-Uwahh, don't worry if you get lost, Senpai! I'm here to explain everything! 🌸</i>\n\n<b>1. Instant Media Stream 🎬:</b>\n• Tap <b>Start Watching</b> to browse.\n• Use Next or Previous and Categories.\n\n<b>2. One-Tap Unlocking & Media Albums 📦:</b>\n• Unlock delivers the full collection.\n• Your Profile Vault keeps it available.\n• Delivered media may clean up automatically.\n\n<b>3. Free Token Rewards 👛:</b>\n• Complete sponsor tasks, use /checkin, and refer friends (+5 by default).\n━━━━━━━━━━━━━━━━━━━━\n🌸 <i>Tap Main Menu whenever you need me!</i>",K([[B('▶️ Start Watching','menu:start')],[B('👤 Profile','menu:profile'),B('🏠 Main Menu','menu:home')]]))
  if which=='categories':
   cats=await self.db.categories.find({'active':True}).sort('name',1).to_list(None); lines=['🎀 <b>EXPLORE CATEGORIES, SENPAI~!</b> ✨','━━━━━━━━━━━━━━━━━━━━','<i>Filter feeds by curated categories:</i>','']
   rows=[]
   for x in cats:
    count=await self.db.collections.count_documents({'category_id':str(x['_id']),'active':True});lines.append(f'• <b>{x["name"]}</b> — {count} collections'+(f'\n  {x["description"]}' if x.get('description') else ''));
    if not rows or len(rows[-1])==2:rows.append([])
    rows[-1].append(B(x['name'][:40],f'cat:{x["_id"]}'))
   return await self.edit(q,'\n'.join(lines),kb.categories(rows))
  if which=='earn':
   ss=await self.db.shorteners.find({'enabled':True}).to_list(None); rows=[]
   for s in ss:
    if not rows or len(rows[-1])==2:rows.append([])
    rows[-1].append(B(f'👀 {s["name"]}'[:55],f'task:{s["_id"]}'))
   rows.append([B('🏠 Main Menu','menu:home')]);return await self.edit(q,f'🎀 <b>EARN FREE TOKENS, SENPAI~!</b> ✨\n━━━━━━━━━━━━━━━━━━━━\n\n👛 <b>Your Balance:</b> {u["balance"]} Tokens\n\n1. Tap a task.\n2. Complete sponsor verification.\n3. Return to the bot.\n4. Tokens are added instantly after valid verification.\n\n🌸 Each task has its own cooldown.',K(rows))
  if which=='refer':return await self.edit(q,f'👥 <b>REFER FRIENDS</b>\n\nShare your personal invite link:\nhttps://t.me/{self.config.bot_username}?start={u["telegram_id"]}\n\nEarn {(await self.settings.get())["referral_reward"]} Tokens for each new friend!',kb.back())
  if which=='start':
   s=await self.settings.get()
   if not await self.users.daily_view(u['telegram_id'],s['daily_free_limit']):return await self.edit(q,'🎬 Your free daily limit has been reached. Unlock collections to receive all media.',K([[B('💰 Earn Tokens','menu:earn')],[B('📦 Browse Collections','menu:start'),B('🏠 Main Menu','menu:home')]]))
   c=await self.collections.latest();return await self.show_collection(q,u,c) if c else await self.edit(q,'📭 No active collections are available yet.',kb.back())
 async def show_collection(self,q,u,c):
  s=await self.settings.get();await self.collections.viewed(u['telegram_id'],c,s['view_window_seconds']);cat=await self.db.categories.find_one({'_id':ObjectId(c['category_id'])}) if c.get('category_id') else None;saved=bool(await self.db.saved_collections.find_one({'user_id':u['telegram_id'],'collection_id':c['_id']}));text=collection_text(c,(cat or {}).get('name','Uncategorized')); markup=kb.card(str(c['_id']),saved)
  try:
   from pyrogram.types import InputMediaPhoto
   if q.message.photo: return await q.message.edit_media(InputMediaPhoto(c['cover_file_id'],caption=text),reply_markup=markup)
   await q.message.reply_photo(c['cover_file_id'],caption=text,reply_markup=markup); return await self.edit(q,'📦 <b>Collection card opened below.</b>',kb.back())
  except Exception: return await self.edit(q,text,markup)
 async def collection_action(self,q,u,p):
  c=await self.collections.get(p[2]);
  if not c:return await q.answer('This collection no longer exists.',show_alert=True)
  if p[1]=='save':await q.answer('Saved!' if await self.collections.toggle_save(u['telegram_id'],c['_id']) else 'Removed from saved collections.');return await self.show_collection(q,u,c)
  state=await self.collections.unlock(u['telegram_id'],c)
  if state=='insufficient':return await self.edit(q,f'❌ <b>Insufficient Balance</b>\n\nRequired: {c["price"]} Tokens\nYour balance: {u["balance"]} Tokens',K([[B('💰 Earn Tokens','menu:earn')],[B('🏠 Main Menu','menu:home')]]))
  if state in ('unlocked','already'):
   await q.answer('Already unlocked — sending again.' if state=='already' else 'Unlocked! Sending media.')
   s=await self.settings.get(); count=await self.media.deliver(self.app,u['telegram_id'],c,s['cleanup_after_minutes'],s['cleanup_enabled'])
   if not count:await q.message.reply_text('⚠️ This collection has no deliverable media. Please contact an admin.')
 async def task(self,q,u,sid):
  try:s=await self.db.shorteners.find_one({'_id':ObjectId(sid),'enabled':True})
  except Exception:s=None
  if not s:return await q.answer('Task unavailable.',show_alert=True)
  try:task,error,error_detail=await self.shorteners.create(u['telegram_id'],s,await self.settings.get())
  except Exception as exc:
   log.exception('task creation failed user_id=%s shortener_id=%s',u['telegram_id'],sid)
   await self.notify_admins('shortener task creation',exc,user_id=u['telegram_id'],provider=s.get('name'),shortener_id=sid)
   return await q.answer('❌ The sponsor task could not be created. The admin has been notified.',show_alert=True)
  if error:
   if error.startswith('❌'):
    await self.notify_admins('shortener API request',RuntimeError(error_detail or error),user_id=u['telegram_id'],provider=s.get('name'),shortener_id=sid)
   return await q.answer(error,show_alert=True)
  await q.message.reply_text(f'👀 <b>{s["name"]}</b>\n\nTap the button below to open the sponsor task. Complete it, then return to the bot after approximately 3 minutes.\n\nReward: {s["reward_tokens"]} Tokens.',reply_markup=K([[B('🔗 Open Sponsor Task',url=task['url'])]]))
 async def vault(self,q,u,kind,page):
  source='unlocked_collections' if kind=='unlocked' else 'saved_collections'; total=await self.db[source].count_documents({'user_id':u['telegram_id']});page,pages,size=page_data(total,page);items=await self.db[source].find({'user_id':u['telegram_id']}).sort('unlocked_at' if kind=='unlocked' else 'saved_at',-1).skip(page*size).limit(size).to_list(size);rows=[];text=f'📦 <b>YOUR {kind.upper()} COLLECTIONS</b>\n\n'
  for i,x in enumerate(items,page*size+1):
   c=await self.db.collections.find_one({'_id':x['collection_id']});
   if c: text+=f'{i}. {c["title"]}\n';rows.append([B(c['title'][:50],f'vaultopen:{kind}:{c["_id"]}')])
  if not items:text+='No collections yet.'
  rows += [[*kb.pager(f'vault:{kind}',page,pages)],[B('👤 Profile','menu:profile')]];await self.edit(q,text,K(rows))
 async def admin(self,m):
  if not self.admin_ok(m.from_user.id):return await m.reply_text('❌ You are not authorized to access the admin panel.')
  await m.reply_text('🛠 <b>ADMIN PANEL</b>',reply_markup=admin_kb())
 async def admin_callback(self,q,p):
  if not self.admin_ok(q.from_user.id): return await q.answer('Unauthorized.',show_alert=True)
  section=p[0]; action=p[1] if len(p)>1 else None
  if section=='home': return await self.edit(q,'🛠 <b>ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ</b>',admin_kb())
  if section=='storage':
   _, report=await self.storage.status(self.app); return await self.edit(q,report,K([[B('🔄 Test Again','admin:storage')],[B('🏠 Admin Menu','admin:home')]]))
  if section=='shorteners' and action=='add':
   await self.db.admin_sessions.delete_many({'admin_id':q.from_user.id,'kind':'shortener'})
   await self.db.admin_sessions.insert_one({'admin_id':q.from_user.id,'kind':'shortener','step':'name','data':{},'created_at':now()})
   return await q.message.reply_text('🔗 <b>ᴀᴅᴅ sʜᴏʀᴛᴇɴᴇʀ</b>\n\nSend the <b>shortener name</b>.')
  if section=='shorteners' and action=='delete' and len(p)>2:
   try: await self.db.shorteners.delete_one({'_id':ObjectId(p[2])})
   except Exception: pass
   return await q.answer('Shortener removed.')
  if section=='shorteners':
   items=await self.db.shorteners.find({}).sort('created_at',-1).to_list(None); rows=[]; text='🔗 <b>sʜᴏʀᴛᴇɴᴇʀs</b>\n\n'
   for item in items:
    text+=f'• <b>{item["name"]}</b> — {item.get("reward_tokens",0)} tokens / {item.get("cooldown_hours",0)}h ({"enabled" if item.get("enabled") else "disabled"})\n'; rows.append([B('🗑 Remove '+item['name'][:24],f'admin:shorteners:delete:{item["_id"]}')])
   if not items:text+='No shorteners configured yet.\n'
   rows += [[B('➕ Add New','admin:shorteners:add')],[B('🏠 Admin Menu','admin:home')]]; return await self.edit(q,text,K(rows))
  if section=='categories' and action=='add':
   await self.db.admin_sessions.delete_many({'admin_id':q.from_user.id,'kind':'category'})
   await self.db.admin_sessions.insert_one({'admin_id':q.from_user.id,'kind':'category','step':'name','data':{}})
   return await q.message.reply_text('📂 <b>ᴀᴅᴅ ᴄᴀᴛᴇɢᴏʀʏ</b>\n\nSend the category name.')
  if section=='categories' and action=='delete' and len(p)>2:
   try:
    oid=ObjectId(p[2])
    # Detach collections so demo categories can be removed without orphaned UI state.
    await self.db.collections.update_many({'category_id':str(oid)},{'$set':{'category_id':None,'updated_at':now()}})
    await self.db.categories.delete_one({'_id':oid})
   except Exception:return await q.answer('Invalid category.',show_alert=True)
   return await q.answer('Category removed; dependent collections are now Uncategorized.')
  if section=='categories':
   items=await self.db.categories.find({}).sort('name',1).to_list(None); rows=[]; text='📂 <b>ᴄᴀᴛᴇɢᴏʀɪᴇs</b>\n\n'
   for item in items:
    count=await self.db.collections.count_documents({'category_id':str(item['_id'])}); text+=f'• <b>{item["name"]}</b> — {count} collections\n'; rows.append([B('🗑 Remove '+item['name'][:24],f'admin:categories:delete:{item["_id"]}')])
   if not items:text+='No categories yet.\n'
   rows += [[B('➕ Add Category','admin:categories:add')],[B('🏠 Admin Menu','admin:home')]]; return await self.edit(q,text,K(rows))
  if section=='set' and action:
   await self.db.admin_sessions.delete_many({'admin_id':q.from_user.id,'kind':'setting'})
   await self.db.admin_sessions.insert_one({'admin_id':q.from_user.id,'kind':'setting','key':action})
   return await q.message.reply_text(f'⚙️ Send a new value for <b>{action}</b>.')
  if section in ('economy','rewards','settings','system'):
   values=await self.settings.get(); keys={'economy':['daily_free_limit','default_collection_price'],'rewards':['checkin_base_reward','checkin_streak_bonus','referral_reward'],'settings':['cleanup_enabled','cleanup_after_minutes'],'system':['maintenance_mode']}[section]
   rows=[[B(f'{key}: {values.get(key)}',f'admin:set:{key}')] for key in keys]; rows.append([B('🏠 Admin Menu','admin:home')])
   return await self.edit(q,f'⚙️ <b>{section.upper()}</b>\n\nTap a value to update it.',K(rows))
  if section=='collections' and action=='delete' and len(p)>2:
   try:
    oid=ObjectId(p[2]); await self.db.collection_media.delete_many({'collection_id':oid}); await self.db.collections.delete_one({'_id':oid})
   except Exception:return await q.answer('Invalid collection.',show_alert=True)
   return await q.answer('Collection deleted.')
  if section=='collections':
   items=await self.db.collections.find({}).sort('created_at',-1).to_list(None); rows=[]; text='🗂 <b>ᴄᴏʟʟᴇᴄᴛɪᴏɴs</b>\n\n'
   for item in items:
    text+=f'• <b>{item["title"]}</b> — {item.get("media_count",0)} files\n'; rows.append([B('🗑 Delete '+item['title'][:24],f'admin:collections:delete:{item["_id"]}')])
   if not items:text+='No collections yet.\n'
   rows += [[B('➕ Add Collection','admin:flow:newcollection')],[B('🏠 Admin Menu','admin:home')]]
   return await self.edit(q,text,K(rows))
  if section=='stats':
   users=await self.db.users.count_documents({}); cols=await self.db.collections.count_documents({}); return await self.edit(q,f'📊 <b>sᴛᴀᴛɪsᴛɪᴄs</b>\n\n👥 Users: {users}\n📦 Collections: {cols}\n🔓 Unlocks: {await self.db.unlocked_collections.count_documents({})}',K([[B('🏠 Admin Menu','admin:home')]]))
  if section=='users': return await self.edit(q,'👥 <b>ᴜsᴇʀs</b>\n\nUse the user-management controls to search and moderate accounts.',K([[B('🏠 Admin Menu','admin:home')]]))
  if section=='broadcast': return await self.edit(q,'📢 <b>ʙʀᴏᴀᴅᴄᴀsᴛ</b>\n\nSend the message you want to broadcast, then confirm it in the broadcast workflow.',K([[B('🏠 Admin Menu','admin:home')]]))
  if section=='flow':
   await self.db.admin_sessions.delete_many({'admin_id':q.from_user.id,'kind':'collection'})
   await self.db.admin_sessions.insert_one({'admin_id':q.from_user.id,'kind':'collection','stage':'title','media':[],'created_at':now()})
   return await q.message.reply_text('🗂 <b>ᴀᴅᴅ ᴄᴏʟʟᴇᴄᴛɪᴏɴ</b>\n\nSend the collection <b>title</b>.')
 async def input(self,m):
  # Guided collection uploads are persisted, so bot restarts do not lose admin state.
  if not self.admin_ok(m.from_user.id):return
  session=await self.db.admin_sessions.find_one({'admin_id':m.from_user.id,'kind':'collection'})
  if session and (m.photo or m.video):
   if session.get('stage')=='cover':

    try: cover=await self.storage.archive(self.app,m)
    except Exception: return await m.reply_text('❌ Could not archive cover to the Storage Channel. Use Admin → Storage Status/Test, then retry.')
    await self.db.admin_sessions.update_one({'_id':session['_id']},{'$set':{'cover':cover,'stage':'media'}});return await m.reply_text('Cover stored permanently. Send photos/videos in order, then /finishcollection.')

   try: media=await self.storage.archive(self.app,m)
   except Exception: return await m.reply_text('❌ Could not archive media to the Storage Channel. Use Admin → Storage Status/Test, then retry.')
   await self.db.admin_sessions.update_one({'_id':session['_id']},{'$push':{'media':media}});return await m.reply_text('Media stored permanently. Send more or /finishcollection.')
  text=m.text or ''; parts=text.split(maxsplit=2)
  if session and text and not text.startswith('/') and session.get('stage') in ('title','category','price','description'):
   stage=session['stage']
   if stage=='title':
    await self.db.admin_sessions.update_one({'_id':session['_id']},{'$set':{'title':text.strip(),'stage':'category'}}); return await m.reply_text('Send the <b>category name</b>.')
   if stage=='category':
    category=await self.db.categories.find_one({'name':text.strip(),'active':True})
    if not category:return await m.reply_text('❌ Category not found. Send its exact name or create it first in Admin → Categories.')
    await self.db.admin_sessions.update_one({'_id':session['_id']},{'$set':{'category_id':str(category['_id']),'stage':'price'}}); return await m.reply_text('Send the collection <b>token price</b>.')
   if stage=='price':
    try: price=int(text.strip())
    except ValueError:return await m.reply_text('❌ Send a whole-number token price.')
    if price<0:return await m.reply_text('❌ Price cannot be negative.')
    await self.db.admin_sessions.update_one({'_id':session['_id']},{'$set':{'price':price,'stage':'description'}}); return await m.reply_text('Send an optional <b>description</b>, or send <code>-</code> to skip.')
   description='' if text.strip()=='-' else text.strip()
   await self.db.admin_sessions.update_one({'_id':session['_id']},{'$set':{'description':description,'stage':'cover'}}); return await m.reply_text('Send the collection <b>cover image</b>.')
  flow=await self.db.admin_sessions.find_one({'admin_id':m.from_user.id,'kind':{'$in':['shortener','category','setting']}})
  if flow and text and not text.startswith('/'):
   if flow['kind']=='category':
    await self.db.categories.insert_one({'name':text.strip(),'description':'','active':True,'created_at':now()}); await self.db.admin_sessions.delete_one({'_id':flow['_id']}); return await m.reply_text(f'✅ Category <b>{text.strip()}</b> created.')
   if flow['kind']=='setting':
    value={'true':True,'false':False}.get(text.strip().lower(),text.strip())
    try:value=int(value)
    except (TypeError,ValueError):pass
    await self.settings.set(flow['key'],value); await self.db.admin_sessions.delete_one({'_id':flow['_id']}); return await m.reply_text(f'✅ <b>{flow["key"]}</b> is now <b>{value}</b>.')
   data=flow.get('data',{}); step=flow['step']; order=['name','api_url','api_key','domain','alias_enabled','reward_tokens','cooldown_hours','alias_prefix']
   if step=='alias_enabled' and text.strip().lower() not in ('true','false'): return await m.reply_text('Please send exactly <b>true</b> or <b>false</b>.')
   if step in ('reward_tokens','cooldown_hours'):
    try:int(text.strip())
    except ValueError:return await m.reply_text('Please send a whole number.')
   data[step]=text.strip(); index=order.index(step)
   if step=='alias_enabled' and text.strip().lower()=='false': index=order.index('alias_prefix')
   if index==len(order)-1:
    doc={'name':data['name'],'api_url':data['api_url'],'api_key':data['api_key'],'domain':data['domain'],'enabled':True,'reward_tokens':int(data['reward_tokens']),'cooldown_hours':int(data['cooldown_hours']),'alias_enabled':data['alias_enabled'].lower()=='true','alias_prefix':data.get('alias_prefix',''),'created_at':now()}
    await self.db.shorteners.insert_one(doc); await self.db.admin_sessions.delete_one({'_id':flow['_id']}); return await m.reply_text(f'✅ <b>Shortener ready</b>\n\nName: {doc["name"]}\nDomain: {doc["domain"]}\nReward: {doc["reward_tokens"]} Tokens\nCooldown: {doc["cooldown_hours"]} hours\nAlias: {doc["alias_enabled"]}\n\n<i>Demo destination:</i> https://t.me/{self.config.bot_username}?start=shortener_demo')
   next_step=order[index+1]
   prompts={'api_url':'Now send the <b>API URL</b>.','api_key':'Now send the <b>API key</b>.','domain':'Now send the <b>domain</b>.','alias_enabled':'Enable aliases? Send <b>true</b> or <b>false</b>.','reward_tokens':'Send the <b>reward tokens</b>.','cooldown_hours':'Send the <b>cooldown hours</b>.','alias_prefix':'Send the <b>alias prefix</b>.'}
   await self.db.admin_sessions.update_one({'_id':flow['_id']},{'$set':{'step':next_step,'data':data}}); return await m.reply_text(prompts[next_step])
  if text == '/buttonstyles':
   from bot.utils.button_styles import test_keyboard
   keyboard, error = test_keyboard()
   if error:
    return await m.reply_text('⚠️ ButtonStyle is not supported by the installed Pyrofork runtime: ' + error)
   return await m.reply_text('Temporary ButtonStyle compatibility test. Telegram should render PRIMARY blue, SUCCESS green, and DANGER red.', reply_markup=keyboard)
  if text.startswith('/newcollection '):
   values=[x.strip() for x in text[len('/newcollection '):].split('|')]
   if len(values)<3:return await m.reply_text('Usage: /newcollection Title | category_id | price | optional description')
   try: price=int(values[2])
   except ValueError:return await m.reply_text('Price must be a non-negative integer.')
   cat=await self.db.categories.find_one({'name':values[1],'active':True})
   if not cat:return await m.reply_text('❌ Category not found. Open Admin → Categories and use the exact category name.')
   values[1]=str(cat['_id'])
   await self.db.admin_sessions.delete_many({'admin_id':m.from_user.id,'kind':'collection'})
   await self.db.admin_sessions.insert_one({'admin_id':m.from_user.id,'kind':'collection','stage':'cover','title':values[0],'category_id':values[1],'price':price,'description':values[3] if len(values)>3 else '','media':[],'created_at':now()});return await m.reply_text('Send collection cover image.')
  if text=='/finishcollection' and session:
   if session.get('stage')!='media' or not session.get('media'):return await m.reply_text('Send a cover and at least one photo/video first.')
   c={'title':session['title'],'description':session['description'],'category_id':session['category_id'],'cover_file_id':session['cover']['file_id'],'cover_storage_message_id':session['cover']['storage_message_id'],'price':session['price'],'views':0,'unlock_count':0,'media_count':len(session['media']),'active':True,'created_at':now(),'updated_at':now()}; result=await self.db.collections.insert_one(c)
   await self.db.collection_media.insert_many([{'collection_id':result.inserted_id,**item,'order':i} for i,item in enumerate(session['media'])]);await self.db.admin_sessions.delete_one({'_id':session['_id']});return await m.reply_text(f'✅ Published collection {c["title"]} with {c["media_count"]} items.')
  if text.startswith('/newshortener '):
   fields=[x.strip() for x in text[len('/newshortener '):].split('|')]
   if len(fields)<6:return await m.reply_text('Usage: /newshortener Name | API URL | API key | Domain | Reward | Cooldown hours | alias prefix(optional)')
   try: reward,cooldown=int(fields[4]),int(fields[5])
   except ValueError:return await m.reply_text('Reward and cooldown must be integers.')
   await self.db.shorteners.insert_one({'name':fields[0],'api_url':fields[1],'api_key':fields[2],'domain':fields[3],'enabled':True,'reward_tokens':reward,'cooldown_hours':cooldown,'alias_enabled':len(fields)>6 and bool(fields[6]),'alias_prefix':fields[6] if len(fields)>6 else '','created_at':now()});return await m.reply_text('✅ Shortener added. Its API key is stored privately.')
  if text=='/listcategories':
   cats=await self.db.categories.find({}).to_list(None);return await m.reply_text('\n'.join(f'{x["_id"]} — {x["name"]} ({"active" if x["active"] else "disabled"})' for x in cats) or 'No categories.')
  if text=='/listcollections':
   items=await self.db.collections.find({}).sort('created_at',-1).limit(30).to_list(30);return await m.reply_text('\n'.join(f'{x["_id"]} — {x["title"]} ({"active" if x["active"] else "inactive"})' for x in items) or 'No collections.')
  if text.startswith('/newcategory '):
   data=text[len('/newcategory '):].split('|',1);await self.db.categories.insert_one({'name':data[0].strip(),'description':data[1].strip() if len(data)>1 else '','active':True,'created_at':now()});return await m.reply_text('✅ Category created.')
  if text.startswith('/set ') and len(parts)==3:
   key,value=parts[1],parts[2]; value={'true':True,'false':False}.get(value.lower(),value)
   try:value=int(value)
   except ValueError:pass
   await self.settings.set(key,value);return await m.reply_text('✅ Setting updated.')
  if text.startswith('/ban ') and len(parts)>=2:
   try:uid=int(parts[1])
   except ValueError:return
   await self.db.users.update_one({'telegram_id':uid},{'$set':{'is_banned':True,'ban_reason':parts[2] if len(parts)>2 else 'Admin action','banned_at':now(),'banned_by':m.from_user.id}});return await m.reply_text('✅ User banned.')
  if text.startswith('/unban ') and len(parts)>=2:
   await self.db.users.update_one({'telegram_id':int(parts[1])},{'$set':{'is_banned':False,'ban_reason':None}});return await m.reply_text('✅ User unbanned.')
  if text.startswith('/tokens ') and len(parts)>=3:
   await self.tokens.change(int(parts[1]),int(parts[2]),'ADMIN_ADD' if int(parts[2])>0 else 'ADMIN_REMOVE','Admin adjustment',earned=int(parts[2])>0,spent=int(parts[2])<0);return await m.reply_text('✅ Token adjustment logged.')
