import os
import json
import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 470343161

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)

DATA_FILE = "data.json"

# ------------------ DATA ------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": [], "modules": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ------------------ MODULES ------------------

MODULES = {
    "warmup": {
        "name": "РАЗОГРЕВ",
        "finish_text": "{name}, переходи к следующему блоку➡️",
        "videos": [
            ("Трель", "BAACAgIAAxkBAAICvmmHnO8V9I3oytM_0IiWhjMTdJp-AAJ6qAACd5hBSKlSxJmdQJHBOgQ"),
            ("Сирена", "BAACAgIAAxkBAAIDIGmI_kAdS8HC05EHgVyGq9jQVaQoAAJQhQACV81JSEiL0QG73KRUOgQ"),
            ("Режимы работы голосовых складок", "BAACAgIAAxkBAAIFbWng_qo7u6OwFP5K_h-GczbCQcC8AAKAnQACU0kIS8ZNCKOp2pSzOwQ"),
            ("Мягкое небо", "BAACAgIAAxkBAAIHNGnhXL3xHKjyivh9gSnrA0Jse3GzAALdkwACU0kQS34mCZVfDDTvOwQ"),
            ("NG", "BAACAgIAAxkBAAIDH2mI-58aJh8VzvCnxpHtu9hxj0QhAAI5hQACV81JSDK87Yy0XYZdOgQ"),
            ("ng A ng Э", "BAACAgIAAxkBAAIEymneqa_G3NtmM8dMxpPONroNQ5U7AAK4lAACYBLxSuqWnm-uZl18OwQ"),
        ]
    },

    "sounds": {
        "name": "РАБОЧИЕ ЗВУКИ",
        "finish_text": "{name}, двигайся к следующему блоку➡️",
        "videos": [
            ("Основные рабочие звуки А-И-У", "BAACAgIAAxkBAAIFumnhHaYAAbSLYje2d_N4qXiqopvf-AACE5IAAlNJEEsYt2qZlJZTgDsE"),
            ("Звонкие качества", "BAACAgIAAxkBAAII92nhfu2ymq0kDxyoMFZzMzE289HsAAISlAACU0kQS5YS6-tgJdcyOwQ"),
            ("ГА ГА ГА, НА НА НА", "BAACAgIAAxkBAAIFxGnhJjXXG37cJfTWg273_KUveChxAAJtkgACU0kQSzn02yOQpEhqOwQ"),
            ("НИ НЭ НА НО НУ", "BAACAgIAAxkBAAIF2WnhM-7P38m-B0bGRnTgXnjwaCCKAAISkwACU0kQS3g6-k1iAQt0OwQ"),
            ("Папайя", "BAACAgIAAxkBAAIF8GnhOty0hfema_C2945TJ3kRNfgQAAJYkwACU0kQSwcyvjHbyS5OOwQ"),
            ("Пицца", "BAACAgIAAxkBAAIGAAFp4T5pkmCPmMpA_K3_sWJ10OnAaQACcZMAAlNJEEtKFEH1OPL8EjsE"),
            ("Не мни мне мини", "BAACAgIAAxkBAAIGC2nhQso05PaTOuxMqgbfmUWKu4vxAAKDkwACU0kQS-5qfczcBdYHOwQ"),
        ]
    },

    "belting": {
        "name": "НАРОДНЫЙ/БЭЛТИНГ",
        "finish_text": "Пришло время реализовать полученные навыки на практике, переходи к блоку \"Вокальные упражнения\"🎤",
        "videos": [
            ("Народный звук (Бэлтинг), объяснение", "BAACAgIAAxkBAAIGMWnhRgSBfkkdzEi3cD4n4yJtEXDgAAKMkwACU0kQS3E571ltEh5sOwQ"),
            ("Народный Э", "BAACAgIAAxkBAAIGUmnhSHqm0EHi9zr-xIMSYOGxVI-9AAKRkwACU0kQSzHyfk-FkhYYOwQ"),
            ("Народный О", "BAACAgIAAxkBAAIGWGnhUD31UYfwrNP7fGRatPn43RISAAKikwACU0kQS6RupTxsjvjcOwQ"),
            ("Стабильность народного звука", "BAACAgIAAxkBAAIGXGnhUIQJ0wHK3IzB1cALXp_wzQl_AAKlkwACU0kQS-5wZs_ul8x1OwQ"),
        ]
    },

    "exercises": {
        "name": "ВОКАЛЬНЫЕ УПРАЖНЕНИЯ",
        "finish_text": "{name}, поздравляю с завершением тренировки!\n\nДля закрепления стойкого результата делайте эти практики регулярно.\n\n<b>С заботой о Вас, Юлия Золотых❤️</b>",
        "videos": [
            ("Я не боюсь темноты", "BAACAgIAAxkBAAIGemnhUiaMGOab8Ngh5ki6b1aQHwJMAAKvkwACU0kQS_mkx39_mJTAOwQ"),
            ("Доброе утро", "BAACAgIAAxkBAAIGfmnhUrpdHCBV1an_Ka86Zz8EVBUHAAKxkwACU0kQS0U45H9dPJY4OwQ"),
            ("За волной волна", "BAACAgIAAxkBAAIGgmnhUx6A5owEQmTRrxoQlaKWCLCEAAKykwACU0kQS8vGmN3mpHqgOwQ"),
            ("Фифа", "BAACAgIAAxkBAAIGhmnhVGbMXxnIkK_POOn1yfzDxWmdAAK_kwACU0kQSwMyG1UvEm1vOwQ"),
            ("Как легко", "BAACAgIAAxkBAAIGimnhVOfQLrZYuaOwukhZ9LktdCFzAALDkwACU0kQS8d1HWfJFB1mOwQ"),
        ]
    }
}

