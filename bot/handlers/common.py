import logging
from pyrogram import filters
from pyrogram.errors import MessageNotModified
log=logging.getLogger(__name__)
def register_common(app,svc):
 @app.on_callback_query()
 async def callback(_,q):
  await q.answer()
  try: await svc.callback(q)
  except MessageNotModified: pass
  except Exception: log.exception('callback failed user_id=%s data=%s',q.from_user.id,q.data)
 @app.on_message(filters.command('start'))
 async def start(_,m): await svc.start(m)
 @app.on_message(filters.command('checkin'))
 async def checkin(_,m): await svc.checkin(m)
 @app.on_message(filters.command('admin'))
 async def admin(_,m): await svc.admin(m)
 @app.on_message(filters.private & ~filters.command(['start','checkin','admin']))
 async def input_(_,m): await svc.input(m)
