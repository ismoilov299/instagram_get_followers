import sqlite3
import json
import asyncio
import random
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from bot.states import InstagramStates
from bot.keyboards import get_followers_keyboard, get_winner_keyboard, get_export_keyboard
from services.instagram_api import InstagramAPI

router = Router()

# Путь к файлу базы данных SQLite
DATABASE_PATH = "instagram_followers.db"

# Фиксированный Instagram username
FIXED_INSTAGRAM_USERNAME = "zayd.catlover"


# Функции для работы с базой данных SQLite
async def initialize_database():
    """Инициализация базы данных SQLite"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Создаем таблицу для хранения информации об аккаунтах
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        username TEXT PRIMARY KEY,
        followers_count INTEGER,
        full_name TEXT,
        following_count INTEGER,
        posts_count INTEGER,
        bio TEXT,
        update_timestamp INTEGER
    )
    ''')

    # Создаем таблицу для хранения подписчиков
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS followers (
        id TEXT,
        username TEXT,
        link TEXT,
        account_username TEXT,
        PRIMARY KEY (id, account_username),
        FOREIGN KEY (account_username) REFERENCES accounts (username)
    )
    ''')

    conn.commit()
    conn.close()


async def save_followers_to_db(user_info, followers_list):
    """Сохранить данные о подписчиках в базе данных SQLite"""
    username = user_info['username']
    followers_count = user_info['followers_count']

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Начинаем транзакцию
    conn.execute("BEGIN TRANSACTION")

    try:
        # Удаляем старые данные об аккаунте, если они есть
        cursor.execute("DELETE FROM accounts WHERE username = ?", (username,))

        # Вставляем новую информацию об аккаунте
        cursor.execute('''
        INSERT INTO accounts (username, followers_count, full_name, following_count, posts_count, bio, update_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            username,
            followers_count,
            user_info.get('full_name', ''),
            user_info.get('following_count', 0),
            user_info.get('posts_count', 0),
            user_info.get('bio', ''),
            int(asyncio.get_event_loop().time())
        ))

        # Удаляем старых подписчиков этого аккаунта
        cursor.execute("DELETE FROM followers WHERE account_username = ?", (username,))

        # Вставляем новых подписчиков
        for follower in followers_list:
            cursor.execute('''
            INSERT INTO followers (id, username, link, account_username)
            VALUES (?, ?, ?, ?)
            ''', (
                follower['id'],
                follower['username'],
                follower['link'],
                username
            ))

        # Завершаем транзакцию
        conn.commit()
        return True

    except Exception as e:
        # Откатываем транзакцию в случае ошибки
        conn.rollback()
        print(f"Ошибка при сохранении данных в базу: {e}")
        return False

    finally:
        conn.close()


async def get_account_info_from_db(username):
    """Получить информацию об аккаунте из базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
    SELECT username, followers_count, full_name, following_count, posts_count, bio, update_timestamp
    FROM accounts
    WHERE username = ?
    ''', (username,))

    result = cursor.fetchone()
    conn.close()

    if not result:
        return None

    return {
        'username': result[0],
        'followers_count': result[1],
        'full_name': result[2],
        'following_count': result[3],
        'posts_count': result[4],
        'bio': result[5],
        'update_timestamp': result[6]
    }


async def get_followers_from_db(username):
    """Получить список подписчиков аккаунта из базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
    SELECT id, username, link
    FROM followers
    WHERE account_username = ?
    ''', (username,))

    followers = []
    for row in cursor.fetchall():
        followers.append({
            'id': row[0],
            'username': row[1],
            'link': row[2]
        })

    conn.close()
    return followers


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, instagram_api: InstagramAPI):
    """
    Начало работы бота. Теперь сразу используется фиксированный пользователь.
    """
    # Инициализируем базу данных при первом запуске
    await initialize_database()

    # Показываем приветственное сообщение
    await message.answer(
        f"👋 Assalomu alaykum! Instagram follower bot'ga xush kelibsiz!\n\n"
        f"🔍 Bot faqat @{FIXED_INSTAGRAM_USERNAME} profilidan ma'lumot oladi."
    )

    # Передаем instagram_api в функцию
    await process_fixed_user(message, state, instagram_api)


