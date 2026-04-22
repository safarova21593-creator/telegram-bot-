import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import CommandStart

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

# -------------------- ДОСТУП --------------------

ALLOWED_USERS = {470343161, 1363068163, 787557638, 518077592}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# -------------------- ДАННЫЕ --------------------

BLOCKS = {
    "warmup": [
        ("Трель", "BAACAgIAAxkBAAICvmmHnO8V9I3oytM_0IiWhjMTdJp-AAJ6qAACd5hBSKlSxJmdQJHBOgQ"),
        ("Сирена", "BAACAgIAAxkBAAIDIGmI_kAdS8HC05EHgVyGq9jQVaQoAAJQhQACV81JSEiL0QG73KRUOgQ"),
        ("Режимы работы голосовых складок", "BAACAgIAAxkBAAIFbWng_qo7u6OwFP5K_h-GczbCQcC8AAKAnQACU0kIS8ZNCKOp2pSzOwQ"),
        ("Мягкое небо", "BAACAgIAAxkBAAIHNGnhXL3xHKjyivh9gSnrA0Jse3GzAALdkwACU0kQS34mCZVfDDTvOwQ"),
        ("NG", "BAACAgIAAxkBAAIDH2mI-58aJh8VzvCnxpHtu9hxj0QhAAI5hQACV81JSDK87Yy0XYZdOgQ"),
        ("NG A, NG Э", "BAACAgIAAxkBAAIEymneqa_G3NtmM8dMxpPONroNQ5U7AAK4lAACYBLxSuqWnm-uZl18OwQ"),
    ],
    "voice": [
        ("Основные рабочие звуки А-И-У", "BAACAgIAAxkBAAIFumnhHaYAAbSLYje2d_N4qXiqopvf-AACE5IAAlNJEEsYt2qZlJZTgDsE"),
        ("Звонкие качества", "BAACAgIAAxkBAAII92nhfu2ymq0kDxyoMFZzMzE289HsAAISlAACU0kQS5YS6-tgJdcyOwQ"),
        ("ГА ГА ГА, НА НА НА", "BAACAgIAAxkBAAIFxGnhJjXXG37cJfTWg273_KUveChxAAJtkgACU0kQSzn02yOQpEhqOwQ"),
        ("НИ НЭ НА НО", "BAACAgIAAxkBAAIF2WnhM-7P38m-B0bGRnTgXnjwaCCKAAISkwACU0kQS3g6-k1iAQt0OwQ"),
        ("Папайя", "BAACAgIAAxkBAAIF8GnhOty0hfema_C2945TJ3kRNfgQAAJYkwACU0kQSwcyvjHbyS5OOwQ"),
        ("Пицца", "BAACAgIAAxkBAAIGAAFp4T5pkmCPmMpA_K3_sWJ10OnAaQACcZMAAlNJEEtKFEH1OPL8EjsE"),
        ("Не мни мне мини", "BAACAgIAAxkBAAIGC2nhQso05PaTOuxMqgbfmUWKu4vxAAKDkwACU0kQS-5qfczcBdYHOwQ"),
    ],
    "belt": [
        ("Народный звук (Бэлтинг)", "BAACAgIAAxkBAAIGMWnhRgSBfkkdzEi3cD4n4yJtEXDgAAKMkwACU0kQS3E571ltEh5sOwQ"),
        ("Народный Э", "BAACAgIAAxkBAAIGUmnhSHqm0EHi9zr-xIMSYOGxVI-9AAKRkwACU0kQSzHyfk-FkhYYOwQ"),
        ("Народный О", "BAACAgIAAxkBAAIGWGnhUD31UYfwrNP7fGRatPn43RISAAKikwACU0kQS6RupTxsjvjcOwQ"),
        ("Стабильность народного звука", "BAACAgIAAxkBAAIGXGnhUIQJ0wHK3IzB1cALXp_wzQl_AAKlkwACU0kQS-5wZs_ul8x1OwQ"),
    ],
    "practice": [
        ("Я не боюсь темноты", "BAACAgIAAxkBAAIGemnhUiaMGOab8Ngh5ki6b1aQHwJMAAKvkwACU0kQS_mkx39_mJTAOwQ"),
        ("Доброе утро", "BAACAgIAAxkBAAIGfmnhUrpdHCBV1an_Ka86Zz8EVBUHAAKxkwACU0kQS0U45H9dPJY4OwQ"),
        ("За волной волна", "BAACAgIAAxkBAAIGgmnhUx6A5owEQmTRrxoQlaKWCLCEAAKykwACU0kQS8vGmN3mpHqgOwQ"),
        ("Фифа", "BAACAgIAAxkBAAIGhmnhVGbMXxnIkK_POOn1yfzDxWmdAAK_kwACU0kQSwMyG1UvEm1vOwQ"),
        ("Как легко", "BAACAgIAAxkBAAIGimnhVOfQLrZYuaOwukhZ9LktdCFzAALDkwACU0kQS8d1HWfJFB1mOwQ"),
    ]
}

