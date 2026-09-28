from pyrogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as K
def menu():return K([[B('▶️ Start Watching','menu:start')],[B('📂 Categories','menu:categories'),B('💰 Earn Tokens','menu:earn')],[B('👤 Profile','menu:profile'),B('📖 Help Guide','menu:help')]])
def back():return K([[B('🏠 Main Menu','menu:home')]])
def profile():return K([[B('📦 Unlocked Collections','vault:unlocked:0'),B('🔖 Saved Collections','vault:saved:0')],[B('💰 Earn Tokens','menu:earn'),B('👥 Refer Friends','menu:refer')],[B('▶️ Start Watching','menu:start'),B('🏠 Main Menu','menu:home')]])
def categories(rows):return K(rows+[[B('▶️ Start Watching','menu:start'),B('🏠 Main Menu','menu:home')]])
def card(cid,saved=False):return K([[B('◀️ Previous',f'nav:prev:{cid}'),B('🔓 Unlock',f'col:unlock:{cid}'),B('▶️ Next',f'nav:next:{cid}')],[B('❌ Unsave' if saved else '🔖 Save',f'col:save:{cid}')],[B('📂 Categories','menu:categories'),B('🏠 Main Menu','menu:home')]])
def pager(prefix,page,pages):return [B('◀️',f'{prefix}:{page-1}') if page else B('·','noop'),B(f'Page {page+1}/{pages}','noop'),B('▶️',f'{prefix}:{page+1}') if page+1<pages else B('·','noop')]