# ------------------ UI ------------------

menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1️⃣ Разогрев")],
        [KeyboardButton(text="2️⃣ Рабочие звуки/звонкие качества")],
        [KeyboardButton(text="3️⃣ Народный/Бэлтинг")],
        [KeyboardButton(text="4️⃣ Вокальные упражнения")]
    ],
    resize_keyboard=True
)

def progress_bar(current, total):
    filled = "🟩" * current
    empty = "⬜" * (total - current)
    return f"{filled}{empty} {current}/{total}"

def inline_kb(module, index):
    total = len(MODULES[module]["videos"])
    buttons = []

    if index < total - 1:
        buttons.append([InlineKeyboardButton(text="Дальше", callback_data=f"next:{module}:{index+1}")])
    else:
        buttons.append([InlineKeyboardButton(text="Завершить", callback_data=f"finish:{module}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ------------------ ACCESS ------------------

def is_allowed(user_id: int):
    return user_id == ADMIN_ID or user_id in data["users"]

# ------------------ START ------------------

@router.message(CommandStart())
async def start(message: Message):
    if not is_allowed(message.from_user.id):
        return await message.answer("Доступ ограничен.")

    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(3)

    await message.answer(f"Приветствую тебя, {message.from_user.first_name}!")
    await message.answer("Выбери блок:", reply_markup=menu_kb)

# ------------------ MODULE START ------------------

async def send_video(message: Message, module: str, index: int):
    video = MODULES[module]["videos"][index]
    title, file_id = video

    total = len(MODULES[module]["videos"])

    text = (
        f"<b>{title}</b>\n\n"
        f"{progress_bar(index + 1, total)}"
    )

    await message.answer_video(
        video=file_id,
        caption=text,
        reply_markup=inline_kb(module, index)
    )

# ------------------ MENU ------------------

@router.message(F.text.in_(["1️⃣ Разогрев"]))
async def warmup(m: Message):
    await send_video(m, "warmup", 0)

@router.message(F.text.in_(["2️⃣ Рабочие звуки/звонкие качества"]))
async def sounds(m: Message):
    await send_video(m, "sounds", 0)

@router.message(F.text.in_(["3️⃣ Народный/Бэлтинг"]))
async def belting(m: Message):
    await send_video(m, "belting", 0)

@router.message(F.text.in_(["4️⃣ Вокальные упражнения"]))
async def exercises(m: Message):
    await send_video(m, "exercises", 0)

# ------------------ CALLBACK ------------------

@router.callback_query(F.data.startswith("next"))
async def next_video(call: CallbackQuery):
    _, module, idx = call.data.split(":")
    idx = int(idx)
    await call.message.delete()
    await send_video(call.message, module, idx)
    await call.answer()

@router.callback_query(F.data.startswith("finish"))
async def finish(call: CallbackQuery):
    _, module = call.data.split(":")
    name = call.from_user.first_name

    await call.message.delete()
    await call.message.answer(MODULES[module]["finish_text"].format(name=name))

    await call.answer()

# ------------------ ADMIN ------------------

@router.message(Command("admin"))
async def admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer("Админ режим активен.\n/users — список пользователей")

@router.message(Command("users"))
async def users(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer("\n".join(map(str, data["users"])) or "Нет пользователей")

@router.message(Command("add_user"))
async def add_user(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(m.text.split()[1])
        if user_id not in data["users"]:
            data["users"].append(user_id)
            save_data(data)
        await m.answer("Добавлен")
    except:
        await m.answer("Формат: /add_user ID")

@router.message(Command("del_user"))
async def del_user(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(m.text.split()[1])
        if user_id in data["users"]:
            data["users"].remove(user_id)
            save_data(data)
        await m.answer("Удалён")
    except:
        await m.answer("Формат: /del_user ID")

# ------------------ RUN ------------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())