@router.message(Command("followers"))
async def cmd_followers(message: Message, state: FSMContext, instagram_api: InstagramAPI):
    """
    Команда для повторного получения подписчиков
    """
    # Передаем instagram_api в функцию
    await process_fixed_user(message, state, instagram_api)


async def process_fixed_user(message: Message, state: FSMContext, instagram_api: InstagramAPI):
    """
    Обработка запроса для фиксированного пользователя

    Args:
        message: Сообщение от пользователя
        state: Контекст состояния бота
        instagram_api: API для работы с Instagram (обязательный параметр)
    """
    username = FIXED_INSTAGRAM_USERNAME

    # Показываем, что бот начал работу
    await message.answer(f"🔍 @{username} profili tekshirilmoqda...")

    # Получаем информацию о пользователе
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        user_info = await instagram_api.get_user_info(username)

        if not user_info:
            await message.answer(
                f"❌ '@{username}' foydalanuvchisi topilmadi yoki ma'lumotlarni olishda xatolik yuz berdi.\n"
                f"Iltimos, keyinroq qayta urinib ko'ring."
            )
            return

    except Exception as e:
        await message.answer(
            f"❌ API bilan bog'lanishda xatolik yuz berdi: {str(e)}\n"
            f"Iltimos, keyinroq qayta urinib ko'ring."
        )
        return

    # Сохраняем информацию о пользователе
    await state.update_data(instagram_user=user_info)

    # Проверяем, есть ли данные в базе
    db_user_info = await get_account_info_from_db(username)

    # Определяем, нужно ли обновлять данные
    need_update = False

    # Если данных нет в базе - нужно обновить
    if not db_user_info:
        need_update = True
    else:
        # Вычисляем разницу в количестве подписчиков
        followers_diff = abs(db_user_info['followers_count'] - user_info['followers_count'])

        # Обновляем только если разница ≥ 1000 подписчиков
        if followers_diff >= 1000:
            need_update = True

    # Если обновление не требуется, используем кэшированные данные
    if not need_update and db_user_info:
        # Показываем информацию о пользователе
        await message.answer(
            f"✅ Ma'lumotlar bazadan olindi!\n\n"
            f"👤 *{user_info['full_name']}* (@{user_info['username']})\n"
            f"📊 Statistika:\n"
            f"- Obunachilar: {user_info['followers_count']}\n"
            f"- Obuna bo'lganlar: {user_info['following_count']}\n"
            f"- Postlar: {user_info['posts_count']}\n\n"
            f"🔗 Link: https://www.instagram.com/{user_info['username']}\n\n",
            # f"🔄 Obunachilar soni 1000 tadan kam farq qilgani uchun, saqlab qo'yilgan ma'lumotlar ishlatilmoqda.\n"
            # f"Bazadagi obunachilar soni: {db_user_info['followers_count']}",
            parse_mode="Markdown"
        )

        # Загружаем подписчиков из базы данных
        followers_list = await get_followers_from_db(username)
        total_fetched = len(followers_list)

        # Сохраняем данные в состоянии
        await state.update_data(
            followers_list=followers_list,
            total_fetched=total_fetched,
            total_followers=db_user_info['followers_count']  # Используем количество из базы для согласованности
        )

        # Сразу предлагаем выбрать победителя
        await message.answer(
            "G'olibni aniqlash uchun tugmani bosing:",
            reply_markup=get_winner_keyboard()
        )
    else:
        # Если нужно обновление или данных нет в базе

        # Если есть данные в базе, показываем сообщение о причине обновления
        if db_user_info:
            followers_diff = abs(db_user_info['followers_count'] - user_info['followers_count'])
            await message.answer(
                f"🔄 Obunachilar soni {followers_diff} ta o'zgargan, yangi ma'lumotlar yuklanmoqda...",
                parse_mode="Markdown"
            )

        # Показываем информацию о пользователе и начинаем загрузку подписчиков
        await message.answer(
            f"✅ Ma'lumotlar topildi!\n\n"
            f"👤 *{user_info['full_name']}* (@{user_info['username']})\n"
            f"📊 Statistika:\n"
            f"- Obunachilar: {user_info['followers_count']}\n"
            f"- Obuna bo'lganlar: {user_info['following_count']}\n"
            f"- Postlar: {user_info['posts_count']}\n\n"
            f"🔗 Link: https://www.instagram.com/{user_info['username']}\n\n"
            f"Obunachilarni yuklash boshlanmoqda...",
            parse_mode="Markdown"
        )

        # Запускаем загрузку подписчиков
        status_message = await message.answer("🔄 Obunachilar yuklanmoqda... 0/0")

        # Подготавливаем данные для загрузки
        await state.update_data(
            current_user_id=user_info['id'],
            followers_list=[],
            next_max_id=None,
            total_fetched=0,
            total_followers=user_info['followers_count'],
            status_message_id=status_message.message_id
        )

        # Запускаем загрузку подписчиков
        await fetch_all_followers(message, state, instagram_api)


