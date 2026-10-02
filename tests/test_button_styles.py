import sys
import types
from enum import Enum

class ButtonStyle(Enum):
    PRIMARY = 'primary'
    SUCCESS = 'success'
    DANGER = 'danger'
class Button:
    def __init__(self, text, **kwargs): self.kwargs = {'text': text, **kwargs}
class Markup:
    def __init__(self, rows): self.rows = rows
sys.modules['pyrogram'] = types.ModuleType('pyrogram')
sys.modules['pyrogram.enums'] = types.SimpleNamespace(ButtonStyle=ButtonStyle)
sys.modules['pyrogram.types'] = types.SimpleNamespace(InlineKeyboardButton=Button, InlineKeyboardMarkup=Markup)
from bot.utils.button_styles import test_keyboard
keyboard, error = test_keyboard()
assert error is None
assert [button.kwargs['style'] for button in keyboard.rows[0]] == [ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER]
