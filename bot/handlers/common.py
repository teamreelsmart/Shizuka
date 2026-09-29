import logging
from pyrogram import filters
from pyrogram.errors import MessageNotModified
log=logging.getLogger(__name__)
def register_common(app,svc):
 async def report(context, event, error):
  user_id=getattr(getattr(event,'from_user',None),'id',None)
  data=getattr(event,'data',None)
  log.exception('%s failed user_id=%s data=%s',context,user_id,data)
  await svc.notify_admins(context,error,user_id=user_id,callback_data=data)
  try:
   if data is not None: await event.answer('❌ Something went wrong. The admin has been notified.',show_alert=True)
   else: await event.reply_text('❌ Something went wrong. The admin has been notified.')
  except Exception: log.exception('could not send error response user_id=%s',user_id)
 @app.on_callback_query()
 async def callback(_,q):
  await q.answer()
  try: await svc.callback(q)
  except MessageNotModified: pass
  except Exception as exc: await report('callback',q,exc)
 @app.on_message(filters.command('start'))
 async def start(_,m):
  try:await svc.start(m)
  except Exception as exc:await report('start command',m,exc)
 @app.on_message(filters.command('checkin'))
 async def checkin(_,m):
  try:await svc.checkin(m)
  except Exception as exc:await report('checkin command',m,exc)
 @app.on_message(filters.command('admin'))
 async def admin(_,m):
  try:await svc.admin(m)
  except Exception as exc:await report('admin command',m,exc)
 @app.on_message(filters.private & ~filters.command(['start','checkin','admin']))
 async def input_(_,m):
  try:await svc.input(m)
  except Exception as exc:await report('input handler',m,exc)
