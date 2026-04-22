import asyncio
import json
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
from aiogram.filters import CommandStart, Command

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 470343161

bot = Bot(token=TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"
STATE_FILE = "state.json"


# -------------------- DATA --------------------

def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_json(DATA_FILE, {"users": []})
state_db = load_json(STATE_FILE, {})


def save_state():
    save_json(STATE_FILE, state_db)


def save_data():
    save_json(DATA_FILE, data)


# -------------------- ACCESS --------------------

def is_admin(uid: int):
    return uid == ADMIN_ID


def is_allowed(uid: int):
    return uid in data["users"] or is_admin(uid)


# -------------------- KEYBOARD --------------------

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1️⃣ Разогрев")],
        [KeyboardButton(text="2️⃣ Рабочие звуки")],
        [KeyboardButton(text="3️⃣ Народный/Бэлтинг")],
        [KeyboardButton(text="4️⃣ Вокальные упражнения")]
    ],
    resize_keyboard=True
)


# -------------------- TRAINING --------------------

TRAININGS = {
    "1": {
        "finish": "👉 {} , переходи к следующему блоку➡️",
        "videos": [
            ("Трель", "BAACAgIAAxkBAAICvmmHnO8V9I3oytM_0IiWhjMTdJp-AAJ6qAACd5hBSKlSxJmdQJHBOgQ"),
            ("Сирена", "BAACAgIAAxkBAAIDIGmI_kAdS8HC05EHgVyGq9jQVaQoAAJQhQACV81JSEiL0QG73KRUOgQ"),
            ("Голосовые складки", "BAACAgIAAxkBAAIFbWng_qo7u6OwFP5K_h-GczbCQcC8AAKAnQACU0kIS8ZNCKOp2pSzOwQ"),
        ]
    },

    "2": {
        "finish": "👉 {} , двигайся дальше➡️",
        "videos": [
            ("А-И-У", "BAACAgIAAxkBAAIFumnhHaYAAbSLYje2d_N4qXiqopvf-AACE5IAAlNJEEsYt2qZlJZTgDsE"),
            ("Звонкие качества", "BAACAgIAAxkBAAII92nhfu2ymq0kDxyoMFZzMzE289HsAAISlAACU0kQS5YS6-tgJdcyOwQ"),
        ]
    },

    "3": {
        "finish": "Пришло время практики → Вокальные упражнения 🎤",
        "videos": [
            ("Народный звук", "BAACAgIAAxkBAAIGMWnhRgSBfkkdzEi3cD4n4yJtEXDgAAKMkwACU0kQS3E571ltEh5sOwQ"),
            ("Народный Э", "BAACAgIAAxkBAAIGUmnhSHqm0EHi9zr-xIMSYOGxVI-9AAKRkwACU0kQSzHyfk-FkhYYOwQ"),
        ]
    },

    "4": {
        "finish": "Юлия Золотых ❤️",
        "videos": [
            ("Я не боюсь темноты", "BAACAgIAAxkBAAIGemnhUiaMGOab8Ngh5ki6b1aQHwJMAAKvkwACU0kQS_mkx39_mJTAOwQ"),
            ("Доброе утро", "BAACAgIAAxkBAAIGfmnhUrpdHCBV1an_Ka86Zz8EVBUHAAKxkwACU0kQS0U45H9dPJY4OwQ"),
        ]
    }
}


# -------------------- UTIL --------------------

def bar(i, total):
    return "🟩" * (i + 1) + "⬜" * (total - (i + 1)) + f" {i+1}/{total}"


def kb(is_last: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Завершить" if is_last else "Дальше", callback_data="next")]
    ])


# -------------------- START --------------------

@dp.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id

    if not is_allowed(uid):
        await message.answer("Доступ ограничен.")
        return

    name = message.from_user.first_name

    await message.answer(f"Приветствую тебя, {name}!")
    await asyncio.sleep(3)
    await message.answer("Выбери блок:", reply_markup=main_kb)


# -------------------- MENU --------------------

async def start_block(message: Message, block: str):
    uid = message.from_user.id
    state_db[str(uid)] = {"block": block, "i": 0}
    save_state()
    await send_video(message, uid)


@dp.message(F.text == "1️⃣ Разогрев")
async def b1(m: Message): await start_block(m, "1")

@dp.message(F.text == "2️⃣ Рабочие звуки")
async def b2(m: Message): await start_block(m, "2")

@dp.message(F.text == "3️⃣ Народный/Бэлтинг")
async def b3(m: Message): await start_block(m, "3")

@dp.message(F.text == "4️⃣ Вокальные упражнения")
async def b4(m: Message): await start_block(m, "4")


# -------------------- FLOW --------------------

async def send_video(message: Message, uid: int):
    uid = str(uid)

    if uid not in state_db:
        return

    state = state_db[uid]
    block = TRAININGS[state["block"]]
    i = state["i"]

    title, vid = block["videos"][i]
    total = len(block["videos"])

    text = f"<b>{title}</b>\n\n{bar(i, total)}"

    await message.answer_video(
        video=vid,
        caption=text,
        parse_mode="HTML",
        reply_markup=kb(i == total - 1)
    )


@dp.callback_query(F.data == "next")
async def next_step(call: CallbackQuery):
    uid = str(call.from_user.id)

    if uid not in state_db:
        return

    state = state_db[uid]
    block = TRAININGS[state["block"]]

    state["i"] += 1
    save_state()

    if state["i"] >= len(block["videos"]):
        await call.message.answer(block["finish"].format(call.from_user.first_name), reply_markup=main_kb)
        return

    await send_video(call.message, int(uid))


# -------------------- ADMIN --------------------

@dp.message(Command("add_user"))
async def add_user(m: Message):
    if not is_admin(m.from_user.id):
        return

    uid = int(m.text.split()[1])
    if uid not in data["users"]:
        data["users"].append(uid)
        save_data()

    await m.answer("Добавлено")


@dp.message(Command("remove_user"))
async def remove_user(m: Message):
    if not is_admin(m.from_user.id):
        return

    uid = int(m.text.split()[1])
    if uid in data["users"]:
        data["users"].remove(uid)
        save_data()

    await m.answer("Удалено")


# -------------------- RUN --------------------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())