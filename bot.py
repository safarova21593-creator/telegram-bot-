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

bot = Bot(TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"
STATE_FILE = "state.json"


# -------------------- STORAGE --------------------

def load(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load(DATA_FILE, {"users": []})
state = load(STATE_FILE, {})
admin_state = {}


def save_all():
    save(DATA_FILE, data)
    save(STATE_FILE, state)


# -------------------- ACCESS --------------------

def allowed(uid: int):
    return uid == ADMIN_ID or uid in data["users"]


# -------------------- MAIN MENU --------------------

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1️⃣Разогрев")],
        [KeyboardButton(text="2️⃣Рабочие звуки/звонкие качества")],
        [KeyboardButton(text="3️⃣Народный/Бэлтинг")],
        [KeyboardButton(text="4️⃣Вокальные упражнения")]
    ],
    resize_keyboard=True
)


# -------------------- ADMIN MENU --------------------

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить пользователя")],
        [KeyboardButton(text="➖ Удалить пользователя")],
        [KeyboardButton(text="🔙 Выйти")]
    ],
    resize_keyboard=True
)


# -------------------- COURSES --------------------

COURSES = {
    "1": {
        "finish": "{} , переходи к следующему блоку➡️",
        "videos": [
            ("Трель", "BAACAgIAAxkBAAICvmmHnO8V9I3oytM_0IiWhjMTdJp-AAJ6qAACd5hBSKlSxJmdQJHBOgQ"),
            ("Сирена", "BAACAgIAAxkBAAIDIGmI_kAdS8HC05EHgVyGq9jQVaQoAAJQhQACV81JSEiL0QG73KRUOgQ"),
            ("Голосовые складки", "BAACAgIAAxkBAAIFbWng_qo7u6OwFP5K_h-GczbCQcC8AAKAnQACU0kIS8ZNCKOp2pSzOwQ"),
            ("Мягкое небо", "BAACAgIAAxkBAAIHNGnhXL3xHKjyivh9gSnrA0Jse3GzAALdkwACU0kQS34mCZVfDDTvOwQ"),
            ("NG", "BAACAgIAAxkBAAIDH2mI-58aJh8VzvCnxpHtu9hxj0QhAAI5hQACV81JSDK87Yy0XYZdOgQ"),
            ("ng A ng Э", "BAACAgIAAxkBAAIEymneqa_G3NtmM8dMxpPONroNQ5U7AAK4lAACYBLxSuqWnm-uZl18OwQ"),
        ]
    },

    "2": {
        "finish": "{} , двигайся к следующему блоку➡️",
        "videos": [
            ("А-И-У", "BAACAgIAAxkBAAIFumnhHaYAAbSLYje2d_N4qXiqopvf-AACE5IAAlNJEEsYt2qZlJZTgDsE"),
            ("Звонкие качества", "BAACAgIAAxkBAAII92nhfu2ymq0kDxyoMFZzMzE289HsAAISlAACU0kQS5YS6-tgJdcyOwQ"),
            ("ГА ГА ГА", "BAACAgIAAxkBAAIFxGnhJjXXG37cJfTWg273_KUveChxAAJtkgACU0kQSzn02yOQpEhqOwQ"),
            ("НИ НЭ", "BAACAgIAAxkBAAIF2WnhM-7P38m-B0bGRnTgXnjwaCCKAAISkwACU0kQS3g6-k1iAQt0OwQ"),
            ("Папайя", "BAACAgIAAxkBAAIF8GnhOty0hfema_C2945TJ3kRNfgQAAJYkwACU0kQSwcyvjHbyS5OOwQ"),
            ("Пицца", "BAACAgIAAxkBAAIGAAFp4T5pkmCPmMpA_K3_sWJ10OnAaQACcZMAAlNJEEtKFEH1OPL8EjsE"),
            ("Не мни мини", "BAACAgIAAxkBAAIGC2nhQso05PaTOuxMqgbfmUWKu4vxAAKDkwACU0kQS-5qfczcBdYHOwQ"),
        ]
    },

    "3": {
        "finish": "Пришло время практики → Вокальные упражнения🎤",
        "videos": [
            ("Народный звук", "BAACAgIAAxkBAAIGMWnhRgSBfkkdzEi3cD4n4yJtEXDgAAKMkwACU0kQS3E571ltEh5sOwQ"),
            ("Народный Э", "BAACAgIAAxkBAAIGUmnhSHqm0EHi9zr-xIMSYOGxVI-9AAKRkwACU0kQSzHyfk-FkhYYOwQ"),
            ("Народный О", "BAACAgIAAxkBAAIGWGnhUD31UYfwrNP7fGRatPn43RISAAKikwACU0kQS6RupTxsjvjcOwQ"),
            ("Стабильность", "BAACAgIAAxkBAAIGXGnhUIQJ0wHK3IzB1cALXp_wzQl_AAKlkwACU0kQS-5wZs_ul8x1OwQ"),
        ]
    },

    "4": {
        "finish": "<b>С заботой о Вас, Юлия Золотых❤️</b>",
        "videos": [
            ("Я не боюсь темноты", "BAACAgIAAxkBAAIGemnhUiaMGOab8Ngh5ki6b1aQHwJMAAKvkwACU0kQS_mkx39_mJTAOwQ"),
            ("Доброе утро", "BAACAgIAAxkBAAIGfmnhUrpdHCBV1an_Ka86Zz8EVBUHAAKxkwACU0kQS0U45H9dPJY4OwQ"),
            ("За волной волна", "BAACAgIAAxkBAAIGgmnhUx6A5owEQmTRrxoQlaKWCLCEAAKykwACU0kQS8vGmN3mpHqgOwQ"),
            ("Фифа", "BAACAgIAAxkBAAIGhmnhVGbMXxnIkK_POOn1yfzDxWmdAAK_kwACU0kQSwMyG1UvEm1vOwQ"),
            ("Как легко", "BAACAgIAAxkBAAIGimnhVOfQLrZYuaOwukhZ9LktdCFzAALDkwACU0kQS8d1HWfJFB1mOwQ"),
        ]
    }
}


