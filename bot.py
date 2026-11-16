
import asyncio
import logging
import os
import ast
import time
import aiosqlite

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ==========================================
# ♛ FARID ACADEMY — BLACK GOLD
# ==========================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB = "mock_test.db"
MAX_QUESTIONS = 200
TEST_TIME = 7200

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher(storage=MemoryStorage())


# ==========================================
# HOLATLAR
# ==========================================

class MockState(StatesGroup):
    name = State()
    media = State()
    question_count = State()
    answer_key = State()


# ==========================================
# BLACK GOLD MENYULAR
# ==========================================

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="♛  MOCK QO'SHISH")],
        [KeyboardButton(text="📚  MOCKLAR RO'YXATI")],
        [KeyboardButton(text="👥  O'QUVCHILAR")],
        [KeyboardButton(text="📊  STATISTIKA")],
        [KeyboardButton(text="🏠  ASOSIY MENYU")],
    ],
    resize_keyboard=True
)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚  MOCK TESTLAR")],
        [KeyboardButton(text="👤  SHAXSIY KABINET")],
        [KeyboardButton(text="🏆  REYTING")],
        [KeyboardButton(text="ℹ️  YORDAM")],
    ],
    resize_keyboard=True
)


def is_admin(user_id):
    return user_id == ADMIN_ID


def academy_header():
    return (
        "♛ **FARID ACADEMY**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "       PREMIUM EDUCATION\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


# ==========================================
# DATABASE
# ==========================================

async def init_db():
    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS mocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                media TEXT,
                answer_key TEXT,
                active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mock_id INTEGER,
                answers TEXT DEFAULT '',
                score INTEGER DEFAULT 0,
                finished INTEGER DEFAULT 0,
                started_at INTEGER DEFAULT 0
            )
        """)

        cursor = await db.execute("PRAGMA table_info(attempts)")
        columns = {row[1] for row in await cursor.fetchall()}

        required = {
            "user_id": "INTEGER DEFAULT 0",
            "mock_id": "INTEGER DEFAULT 0",
            "answers": "TEXT DEFAULT ''",
            "score": "INTEGER DEFAULT 0",
            "finished": "INTEGER DEFAULT 0",
            "started_at": "INTEGER DEFAULT 0",
        }

        for column, definition in required.items():
            if column not in columns:
                await db.execute(
                    f"ALTER TABLE attempts ADD COLUMN {column} {definition}"
                )

        await db.commit()

    print("Database tayyor!")


async def get_mock(mock_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT id, name, media, answer_key, active FROM mocks WHERE id=?",
            (mock_id,)
        )
        return await cursor.fetchone()


async def get_attempt(attempt_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, mock_id, answers,
                   score, finished, started_at
            FROM attempts WHERE id=?
            """,
            (attempt_id,)
        )
        return await cursor.fetchone()


# ==========================================
# TEST TUGMALARI
# ==========================================

def make_test_keyboard(attempt_id, question_no, total):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🅰️ A",
                    callback_data=f"ans:{attempt_id}:{question_no}:A"
                ),
                InlineKeyboardButton(
                    text="🅱️ B",
                    callback_data=f"ans:{attempt_id}:{question_no}:B"
                ),
                InlineKeyboardButton(
                    text="©️ C",
                    callback_data=f"ans:{attempt_id}:{question_no}:C"
                ),
                InlineKeyboardButton(
                    text="🇩 D",
                    callback_data=f"ans:{attempt_id}:{question_no}:D"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ OLDINGI",
                    callback_data=f"nav:{attempt_id}:{question_no-1}"
                ),
                InlineKeyboardButton(
                    text="KEYINGI ➡️",
                    callback_data=f"nav:{attempt_id}:{question_no+1}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏁 TESTNI YAKUNLASH",
                    callback_data=f"finish:{attempt_id}"
                )
            ]
        ]
    )


# ==========================================
# SAVOLNI KO'RSATISH
# ==========================================

