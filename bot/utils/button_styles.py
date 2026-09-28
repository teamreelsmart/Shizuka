"""Optional Pyrofork ButtonStyle compatibility probe, isolated from production UI."""
def test_keyboard():
    try:
        from pyrogram.enums import ButtonStyle
        from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton('PRIMARY (blue)', callback_data='style:test:primary', style=ButtonStyle.PRIMARY),
            InlineKeyboardButton('SUCCESS (green)', callback_data='style:test:success', style=ButtonStyle.SUCCESS),
            InlineKeyboardButton('DANGER (red)', callback_data='style:test:danger', style=ButtonStyle.DANGER),
        ]])
    except (ImportError, AttributeError, TypeError) as exc:
        return None, str(exc)
    return keyboard, None
