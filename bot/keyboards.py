from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_followers_keyboard(user_id: str, followers_count: int) -> InlineKeyboardMarkup:
    """
    Create a keyboard with a button to view followers.
    Includes the followers count in the callback data.

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


def get_winner_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with a button to select a random winner.

    Returns:
        InlineKeyboardMarkup: Keyboard with winner selection button
    """
    keyboard = [
        [InlineKeyboardButton(
            text="🎲 G'olibni aniqlash",
            callback_data="select_winner"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_export_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with buttons for exporting to Excel and selecting a winner.

    Returns:
        InlineKeyboardMarkup: Keyboard with export and winner buttons
    """
    keyboard = [
        [InlineKeyboardButton(
            text="📊 Excel formatida yuklash",
            callback_data="export_excel"
        )],
        [InlineKeyboardButton(
            text="🎲 G'olibni aniqlash",
            callback_data="select_winner"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)