async def show_question(target, attempt_id, question_no):

    attempt = await get_attempt(attempt_id)

    if not attempt:
        return

    _, user_id, mock_id, answers, score, finished, started_at = attempt

    if finished:
        return

    mock = await get_mock(mock_id)

    if not mock or not mock[4]:
        return

    answer_key = mock[3]
    total = len(answer_key)

    if total == 0:
        return

    if started_at and time.time() - started_at >= TEST_TIME:
        result = await result_text(attempt_id, user_id)

        if isinstance(target, CallbackQuery):
            await target.message.edit_text(
                result,
                parse_mode="Markdown"
            )
        else:
            await target.answer(result, parse_mode="Markdown")
        return

    question_no = max(1, min(question_no, total))

    answers = (answers or "").ljust(total, "-")[:total]
    selected = answers[question_no - 1]

    text = (
        academy_header()
        + f"📘 **{mock[1]}**\n\n"
        + "━━━━━━━━━━━━━━━━━━\n"
        + f"📌 **SAVOL:** {question_no}/{total}\n"
        + f"✍️ **JAVOB:** {selected if selected != '-' else 'Belgilanmagan'}\n"
        + "━━━━━━━━━━━━━━━━━━\n\n"
        + "Javob variantini tanlang:"
    )

    keyboard = make_test_keyboard(
        attempt_id,
        question_no,
        total
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await target.answer(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


# ==========================================
# TESTNI YAKUNLASH
# ==========================================

async def finish_attempt(attempt_id, user_id):

    attempt = await get_attempt(attempt_id)

    if not attempt:
        return None

    _, owner_id, mock_id, answers, score, finished, started_at = attempt

    if owner_id != user_id or finished:
        return None

    mock = await get_mock(mock_id)

    if not mock:
        return None

    answer_key = mock[3]
    total = len(answer_key)

    answers = (answers or "").ljust(total, "-")[:total]

    correct = sum(
        1 for a, b in zip(answers, answer_key)
        if a == b
    )

    percent = round(correct / total * 100) if total else 0

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """
            UPDATE attempts
            SET answers=?, score=?, finished=1
            WHERE id=?
            """,
            (answers, correct, attempt_id)
        )
        await db.commit()

    return correct, total, percent, mock[1]


async def result_text(attempt_id, user_id):

    result = await finish_attempt(attempt_id, user_id)

    if not result:
        return "Test yakunlangan yoki topilmadi."

    correct, total, percent, name = result

    return (
        academy_header()
        + "🏁 **TEST YAKUNLANDI!**\n\n"
        + f"📘 Mock: {name}\n"
        + "━━━━━━━━━━━━━━━━━━\n"
        + f"✅ To'g'ri javoblar: {correct}/{total}\n"
        + f"📊 Natija: {percent}%\n"
        + "━━━━━━━━━━━━━━━━━━"
    )


# ==========================================
# START
# ==========================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    await state.clear()

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO users(user_id, username)
            VALUES(?, ?)
            """,
            (
                message.from_user.id,
                message.from_user.username or ""
            )
        )
        await db.commit()

    if is_admin(message.from_user.id):
        await message.answer(
            academy_header()
            + "👑 **ADMIN PANELGA XUSH KELIBSIZ!**\n\n"
            + "Platformani boshqarish uchun bo'limni tanlang.",
            reply_markup=admin_menu,
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            academy_header()
            + "🎓 **XUSH KELIBSIZ!**\n\n"
            + "Bilimingizni sinab ko'ring va natijangizni yaxshilang.\n\n"
            + "Kerakli bo'limni tanlang:",
            reply_markup=main_menu,
            parse_mode="Markdown"
        )


@dp.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext):

    if not is_admin(message.from_user.id):
        return

    await state.clear()

    await message.answer(
        "❎ Amal bekor qilindi.",
        reply_markup=admin_menu
    )


@dp.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):

    if not is_admin(message.from_user.id):
        return

    await state.clear()

    await message.answer(
        academy_header() + "👑 **ADMIN PANEL**",
        reply_markup=admin_menu,
        parse_mode="Markdown"
    )


# ==========================================
# MOCK QO'SHISH
# ==========================================

@dp.message(F.text == "♛  MOCK QO'SHISH")
async def add_mock(message: Message, state: FSMContext):

    if not is_admin(message.from_user.id):
        return

    await state.clear()
    await state.set_state(MockState.name)

    await message.answer(
        academy_header()
        + "➕ **YANGI MOCK QO'SHISH**\n\n"
        + "Mock nomini yuboring:",
        parse_mode="Markdown"
    )


@dp.message(MockState.name)
async def mock_name(message: Message, state: FSMContext):

    name = (message.text or "").strip()

    if not name:
        await message.answer("Mock nomini matn ko'rinishida yuboring.")
        return

    await state.update_data(
        name=name,
        media=[]
    )

    await state.set_state(MockState.media)

    await message.answer(
        "📄 PDF yoki rasmlarni yuboring.\n\n"
        "Barcha fayllardan keyin /done yozing.\n"
        "Bekor qilish uchun /cancel."
    )


@dp.message(MockState.media, Command("done"))
async def media_done(message: Message, state: FSMContext):

    data = await state.get_data()
    media = data.get("media", [])

    if not media:
        await message.answer("Avval PDF yoki rasm yuboring.")
        return

    await state.set_state(MockState.question_count)

    await message.answer(
        f"📄 Fayllar: {len(media)} ta.\n\n"
        "Bu mockda nechta savol bor?\n"
        "Masalan: 30"
    )


@dp.message(MockState.media)
async def receive_media(message: Message, state: FSMContext):

    file_id = None
    file_type = None

    if message.document:
        file_id = message.document.file_id
        file_type = "document"

    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"

    else:
        await message.answer("PDF yoki rasm yuboring.")
        return

    data = await state.get_data()
    media = data.get("media", [])

    media.append({
        "type": file_type,
        "file_id": file_id
    })

    await state.update_data(media=media)

    await message.answer(
        f"✅ Fayl qabul qilindi. Jami: {len(media)} ta.\n"
        "Yana yuboring yoki /done yozing."
    )


@dp.message(MockState.question_count)
async def get_question_count(message: Message, state: FSMContext):

    value = (message.text or "").strip()

    if not value.isdigit():
        await message.answer("Faqat son yuboring. Masalan: 30")
        return

    count = int(value)

    if not 1 <= count <= MAX_QUESTIONS:
        await message.answer("Savollar soni 1 dan 200 gacha bo'lishi kerak.")
        return

    await state.update_data(question_count=count)
    await state.set_state(MockState.answer_key)

    await message.answer(
        f"Endi {count} ta savolning javob kalitini yuboring.\n\n"
        "Masalan: ABCDABCD\n\n"
        "Faqat A, B, C, D harflari."
    )


@dp.message(MockState.answer_key)
async def save_mock(message: Message, state: FSMContext):

    key = "".join(
        (message.text or "").upper().split()
    )

    data = await state.get_data()
    count = data.get("question_count", 0)

    if len(key) != count:
        await message.answer(
            f"❌ Kerakli harflar soni: {count}\n"
            f"Siz yuborgan harflar: {len(key)}"
        )
        return

    if any(letter not in "ABCD" for letter in key):
        await message.answer("Faqat A, B, C, D harflaridan foydalaning.")
        return

    name = data["name"]
    media = data["media"]

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """
            INSERT INTO mocks(name, media, answer_key, active)
            VALUES(?, ?, ?, 1)
            """,
            (name, str(media), key)
        )
        await db.commit()

    await state.clear()

    await message.answer(
        academy_header()
        + "✅ **MOCK SAQLANDI!**\n\n"
        + f"📘 Nomi: {name}\n"
        + f"📄 Fayllar: {len(media)} ta\n"
        + f"📝 Savollar: {count} ta",
        reply_markup=admin_menu,
        parse_mode="Markdown"
    )


# ==========================================
# MOCKLAR RO'YXATI
# ==========================================

@dp.message(F.text == "📚  MOCKLAR RO'YXATI")
async def mock_list(message: Message):

    if not is_admin(message.from_user.id):
        return

    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT id, name, answer_key, active
            FROM mocks ORDER BY id DESC
            """
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Hozircha mocklar yo'q.")
        return

    text = academy_header() + "📚 **MOCKLAR RO'YXATI**\n\n"

    for mock_id, name, key, active in rows:
        status = "🟢 Faol" if active else "🔴 Nofaol"

        text += (
            f"🆔 ID: {mock_id}\n"
            f"📘 {name}\n"
            f"📝 Savollar: {len(key)} ta\n"
            f"Holati: {status}\n"
            "━━━━━━━━━━━━━━━━━━\n"
        )

    await message.answer(text, parse_mode="Markdown")


# ==========================================
# O'QUVCHILAR
# ==========================================

@dp.message(F.text == "👥  O'QUVCHILAR")
async def students(message: Message):

    if not is_admin(message.from_user.id):
        return

    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count = (await cursor.fetchone())[0]

    await message.answer(
        academy_header()
        + f"👥 **O'QUVCHILAR:** {count} ta",
        parse_mode="Markdown"
    )


# ==========================================
# STATISTIKA
# ==========================================

@dp.message(F.text == "📊  STATISTIKA")
async def statistics(message: Message):

    if not is_admin(message.from_user.id):
        return

    async with aiosqlite.connect(DB) as db:

        c1 = await db.execute("SELECT COUNT(*) FROM mocks")
        mocks = (await c1.fetchone())[0]

        c2 = await db.execute("SELECT COUNT(*) FROM users")
        users = (await c2.fetchone())[0]

        c3 = await db.execute(
            "SELECT COUNT(*) FROM attempts WHERE finished=1"
        )
        finished = (await c3.fetchone())[0]

    await message.answer(
        academy_header()
        + "📊 **STATISTIKA**\n\n"
        + f"📘 Mocklar: {mocks}\n"
        + f"👥 O'quvchilar: {users}\n"
        + f"🏁 Tugatilgan testlar: {finished}",
        parse_mode="Markdown"
    )


# ==========================================
# ASOSIY MENYU
# ==========================================

@dp.message(F.text == "🏠  ASOSIY MENYU")
async def back_main(message: Message, state: FSMContext):

    await state.clear()

    if is_admin(message.from_user.id):
        await message.answer(
            academy_header() + "👑 **ADMIN PANEL**",
            reply_markup=admin_menu,
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            academy_header() + "🏠 **ASOSIY MENYU**",
            reply_markup=main_menu,
            parse_mode="Markdown"
        )


# ==========================================
# O'QUVCHI MOCKLARI
# ==========================================

@dp.message(F.text == "📚  MOCK TESTLAR")
async def student_mocks(message: Message):

    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT id, name, answer_key
            FROM mocks WHERE active=1
            ORDER BY id DESC
            """
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Hozircha faol mocklar yo'q.")
        return

    await message.answer(
        academy_header() + "📚 **MAVJUD MOCK TESTLAR**",
        parse_mode="Markdown"
    )

    for mock_id, name, key in rows:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📖 MOCKNI OCHISH",
                        callback_data=f"open:{mock_id}"
                    )
                ]
            ]
        )

        await message.answer(
            f"♛ **{name}**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📝 Savollar: {len(key)} ta",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


# ==========================================
# MOCKNI OCHISH
# ==========================================

@dp.callback_query(F.data.startswith("open:"))
async def open_mock(callback: CallbackQuery):

    mock_id = int(callback.data.split(":")[1])
    mock = await get_mock(mock_id)

    if not mock or not mock[4]:
        await callback.answer("Mock topilmadi.", show_alert=True)
        return

    await callback.answer()

    _, name, media_text, answer_key, active = mock
    total = len(answer_key)

    await callback.message.answer(
        academy_header()
        + f"📘 **{name}**\n"
        + f"📝 Savollar soni: {total} ta\n\n"
        + "PDF faylni ko'rib chiqing.",
        parse_mode="Markdown"
    )

    try:
        media = ast.literal_eval(media_text)
    except (ValueError, SyntaxError, TypeError):
        await callback.message.answer("PDF ma'lumotida xatolik bor.")
        return

    for item in media:

        try:
            if item["type"] == "document":
                await callback.message.answer_document(item["file_id"])
            elif item["type"] == "photo":
                await callback.message.answer_photo(item["file_id"])
        except Exception:
            logging.exception("Media yuborishda xatolik")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 TESTNI BOSHLASH",
                    callback_data=f"begin:{mock_id}"
                )
            ]
        ]
    )

    await callback.message.answer(
        "♛ Tayyor bo'lsangiz, testni boshlang.",
        reply_markup=keyboard
    )


# ==========================================
# TESTNI BOSHLASH
# ==========================================

@dp.callback_query(F.data.startswith("begin:"))
async def begin_test(callback: CallbackQuery):

    mock_id = int(callback.data.split(":")[1])
    mock = await get_mock(mock_id)

    if not mock or not mock[4]:
        await callback.answer("Mock topilmadi.", show_alert=True)
        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute(
            """
            SELECT id, answers, started_at
            FROM attempts
            WHERE user_id=? AND mock_id=? AND finished=0
            ORDER BY id DESC LIMIT 1
            """,
            (callback.from_user.id, mock_id)
        )

        old_attempt = await cursor.fetchone()

        if old_attempt:

            attempt_id = old_attempt[0]
            answers = old_attempt[1] or ""
            started_at = old_attempt[2] or int(time.time())

            if time.time() - started_at >= TEST_TIME:
                await db.execute(
                    "UPDATE attempts SET finished=1 WHERE id=?",
                    (attempt_id,)
                )
                await db.commit()
                old_attempt = None

        if not old_attempt:

            cursor = await db.execute(
                """
                INSERT INTO attempts(
                    user_id, mock_id, answers, started_at
                )
                VALUES(?, ?, '', ?)
                """,
                (
                    callback.from_user.id,
                    mock_id,
                    int(time.time())
                )
            )

            attempt_id = cursor.lastrowid
            answers = ""

        else:
            attempt_id = old_attempt[0]

        await db.commit()

    await callback.answer("Test boshlandi!")

    total = len(mock[3])
    answers = (answers or "").ljust(total, "-")[:total]

    question_no = 1

    for index, answer in enumerate(answers):
        if answer == "-":
            question_no = index + 1
            break
    else:
        question_no = total

    await show_question(
        callback.message,
        attempt_id,
        question_no
    )


# ==========================================
# JAVOB TANLASH
# ==========================================

@dp.callback_query(F.data.startswith("ans:"))
async def choose_answer(callback: CallbackQuery):

    _, attempt_id, question_no, answer = callback.data.split(":")

    attempt_id = int(attempt_id)
    question_no = int(question_no)

    attempt = await get_attempt(attempt_id)

    if not attempt or attempt[1] != callback.from_user.id or attempt[5]:
        await callback.answer(
            "Bu test sizga tegishli emas yoki yakunlangan."
        )
        return

    mock = await get_mock(attempt[2])

    if not mock:
        await callback.answer("Mock topilmadi.")
        return

    if time.time() - attempt[6] >= TEST_TIME:
        result = await result_text(attempt_id, callback.from_user.id)
        await callback.message.edit_text(result, parse_mode="Markdown")
        await callback.answer("Test vaqti tugadi.")
        return

    total = len(mock[3])

    if not 1 <= question_no <= total:
        await callback.answer("Savol topilmadi.")
        return

    answers = (attempt[3] or "").ljust(total, "-")[:total]

    answers = (
        answers[:question_no - 1]
        + answer
        + answers[question_no:]
    )

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE attempts SET answers=? WHERE id=?",
            (answers, attempt_id)
        )
        await db.commit()

    await callback.answer(f"{answer} javobi belgilandi.")

    next_question = min(question_no + 1, total)

    await show_question(
        callback,
        attempt_id,
        next_question
    )


# ==========================================
# SAVOLLAR ORASIDA YURISH
# ==========================================

@dp.callback_query(F.data.startswith("nav:"))
async def navigate(callback: CallbackQuery):

    _, attempt_id, question_no = callback.data.split(":")

    attempt_id = int(attempt_id)
    question_no = int(question_no)

    attempt = await get_attempt(attempt_id)

    if not attempt or attempt[1] != callback.from_user.id or attempt[5]:
        await callback.answer("Test topilmadi yoki yakunlangan.")
        return

    if time.time() - attempt[6] >= TEST_TIME:
        result = await result_text(attempt_id, callback.from_user.id)
        await callback.message.edit_text(result, parse_mode="Markdown")
        await callback.answer("Test vaqti tugadi.")
        return

    mock = await get_mock(attempt[2])

    if not mock:
        await callback.answer("Mock topilmadi.")
        return

    total = len(mock[3])
    question_no = max(1, min(question_no, total))

    await callback.answer()

    await show_question(
        callback,
        attempt_id,
        question_no
    )


# ==========================================
# TESTNI YAKUNLASH
# ==========================================

@dp.callback_query(F.data.startswith("finish:"))
async def finish_test(callback: CallbackQuery):

    attempt_id = int(callback.data.split(":")[1])

    attempt = await get_attempt(attempt_id)

    if not attempt or attempt[1] != callback.from_user.id:
        await callback.answer("Test sizga tegishli emas.")
        return

    if attempt[5]:
        await callback.answer("Test allaqachon yakunlangan.")
        return

    result = await result_text(
        attempt_id,
        callback.from_user.id
    )

    await callback.message.edit_text(
        result,
        parse_mode="Markdown"
    )

    await callback.answer("Test yakunlandi!")


# ==========================================
# SHAXSIY KABINET
# ==========================================

@dp.message(F.text == "👤  SHAXSIY KABINET")
async def profile(message: Message):

    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*), SUM(score)
            FROM attempts
            WHERE user_id=? AND finished=1
            """,
            (message.from_user.id,)
        )

        count, score = await cursor.fetchone()

    await message.answer(
        academy_header()
        + "👤 **SHAXSIY KABINET**\n\n"
        + f"🆔 ID: {message.from_user.id}\n"
        + f"🏁 Tugatilgan testlar: {count or 0}\n"
        + f"✅ Jami to'g'ri javoblar: {score or 0}\n"
        + "━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )


# ==========================================
# REYTING
# ==========================================

@dp.message(F.text == "🏆  REYTING")
async def ranking(message: Message):

    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT user_id, SUM(score) AS total
            FROM attempts
            WHERE finished=1
            GROUP BY user_id
            ORDER BY total DESC
            LIMIT 10
            """
        )

        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Hozircha reyting mavjud emas.")
        return

    text = academy_header() + "🏆 **TOP 10 REYTING**\n\n"

    for i, (user_id, score) in enumerate(rows, start=1):
        text += f"{i}. ID: {user_id} — {score} ball\n"

    await message.answer(text, parse_mode="Markdown")


# ==========================================
# YORDAM
# ==========================================

@dp.message(F.text == "ℹ️  YORDAM")
async def help_section(message: Message):

    await message.answer(
        academy_header()
        + "ℹ️ **YORDAM MARKAZI**\n\n"
        + "📚 Mock testlar bo'limidan testni tanlang.\n"
        + "📄 PDF faylni ochib savollarni ko'ring.\n"
        + "🚀 Testni boshlang va A, B, C yoki D javobini belgilang.\n"
        + "🏁 Yakunda natijangizni ko'rishingiz mumkin.\n\n"
        + "⏱ Test vaqti: 120 daqiqa.",
        parse_mode="Markdown"
    )


# ==========================================
# ISHGA TUSHIRISH
# ==========================================

async def main():

    if not BOT_TOKEN:
        raise ValueError(".env faylida BOT_TOKEN topilmadi.")

    if not ADMIN_ID:
        raise ValueError(".env faylida ADMIN_ID topilmadi.")

    await init_db()

    print("FARID ACADEMY — BLACK GOLD ishga tushdi!")

    await dp.start_polling(bot)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())
