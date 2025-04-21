from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_followers_keyboard(user_id: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📋 Obunachilarni ko'rish", callback_data=f"followers_{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)