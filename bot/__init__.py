# bot/__init__.py

# Bu fayl asosan importlar bilan ishlashni osonlashtiradi
# Va bot modulidan boshqa fayllarda oson import qilish imkonini beradi

# Handler va boshqa fayllarni ko'rsatish
from bot.states import InstagramStates
from bot.keyboards import get_followers_keyboard

# Bu fayl bo'sh bo'lishi ham mumkin, lekin asosiy
# modullarni shunday ko'rsatish loyiha tashkilotini osonlashtiradi