# -------------------- UTIL --------------------

def bar(i, total):
    return "🟩" * (i + 1) + "⬜" * (total - (i + 1)) + f" {i+1}/{total}"


def kb(last: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Завершить" if last else "Дальше", callback_data="next")]
    ])


# -------------------- START --------------------

@dp.message(CommandStart())
async def start(m: Message):
    if not allowed(m.from_user.id):
        return await m.answer("Доступ ограничен")

    name = m.from_user.first_name
    await m.answer(f"Приветствую тебя, {name}!")

    await asyncio.sleep(3)
    await m.answer("Выбери блок:", reply_markup=menu)


# -------------------- COURSE START --------------------

async def start_course(m: Message, cid: str):
    state[str(m.from_user.id)] = {"c": cid, "i": 0}
    save_all()
    await send_video(m, m.from_user.id)


@dp.message(F.text == "1️⃣Разогрев")
async def c1(m): await start_course(m, "1")

@dp.message(F.text == "2️⃣Рабочие звуки/звонкие качества")
async def c2(m): await start_course(m, "2")

@dp.message(F.text == "3️⃣Народный/Бэлтинг")
async def c3(m): await start_course(m, "3")

@dp.message(F.text == "4️⃣Вокальные упражнения")
async def c4(m): await start_course(m, "4")


# -------------------- FLOW --------------------

async def send_video(m: Message, uid: int):
    uid = str(uid)
    if uid not in state:
        return

    s = state[uid]
    course = COURSES[s["c"]]
    i = s["i"]

    title, vid = course["videos"][i]

    await m.answer_video(
        vid,
        caption=f"<b>{title}</b>\n\n{bar(i, len(course['videos']))}",
        parse_mode="HTML",
        reply_markup=kb(i == len(course["videos"]) - 1)
    )


@dp.callback_query(F.data == "next")
async def nxt(c: CallbackQuery):
    uid = str(c.from_user.id)
    if uid not in state:
        return

    s = state[uid]
    course = COURSES[s["c"]]

    s["i"] += 1
    save_all()

    if s["i"] >= len(course["videos"]):
        await c.message.answer(course["finish"].format(c.from_user.first_name), reply_markup=menu)
        return

    await send_video(c.message, int(uid))


# -------------------- ADMIN PANEL --------------------

@dp.message(Command("admin"))
async def admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = None
    await m.answer("Админ-панель:", reply_markup=admin_kb)


@dp.message(F.text == "➕ Добавить пользователя")
async def add_mode(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = "add"
    await m.answer("Отправь ID пользователя")


@dp.message(F.text == "➖ Удалить пользователя")
async def rem_mode(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = "remove"
    await m.answer("Отправь ID пользователя")


@dp.message(F.text == "🔙 Выйти")
async def exit_admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = None
    await m.answer("Выход", reply_markup=menu)


@dp.message()
async def admin_input(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    mode = admin_state.get(m.from_user.id)
    if not mode:
        return

    try:
        uid = int(m.text)
    except:
        return await m.answer("Неверный ID")

    if mode == "add":
        if uid not in data["users"]:
            data["users"].append(uid)

    if mode == "remove":
        if uid in data["users"]:
            data["users"].remove(uid)

    save_all()
    admin_state[m.from_user.id] = None

    await m.answer("Готово")


# -------------------- RUN --------------------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())