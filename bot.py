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


# -------------------- STORAGE --------------------

def load(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load(DATA_FILE, {
    "users": [],
    "courses": {
        "1": [],
        "2": [],
        "3": [],
        "4": []
    }
})

state = load(STATE_FILE, {})
admin_state = {}
pending_video = {}


def save_all():
    save(DATA_FILE, data)
    save(STATE_FILE, state)


# -------------------- ACCESS --------------------

def allowed(uid: int):
    return uid == ADMIN_ID or uid in data["users"]


# -------------------- KEYBOARDS --------------------

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1️⃣Разогрев")],
        [KeyboardButton(text="2️⃣Рабочие звуки/звонкие качества")],
        [KeyboardButton(text="3️⃣Народный/Бэлтинг")],
        [KeyboardButton(text="4️⃣Вокальные упражнения")]
    ],
    resize_keyboard=True
)


admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить пользователя")],
        [KeyboardButton(text="➖ Удалить пользователя")],
        [KeyboardButton(text="🎥 Добавить видео")],
        [KeyboardButton(text="🔙 Выйти")]
    ],
    resize_keyboard=True
)


# -------------------- UTIL --------------------

def bar(i, total):
    return "🟩" * (i + 1) + "⬜" * (total - (i + 1)) + f" {i+1}/{total}"


def kb(last: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Завершить" if last else "Дальше", callback_data="next")]
    ])


def get_course(cid):
    return data["courses"][cid]


# -------------------- START --------------------

@dp.message(CommandStart())
async def start(m: Message):
    if not allowed(m.from_user.id):
        return await m.answer("Доступ ограничен")

    await m.answer(f"Приветствую тебя, {m.from_user.first_name}!")
    await asyncio.sleep(3)
    await m.answer("Выбери блок:", reply_markup=menu)


# -------------------- START COURSE --------------------

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


# -------------------- VIDEO FLOW --------------------

async def send_video(m: Message, uid: int):
    uid = str(uid)

    if uid not in state:
        return

    s = state[uid]
    course = get_course(s["c"])
    i = s["i"]

    if i >= len(course):
        await m.answer("Курс завершён")
        return

    item = course[i]

    await m.answer_video(
        item["file_id"],
        caption=f"<b>{item['name']}</b>\n\n{bar(i, len(course))}",
        parse_mode="HTML",
        reply_markup=kb(i == len(course) - 1)
    )


@dp.callback_query(F.data == "next")
async def nxt(c: CallbackQuery):
    uid = str(c.from_user.id)

    if uid not in state:
        return

    s = state[uid]
    course = get_course(s["c"])

    s["i"] += 1
    save_all()

    if s["i"] >= len(course):
        await c.message.answer("Курс завершён", reply_markup=menu)
        return

    await send_video(c.message, int(uid))


# -------------------- ADMIN PANEL --------------------

@dp.message(Command("admin"))
async def admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = None
    await m.answer("Админ-панель:", reply_markup=admin_kb)


# -------------------- USERS --------------------

@dp.message(F.text == "➕ Добавить пользователя")
async def add_user(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = "add_user"
    await m.answer("Отправь ID пользователя")


@dp.message(F.text == "➖ Удалить пользователя")
async def remove_user(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = "remove_user"
    await m.answer("Отправь ID пользователя")


@dp.message(F.text == "🔙 Выйти")
async def exit_admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = None
    await m.answer("Выход", reply_markup=menu)


# -------------------- ADD VIDEO FLOW --------------------

@dp.message(F.text == "🎥 Добавить видео")
async def add_video(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    admin_state[m.from_user.id] = "choose_course"
    await m.answer("Выбери курс (1–4)")


@dp.message(F.text.in_(["1", "2", "3", "4"]))
async def choose_course(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    if admin_state.get(m.from_user.id) != "choose_course":
        return

    pending_video[m.from_user.id] = {"course": m.text}
    admin_state[m.from_user.id] = "wait_video"

    await m.answer("Отправь или перешли видео (forward тоже работает)")


# -------------------- RECEIVE VIDEO --------------------

@dp.message(F.video | F.document)
async def receive_video(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    if admin_state.get(m.from_user.id) != "wait_video":
        return

    file_id = None

    if m.video:
        file_id = m.video.file_id
    elif m.document and m.document.mime_type.startswith("video"):
        file_id = m.document.file_id

    if not file_id:
        return await m.answer("Нужно видео")

    pending_video[m.from_user.id]["file_id"] = file_id
    admin_state[m.from_user.id] = "wait_name"

    await m.answer("Теперь отправь название")


# -------------------- RECEIVE NAME --------------------

@dp.message()
async def receive_name(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    if admin_state.get(m.from_user.id) != "wait_name":
        return

    name = m.text
    pv = pending_video[m.from_user.id]

    cid = pv["course"]

    data["courses"][cid].append({
        "name": name,
        "file_id": pv["file_id"]
    })

    save_all()

    admin_state[m.from_user.id] = None
    pending_video[m.from_user.id] = {}

    await m.answer("Видео добавлено ✅")


# -------------------- USER ADMIN --------------------

@dp.message()
async def user_admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    mode = admin_state.get(m.from_user.id)

    if mode not in ["add_user", "remove_user"]:
        return

    try:
        uid = int(m.text)
    except:
        return await m.answer("Ошибка ID")

    if mode == "add_user":
        if uid not in data["users"]:
            data["users"].append(uid)

    elif mode == "remove_user":
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