@router.callback_query(F.data == "select_winner")
async def select_winner(callback: CallbackQuery, state: FSMContext):
    """
    Randomly select ONE winner from the followers list
    """
    await callback.answer("🎲 G'olib tanlanmoqda...")

    # Get the followers list from state
    data = await state.get_data()
    followers_list = data.get('followers_list', [])
    total_fetched = data.get('total_fetched', 0)

    if not followers_list:
        await callback.message.answer("❌ G'olibni aniqlash uchun obunachilar ro'yxati mavjud emas!")
        return

    # Create some suspense with typing action and delay
    await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")
    await asyncio.sleep(1.5)

    # Select a random winner - ONLY ONE
    winner = random.choice(followers_list)
    winner_index = followers_list.index(winner) + 1

    # Используем разные тексты для каждого обновления анимации
    dots_message = await callback.message.answer("🎲 G'olib tanlanmoqda...")

    # Анимированные точки для интриги, с разными текстами
    animation_texts = [
        "🎲 G'olib tanlanmoqda...",
        "🎲 G'olib hisoblanmoqda...",
        "🎲 Natijalar tayyorlanmoqda..."
    ]

    for text in animation_texts:
        await asyncio.sleep(0.7)
        try:
            await dots_message.edit_text(text)
        except Exception as e:
            print(f"Ошибка при обновлении анимации: {e}")
            # Продолжаем выполнение даже при ошибке
            continue

    await asyncio.sleep(0.7)

    # Final winner announcement
    winner_text = (
        f"🎉 *G'OLIB ANIQLANDI!* 🎉\n\n"
        f"🏆 G'olib: [{winner['username']}]({winner['link']})\n"
        f"🔢 G'olibning tartib raqami: {winner_index} / {total_fetched}\n\n"
        f"Tabriklaymiz! 🎊"
    )

    # Delete the dots message and send the winner announcement
    try:
        await dots_message.delete()
    except Exception:
        pass  # Игнорируем ошибку, если сообщение уже удалено

    # Send winner with confetti animation effect
    await callback.message.answer(
        winner_text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    # Allow selecting another winner
    await callback.message.answer(
        "Boshqa g'olibni aniqlash uchun tugmani bosing:",
        reply_markup=get_winner_keyboard()
    )


async def fetch_all_followers(message: Message, state: FSMContext, instagram_api: InstagramAPI):
    """
    Автоматическая загрузка всех подписчиков с сохранением в базу данных SQLite
    """
    data = await state.get_data()
    user_id = data.get('current_user_id')
    status_message_id = data.get('status_message_id')
    total_followers = data.get('total_followers')
    user_info = data.get('instagram_user')

    followers_list = []
    next_max_id = None
    total_fetched = 0
    last_status_text = ""

    # Увеличим размер партии для более быстрой загрузки
    batch_size = 100

    # Начальное сообщение для пользователя
    await safe_edit_message(
        message.bot,
        message.chat.id,
        status_message_id,
        f"🔄 Obunachilar yuklanmoqda... 0/{total_followers} (0%)"
    )

    # Функция безопасного обновления сообщения
    async def update_status_safely(text):
        nonlocal last_status_text

        if text == last_status_text:
            return

        last_status_text = text

        await safe_edit_message(
            message.bot,
            message.chat.id,
            status_message_id,
            text
        )

    # Начинаем загрузку
    while total_fetched < total_followers:
        # Показываем активность
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        try:
            # Получаем следующую партию подписчиков
            batch_result = await instagram_api.get_user_followers_batch(
                user_id=user_id,
                count=batch_size,
                max_id=next_max_id
            )

            # Проверяем результат
            if not batch_result or not batch_result.get('followers'):
                await message.answer("⚠️ Obunachilarni yuklashda xatolik yuz berdi yoki API cheklovlar qo'yilgan.")
                break

            # Добавляем подписчиков в список
            new_followers = batch_result.get('followers', [])
            followers_list.extend(new_followers)

            # Обновляем счетчики
            total_fetched = len(followers_list)
            next_max_id = batch_result.get('next_max_id')

            # Обновляем статус
            percentage = min(100, int((total_fetched / total_followers) * 100))
            await update_status_safely(
                f"🔄 Obunachilar yuklanmoqda... {total_fetched}/{total_followers} ({percentage}%)")

            # Если больше нет подписчиков, завершаем
            if not next_max_id or not new_followers:
                break

            # Добавляем задержку для избежания блокировки API
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"Error fetching followers: {e}")
            await asyncio.sleep(2)
            continue

    # Сохраняем результаты в состоянии
    await state.update_data(
        followers_list=followers_list,
        total_fetched=total_fetched
    )

    # Сохраняем данные в базе SQLite
    if user_info and followers_list:
        await save_followers_to_db(user_info, followers_list)

    # Показываем итоговый статус
    final_percentage = min(100, int((total_fetched / total_followers) * 100))
    await update_status_safely(f"✅ Obunachilar yuklandi: {total_fetched}/{total_followers} ({final_percentage}%)")

    # Предлагаем выбрать победителя
    if followers_list:
        await message.answer(
            "G'olibni aniqlash uchun tugmani bosing:",
            reply_markup=get_winner_keyboard()
        )
    else:
        await message.answer("❌ Obunachilar ro'yxatini olib bo'lmadi. Iltimos, keyinroq qayta urinib ko'ring.")


