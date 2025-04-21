from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

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

    keyboard = get_followers_keyboard(user_info['id'])
    await message.answer("Tanlang:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("followers_"))
async def process_followers_button(callback: CallbackQuery, instagram_api: InstagramAPI, config):
    await callback.answer()

    user_id = callback.data.split("_")[1]

    await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")

    followers = await instagram_api.get_user_followers(user_id, config.instagram.follower_count)

    if not followers:
        await callback.message.answer("❌ Obunachilarni olishda xatolik yuz berdi!")
        return

    followers_text = "📋 *Obunachilar ro'yxati:*\n\n"

    for i, follower in enumerate(followers, 1):
        followers_text += f"{i}. [{follower['username']}]({follower['link']})\n"

    followers_text += f"\n*Jami ko'rsatilgan:* {len(followers)} ta obunachi."

    await callback.message.answer(
        followers_text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


@router.message()
async def unknown_command(message: Message):
    await message.answer(
        "❓ Noma'lum buyruq. Instagram foydalanuvchi nomini kiriting yoki /start buyrug'ini ishga tushiring."
    )