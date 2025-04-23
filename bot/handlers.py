from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
import asyncio

from bot.states import InstagramStates
from bot.keyboards import get_followers_keyboard
from services.instagram_api import InstagramAPI

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "👋 Assalomu alaykum! Instagram follower bot'ga xush kelibsiz!\n\n"
        "Qidirish uchun Instagram foydalanuvchi nomini (username) kiriting:"
    )
    await state.set_state(InstagramStates.waiting_username)


@router.message(StateFilter(InstagramStates.waiting_username), ~F.text.startswith('/'))
async def process_username(message: Message, state: FSMContext, instagram_api: InstagramAPI):
    username = message.text.strip().lower()

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    user_info = await instagram_api.get_user_info(username)

    if not user_info:
        await message.answer(
            f"❌ '{username}' foydalanuvchisi topilmadi yoki ma'lumotlarni olishda xatolik yuz berdi.\n"
            f"Boshqa foydalanuvchi nomini kiriting yoki /start buyrug'ini qayta ishga tushiring."
        )
        return

    await state.update_data(instagram_user=user_info)

    await message.answer(
        f"✅ Ma'lumotlar topildi!\n\n"
        f"👤 *{user_info['full_name']}* (@{user_info['username']})\n"
        f"📊 Statistika:\n"
        f"- Obunachilar: {user_info['followers_count']}\n"
        f"- Obuna bo'lganlar: {user_info['following_count']}\n"
        f"- Postlar: {user_info['posts_count']}\n\n"
        f"📝 Bio: {user_info['bio']}\n\n"
        f"🔗 Link: https://www.instagram.com/{user_info['username']}\n\n"
        f"Obunachilarni ko'rish uchun quyidagi tugmani bosing:",
        parse_mode="Markdown"
    )

    keyboard = get_followers_keyboard(user_info['id'], user_info['followers_count'])
    await message.answer("Tanlang:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("followers_"))
async def process_followers_button(callback: CallbackQuery, state: FSMContext, instagram_api: InstagramAPI):
    # Parse data from callback
    callback_data = callback.data.split("_")
    user_id = callback_data[1]
    total_followers = int(callback_data[2])

    await callback.answer(f"🔄 {total_followers} ta obunachi yuklanmoqda...")

    # Initialize the follower collection process
    await state.update_data(
        current_user_id=user_id,
        followers_list=[],
        next_max_id=None,
        total_fetched=0,
        total_followers=total_followers
    )

    # Initial message to show progress
    status_message = await callback.message.answer(f"🔄 Obunachilar yuklanmoqda... 0/{total_followers}")

    # Store the status message ID for updating later
    await state.update_data(status_message_id=status_message.message_id)

    # Start the automatic fetching process
    await fetch_all_followers(callback.message, state, instagram_api)


async def fetch_all_followers(message: Message, state: FSMContext, instagram_api: InstagramAPI):
    """
    Automatically fetch all followers as indicated by the profile's follower count
    """
    data = await state.get_data()
    user_id = data.get('current_user_id')
    status_message_id = data.get('status_message_id')
    total_followers = data.get('total_followers')

    followers_list = []
    next_max_id = None
    total_fetched = 0

    # Determine update frequency based on total followers count
    if total_followers <= 200:
        update_frequency = 1  # Update after each batch for small accounts
    elif total_followers <= 1000:
        update_frequency = 3  # Every 3 batches (150 followers) for medium accounts
    else:
        update_frequency = 10  # Every 10 batches (500 followers) for large accounts

    batch_count = 0
    batch_size = 50  # API batch size

    while total_fetched < total_followers:
        # Show typing action
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        try:
            # Fetch next batch
            batch_result = await instagram_api.get_user_followers_batch(
                user_id=user_id,
                count=batch_size,
                max_id=next_max_id
            )

            # Check for errors or empty results
            if not batch_result or not batch_result.get('followers'):
                await message.answer("⚠️ Obunachilarni yuklashda xatolik yuz berdi yoki API cheklovlar qo'yilgan.")
                break

            # Add new followers to the list
            new_followers = batch_result.get('followers', [])
            followers_list.extend(new_followers)

            # Update counters
            total_fetched = len(followers_list)
            next_max_id = batch_result.get('next_max_id')
            batch_count += 1

            # Update status message periodically
            if batch_count % update_frequency == 0 or total_fetched >= total_followers or not next_max_id:
                # Calculate percentage
                percentage = min(100, int((total_fetched / total_followers) * 100))

                await message.bot.edit_message_text(
                    f"🔄 Obunachilar yuklanmoqda... {total_fetched}/{total_followers} ({percentage}%)",
                    chat_id=message.chat.id,
                    message_id=status_message_id
                )

            # Stop if there are no more followers to fetch
            if not next_max_id or not new_followers:
                break

            # Add a small delay to avoid hitting rate limits (important for large accounts)
            if total_followers > 1000:
                await asyncio.sleep(0.5)

        except Exception as e:
            # Log error and try to continue if possible
            print(f"Error fetching followers: {e}")
            await asyncio.sleep(2)  # Larger delay if error occurred
            continue

    # Save final followers list to state
    await state.update_data(
        followers_list=followers_list,
        total_fetched=total_fetched
    )

    # Show completion message
    final_percentage = min(100, int((total_fetched / total_followers) * 100))
    await message.bot.edit_message_text(
        f"✅ Obunachilar yuklandi: {total_fetched}/{total_followers} ({final_percentage}%)",
        chat_id=message.chat.id,
        message_id=status_message_id
    )

    # If we got at least some followers, display them
    if followers_list:
        await send_followers_in_batches(message, followers_list)
    else:
        await message.answer("❌ Obunachilar ro'yxatini olib bo'lmadi. Iltimos, keyinroq qayta urinib ko'ring.")


async def send_followers_in_batches(message: Message, followers_list: list):
    """
    Send the followers list in batches to avoid message size limits
    """
    # Telegram message size limit is approximately 4096 characters
    # We need to make smaller batches to stay within this limit

    total_followers = len(followers_list)

    # Reduce batch size to avoid exceeding message limit
    # Each follower entry takes approximately 50-70 characters
    # So we limit to smaller numbers per message
    if total_followers <= 200:
        display_batch_size = 50  # Reduced from 100
    elif total_followers <= 1000:
        display_batch_size = 40  # Reduced from 200
    else:
        display_batch_size = 30  # Reduced from 300

    total_batches = (total_followers + display_batch_size - 1) // display_batch_size

    for i in range(0, total_followers, display_batch_size):
        batch = followers_list[i:i + display_batch_size]
        batch_num = (i // display_batch_size) + 1

        followers_text = f"📋 *Obunachilar ro'yxati (Qism {batch_num}/{total_batches}):*\n\n"

        # Build message with length checking
        for idx, follower in enumerate(batch, i + 1):
            line = f"{idx}. [{follower['username']}]({follower['link']})\n"

            # Check if adding this line would exceed Telegram's limit
            if len(followers_text + line) >= 3800:  # Leave buffer for final message
                followers_text += "\n⚠️ *Xabar hajmi chegarasi sababli qolgan obunachilar keyingi xabarda.*"
                break

            followers_text += line

        # Add completion message to the last batch
        if i + display_batch_size >= total_followers and len(followers_text) < 3900:
            followers_text += f"\n✅ *Barchasi yuklandi:* {total_followers} ta obunachi."

        try:
            await message.answer(
                followers_text,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        except Exception as e:
            # If message still too long, send error and try with even smaller batch
            print(f"Error sending message: {e}")
            await message.answer(
                f"⚠️ Obunachilar ro'yxati juda uzun. {batch_num}-qism yuborishda muammo yuzaga keldi.",
                parse_mode="Markdown"
            )

        # Add a small delay between message batches
        if batch_num < total_batches:
            await asyncio.sleep(0.5)


@router.message()
async def unknown_command(message: Message):
    await message.answer(
        "❓ Noma'lum buyruq. Instagram foydalanuvchi nomini kiriting yoki /start buyrug'ini ishga tushiring."
    )