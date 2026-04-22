import asyncio
import logging
import os

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


# -------------------- CONFIG --------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

ALLOWED_USERS = {470343161, 1363068163, 787557638, 518077592}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


# -------------------- DATA --------------------

BLOCKS = {
    "warmup": [
        ("Трель", "BAACAgIAAxkBAAICvmmHnO8V9I3oytM_0IiWhjMTdJp-AAJ6qAACd5hBSKlSxJmdQJHBOgQ"),
        ("Сирена", "BAACAgIAAxkBAAIDIGmI_kAdS8HC05EHgVyGq9jQVaQoAAJQhQACV81JSEiL0QG73KRUOgQ"),
    ],
    "voice": [],
    "belt": [],
    "practice": []
}

user_state = {}
admin_state = {}


# -------------------- KEYBOARDS --------------------

admin_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📦 Блоки", callback_data="admin:blocks")],
])

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Разогрев")],
        [KeyboardButton(text="Рабочие")],
        [KeyboardButton(text="Народный")],
        [KeyboardButton(text="Вокальные")],
    ],
    resize_keyboard=True
)


def inline_next(block, index):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Далее", callback_data=f"next:{block}:{index}")]
    ])


def progress_text(block, index):
    total = len(BLOCKS[block])
    return f"Шаг {index + 1}/{total}"


# -------------------- START --------------------

@dp.message(CommandStart())
async def start(message: Message):
    if message.from_user.id == 470343161:
        await message.answer("Админ-панель:", reply_markup=admin_kb)
        return

    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("Доступ ограничен")
        return

    await message.answer("Выбери блок:", reply_markup=main_kb)


# -------------------- MAIN ROUTER --------------------

@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text.lower()

    # ---------------- ADMIN MODE ----------------
    if user_id in admin_state:
        state = admin_state[user_id]

        if state["action"] == "add":
            try:
                title, video_id = message.text.split("|")
                BLOCKS[state["block"]].append((title.strip(), video_id.strip()))
                await message.answer("Добавлено ✔️")
                admin_state.pop(user_id)
            except:
                await message.answer("Формат: название | video_id")
            return

        if state["action"] == "delete":
            try:
                idx = int(message.text)
                block = state["block"]

                if 0 <= idx < len(BLOCKS[block]):
                    BLOCKS[block].pop(idx)
                    await message.answer("Удалено ✔️")
                else:
                    await message.answer("Неверный номер")

                admin_state.pop(user_id)
            except:
                await message.answer("Введи число")
            return

    # ---------------- USER MODE ----------------
    if "разогрев" in text:
        user_state[user_id] = {"block": "warmup", "index": 0}
        await send_video(message, "warmup", 0)

    elif "рабочие" in text:
        user_state[user_id] = {"block": "voice", "index": 0}
        await send_video(message, "voice", 0)

    elif "народный" in text:
        user_state[user_id] = {"block": "belt", "index": 0}
        await send_video(message, "belt", 0)

    elif "вокальные" in text:
        user_state[user_id] = {"block": "practice", "index": 0}
        await send_video(message, "practice", 0)


# -------------------- VIDEO --------------------

async def send_video(message, block, index):
    user_id = message.from_user.id
    title, video_id = BLOCKS[block][index]

    caption = f"{title}\n\n{progress_text(block, index)}"

    try:
        await bot.send_video(
            chat_id=user_id,
            video=video_id,
            caption=caption,
            reply_markup=inline_next(block, index),
            protect_content=True
        )
    except Exception as e:
        logging.error(e)
        await message.answer("Ошибка загрузки")


# -------------------- NEXT --------------------

@dp.callback_query(F.data.startswith("next:"))
async def next_step(call: CallbackQuery):
    _, block, idx = call.data.split(":")
    idx = int(idx)

    user_id = call.from_user.id
    next_idx = idx + 1

    if next_idx < len(BLOCKS[block]):
        user_state[user_id] = {"block": block, "index": next_idx}
        await send_video(call.message, block, next_idx)
    else:
        await call.message.answer("Блок завершён")

    await call.answer()


# -------------------- ADMIN --------------------

@dp.callback_query(F.data == "admin:blocks")
async def admin_blocks(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=b, callback_data=f"admin:block:{b}")]
        for b in BLOCKS.keys()
    ])

    await call.message.answer("Блоки:", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("admin:block:"))
async def admin_block(call: CallbackQuery):
    block = call.data.split(":")[2]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data=f"admin:add:{block}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:delete:{block}")],
    ])

    await call.message.answer(f"Блок: {block}", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("admin:add:"))
async def admin_add(call: CallbackQuery):
    block = call.data.split(":")[2]
    admin_state[call.from_user.id] = {"action": "add", "block": block}
    await call.message.answer("Название | video_id")
    await call.answer()


@dp.callback_query(F.data.startswith("admin:delete:"))
async def admin_delete(call: CallbackQuery):
    block = call.data.split(":")[2]

    text = "\n".join(
        f"{i}. {t}" for i, (t, _) in enumerate(BLOCKS[block])
    )

    admin_state[call.from_user.id] = {"action": "delete", "block": block}
    await call.message.answer(text + "\n\nВведите номер")
    await call.answer()


# -------------------- RUN --------------------

async def main():
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())