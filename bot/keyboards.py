from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_followers_keyboard(user_id: str, followers_count: int) -> InlineKeyboardMarkup:
    """
    Create a keyboard with a button to view followers.
    Now includes the followers count in the callback data.

    Args:
        user_id: Instagram user ID
        followers_count: Total number of followers

    Returns:
        InlineKeyboardMarkup: Keyboard with followers button
    """
    keyboard = [
        [InlineKeyboardButton(
            text="📋 Obunachilarni ko'rish",
            callback_data=f"followers_{user_id}_{followers_count}"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)