# -------------------- СОСТОЯНИЕ --------------------

user_state = {}
admin_state = {}

# -------------------- КЛАВИАТУРЫ --------------------

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1️⃣ Разогрев")],
        [KeyboardButton(text="2️⃣ Рабочие звуки/звонкие качества")],
        [KeyboardButton(text="3️⃣ Народный/Бэлтинг")],
        [KeyboardButton(text="4️⃣ Вокальные упражнения")],
    ],
    resize_keyboard=True
)

def inline_next(block: str, index: int):
    last = index == len(BLOCKS[block]) - 1
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Завершить" if last else "Дальше",
            callback_data=f"next:{block}:{index}"
        )
    ]])

def progress_text(block, index):
    total = len(BLOCKS[block])
    done = index + 1
    bar = "🟩" * done + "⬜" * (total - done)
    return f"{bar} {done}/{total}"

# -------------------- ADMIN MENU --------------------

ADMIN_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить видео", callback_data="admin:add")],
    [InlineKeyboardButton(text="📦 Блоки", callback_data="admin:blocks")]
])

# -------------------- START --------------------

@dp.message(CommandStart())
async def start(message: Message):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("Доступ ограничен")
        return

    await message.answer(f"Привет, {message.from_user.first_name}!")
    await asyncio.sleep(1)
    await message.answer("Выбери блок:", reply_markup=main_kb)

# -------------------- ADMIN ENTRY --------------------

@dp.message(F.text == "/admin")
async def admin_panel(message: Message):
    if message.from_user.id not in ALLOWED_USERS:
        return

    await message.answer("Админ-панель:", reply_markup=ADMIN_MENU)

@dp.callback_query(F.data == "admin:add")
async def admin_add(call: CallbackQuery):
    if call.from_user.id not in ALLOWED_USERS:
        return

    admin_state[call.from_user.id] = {"step": "choose_block"}

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Разогрев", callback_data="add:warmup")],
        [InlineKeyboardButton(text="Рабочие", callback_data="add:voice")],
        [InlineKeyboardButton(text="Бэлтинг", callback_data="add:belt")],
        [InlineKeyboardButton(text="Практика", callback_data="add:practice")]
    ])

    await call.message.answer("Выбери блок:", reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("add:"))
async def choose_block(call: CallbackQuery):
    block = call.data.split(":")[1]

    admin_state[call.from_user.id] = {
        "step": "wait_video",
        "block": block
    }

    await call.message.answer("Отправь видео (как файл или видео)")
    await call.answer()

# -------------------- VIDEO UPLOAD (NO FILE ID MANUAL) --------------------

@dp.message(F.video)
async def handle_video(message: Message):
    user_id = message.from_user.id

    if user_id not in ALLOWED_USERS:
        return

    if user_id not in admin_state:
        return

    state = admin_state[user_id]

    if state.get("step") != "wait_video":
        return

    block = state["block"]
    file_id = message.video.file_id
    title = message.caption or "Без названия"

    BLOCKS[block].append((title, file_id))

    admin_state.pop(user_id, None)

    await message.answer(f"Добавлено в блок {block}")

# -------------------- USER BLOCKS --------------------

@dp.message(F.text.contains("Разогрев"))
async def warmup(message: Message):
    user_state[message.from_user.id] = {"block": "warmup", "index": 0}
    await send_video(message, "warmup", 0)

@dp.message(F.text.contains("Рабочие"))
async def voice(message: Message):
    user_state[message.from_user.id] = {"block": "voice", "index": 0}
    await send_video(message, "voice", 0)

@dp.message(F.text.contains("Народный"))
async def belt(message: Message):
    user_state[message.from_user.id] = {"block": "belt", "index": 0}
    await send_video(message, "belt", 0)

@dp.message(F.text.contains("Вокальные"))
async def practice(message: Message):
    user_state[message.from_user.id] = {"block": "practice", "index": 0}
    await send_video(message, "practice", 0)

# -------------------- SEND VIDEO --------------------

async def send_video(message_or_call, block, index):
    user_id = message_or_call.from_user.id
    title, video_id = BLOCKS[block][index]

    caption = f"<b>{title}</b>\n\n{progress_text(block, index)}"

    try:
        await bot.send_video(
            chat_id=user_id,
            video=video_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=inline_next(block, index),
            protect_content=True
        )
    except Exception as e:
        logging.error(e)
        await bot.send_message(user_id, "Ошибка загрузки")

# -------------------- CALLBACK NEXT --------------------

@dp.callback_query(F.data.startswith("next:"))
async def next_step(call: CallbackQuery):
    _, block, idx = call.data.split(":")
    idx = int(idx)

    user_id = call.from_user.id
    next_idx = idx + 1

    if next_idx < len(BLOCKS[block]):
        user_state[user_id] = {"block": block, "index": next_idx}
        await send_video(call, block, next_idx)
    else:
        await bot.send_message(user_id, "Блок завершён")

    await call.answer()

# -------------------- RUN --------------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())