@router.callback_query(F.data == "export_excel")
async def export_to_excel(callback: CallbackQuery, state: FSMContext):
    """
    Export followers list to Excel file
    """
    await callback.answer("📊 Excel fayl tayyorlanmoqda...")

    # Get the followers list from state
    data = await state.get_data()
    followers_list = data.get('followers_list', [])
    total_fetched = data.get('total_fetched', 0)

    if not followers_list:
        await callback.message.answer("❌ Eksport qilish uchun obunachilar ro'yxati mavjud emas!")
        return

    # Show typing action to indicate processing
    await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action="upload_document")

    # Create Excel file in memory
    excel_file = await create_excel_file(followers_list, FIXED_INSTAGRAM_USERNAME)

    # Send the file to user
    await callback.message.answer_document(
        FSInputFile(
            excel_file,
            filename=f"{FIXED_INSTAGRAM_USERNAME}_followers.xlsx"
        ),
        caption=f"📊 {FIXED_INSTAGRAM_USERNAME} uchun {total_fetched} ta obunachi ma'lumotlari."
    )

    # Allow selecting a winner
    await callback.message.answer(
        "🎲 G'olibni aniqlash uchun tugmani bosing:",
        reply_markup=get_winner_keyboard()
    )


async def create_excel_file(followers_list, account_username):
    """
    Create Excel file with followers data
    """
    # Create a workbook and select active worksheet
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Obunachilar"

    # Define header style
    header_font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')

    # Add headers
    headers = ["№", "Username", "Instagram Link", "ID"]
    for col_num, header in enumerate(headers, 1):
        cell = worksheet.cell(row=1, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    # Add data
    for row_num, follower in enumerate(followers_list, 2):
        worksheet.cell(row=row_num, column=1).value = row_num - 1  # № (counter)
        worksheet.cell(row=row_num, column=2).value = follower['username']
        worksheet.cell(row=row_num, column=3).value = follower['link']
        worksheet.cell(row=row_num, column=4).value = follower['id']

    # Auto-adjust column width
    for column_cells in worksheet.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = length + 5

    # Save to in-memory file
    file_path = f"temp_{account_username}_followers.xlsx"
    workbook.save(file_path)

    return file_path


async def safe_edit_message(bot, chat_id, message_id, text, **kwargs):
    """
    Безопасно обновляет сообщение, игнорируя ошибки "message is not modified"
    """
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            **kwargs
        )
        return True
    except Exception as e:
        # Игнорируем ошибку "message is not modified"
        if "message is not modified" in str(e).lower():
            return True  # Сообщение уже содержит нужный текст

        # Для других ошибок просто логируем и продолжаем
        print(f"Ошибка при обновлении сообщения: {e}")
        return False