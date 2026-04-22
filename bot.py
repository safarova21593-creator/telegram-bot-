import asyncio
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, ADMIN_ID, DATA_FILE

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ---------------- DATA ----------------

def load():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": [], "progress": {}}


def save():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load()

# ---------------- CONTENT ----------------

WORKOUTS = {
    "warmup": [
        ("Трель", "BAACAgIAAxkBAAICvmmHnO8V9I3oytM_0IiWhjMTdJp-AAJ6qAACd5hBSKlSxJmdQJHBOgQ"),
        ("Сирена", "BAACAgIAAxkBAAIDIGmI_kAdS8HC05EHgVyGq9jQVaQoAAJQhQACV81JSEiL0QG73KRUOgQ"),
        ("Режимы голосовых складок", "BAACAgIAAxkBAAIFbWng_qo7u6OwFP5K_h-GczbCQcC8AAKAnQACU0kIS8ZNCKOp2pSzOwQ"),
        ("Мягкое небо", "BAACAgIAAxkBAAIHNGnhXL3xHKjyivh9gSnrA0Jse3GzAALdkwACU0kQS34mCZVfDDTvOwQ"),
        ("NG", "BAACAgIAAxkBAAIDH2mI-58aJh8VzvCnxpHtu9hxj0QhAAI5hQACV81JSDK87Yy0XYZdOgQ"),
        ("ng A ng Э", "BAACAgIAAxkBAAIEymneqa_G3NtmM8dMxpPONroNQ5U7AAK4lAACYBLxSuqWnm-uZl18OwQ"),
    ],

    "quality": [
        ("Основные звуки А-И-У", "BAACAgIAAxkBAAIFumnhHaYAAbSLYje2d_N4qXiqopvf-AACE5IAAlNJEEsYt2qZlJZTgDsE"),
        ("Звонкие качества", "BAACAgIAAxkBAAII92nhfu2ymq0kDxyoMFZzMzE289HsAAISlAACU0kQS5YS6-tgJdcyOwQ"),
        ("ГА ГА ГА", "BAACAgIAAxkBAAIFxGnhJjXXG37cJfTWg273_KUveChxAAJtkgACU0kQSzn02yOQpEhqOwQ"),
        ("НИ НЭ НА НО НУ", "BAACAgIAAxkBAAIF2WnhM-7P38m-B0bGRnTgXnjwaCCKAAISkwACU0kQS3g6-k1iAQt0OwQ"),
        ("Папайя", "BAACAgIAAxkBAAIF8GnhOty0hfema_C2945TJ3kRNfgQAAJYkwACU0kQSwcyvjHbyS5OOwQ"),
        ("Пицца", "BAACAgIAAxkBAAIGAAFp4T5pkmCPmMpA_K3_sWJ10OnAaQACcZMAAlNJEEtKFEH1OPL8EjsE"),
        ("Не мни мне мини", "BAACAgIAAxkBAAIGC2nhQso05PaTOuxMqgbfmUWKu4vxAAKDkwACU0kQS-5qfczcBdYHOwQ"),
    ],

    "belting": [
        ("Народный звук", "BAACAgIAAxkBAAIGMWnhRgSBfkkdzEi3cD4n4yJtEXDgAAKMkwACU0kQS3E571ltEh5sOwQ"),
        ("Народный Э", "BAACAgIAAxkBAAIGUmnhSHqm0EHi9zr-xIMSYOGxVI-9AAKRkwACU0kQSzHyfk-FkhYYOwQ"),
        ("Народный О", "BAACAgIAAxkBAAIGWGnhUD31UYfwrNP7fGRatPn43RISAAKikwACU0kQS6RupTxsjvjcOwQ"),
        ("Стабильность", "BAACAgIAAxkBAAIGXGnhUIQJ0wHK3IzB1cALXp_wzQl_AAKlkwACU0kQS-5wZs_ul8x1OwQ"),
    ],

    "exercise": [
        ("Я не боюсь темноты", "BAACAgIAAxkBAAIGemnhUiaMGOab8Ngh5ki6b1aQHwJMAAKvkwACU0kQS_mkx39_mJTAOwQ"),
        ("Доброе утро", "BAACAgIAAxkBAAIGfmnhUrpdHCBV1an_Ka86Zz8EVBUHAAKxkwACU0kQS0U45H9dPJY4OwQ"),
        ("За волной волна", "BAACAgIAAxkBAAIGgmnhUx6A5owEQmTRrxoQlaKWCLCEAAKykwACU0kQS8vGmN3mpHqgOwQ"),
        ("Фифа", "BAACAgIAAxkBAAIGhmnhVGbMXxnIkK_POOn1yfzDxWmdAAK_kwACU0kQSwMyG1UvEm1vOwQ"),
        ("Как легко", "BAACAgIAAxkBAAIGimnhVOfQLrZYuaOwukhZ9LktdCFzAALDkwACU0kQS8d1HWfJFB1mOwQ"),
    ]
}

# ---------------- UI ----------------

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Разогрев")],
        [KeyboardButton(text="Рабочие звуки/звонкие качества")],
        [KeyboardButton(text="Народный/Бэлтинг")],
        [KeyboardButton(text="Вокальные упражнения")]
    ],
    resize_keyboard=True
)


def bar(i, total):
    return "🟩" * (i + 1) + "⬜" * (total - i - 1)


def kb(cat, idx):
    total = len(WORKOUTS[cat])
    if idx == total - 1:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Завершить", callback_data=f"end|{cat}")]]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Дальше", callback_data=f"next|{cat}|{idx}")]]
    )

# ---------------- ACCESS ----------------

def allowed(uid):
    return uid == ADMIN_ID or uid in data["users"]

# ---------------- START ----------------

@dp.message(F.text == "/start")
async def start(m: Message):
    if not allowed(m.from_user.id):
        return await m.answer("Доступ ограничен")

    await m.answer_chat_action("typing")
    await asyncio.sleep(3)

    await m.answer(f"Приветствую тебя, {m.from_user.first_name}!")
    await m.answer("Выбери блок:", reply_markup=menu)

# ---------------- SEND VIDEO ----------------

async def send(cat, idx, msg: Message):
    title, file_id = WORKOUTS[cat][idx]
    total = len(WORKOUTS[cat])

    caption = (
        f"<b>{title}</b>\n\n"
        f"{bar(idx, total)}\n"
        f"{idx+1}/{total}"
    )

    await msg.answer_video(
        video=file_id,
        caption=caption,
        reply_markup=kb(cat, idx)
    )

# ---------------- MENU ----------------

@dp.message(F.text)
async def router(m: Message):
    if not allowed(m.from_user.id):
        return

    mapping = {
        "Разогрев": "warmup",
        "Рабочие звуки/звонкие качества": "quality",
        "Народный/Бэлтинг": "belting",
        "Вокальные упражнения": "exercise"
    }

    if m.text in mapping:
        cat = mapping[m.text]
        data["progress"][str(m.from_user.id)] = {"cat": cat, "i": 0}
        save()

        await send(cat, 0, m)

# ---------------- CALLBACK ----------------

@dp.callback_query(F.data.startswith("next"))
async def nxt(c: CallbackQuery):
    _, cat, idx = c.data.split("|")
    idx = int(idx) + 1

    await c.message.delete()
    await send(cat, idx, c.message)
    await c.answer()


@dp.callback_query(F.data.startswith("end"))
async def end(c: CallbackQuery):
    _, cat = c.data.split("|")

    await c.message.answer(f"{c.from_user.first_name}, переходи к следующему блоку➡️")
    await c.answer()

# ---------------- ADMIN ----------------

@dp.message(F.text.startswith("/add_user"))
async def add(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    uid = int(m.text.split()[1])
    data["users"].append(uid)
    save()
    await m.answer("OK")


@dp.message(F.text.startswith("/remove_user"))
async def remove(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    uid = int(m.text.split()[1])
    data["users"].remove(uid)
    save()
    await m.answer("OK")

# ---------------- RUN ----------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())