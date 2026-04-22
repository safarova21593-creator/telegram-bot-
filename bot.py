import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

ADMIN_ID = 470343161

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

users = {ADMIN_ID}

# ------------------- COURSES -------------------

COURSES = {
    "warmup": {
        "title": "Разогрев",
        "videos": [
            ("Трель", "BAACAgIAAxkBAAICvmmHnO8V9I3oytM_0IiWhjMTdJp-AAJ6qAACd5hBSKlSxJmdQJHBOgQ"),
            ("Сирена", "BAACAgIAAxkBAAIDIGmI_kAdS8HC05EHgVyGq9jQVaQoAAJQhQACV81JSEiL0QG73KRUOgQ"),
            ("Режимы работы голосовых складок", "BAACAgIAAxkBAAIFbWng_qo7u6OwFP5K_h-GczbCQcC8AAKAnQACU0kIS8ZNCKOp2pSzOwQ"),
            ("Мягкое небо", "BAACAgIAAxkBAAIHNGnhXL3xHKjyivh9gSnrA0Jse3GzAALdkwACU0kQS34mCZVfDDTvOwQ"),
            ("NG", "BAACAgIAAxkBAAIDH2mI-58aJh8VzvCnxpHtu9hxj0QhAAI5hQACV81JSDK87Yy0XYZdOgQ"),
            ("ng A ng Э", "BAACAgIAAxkBAAIEymneqa_G3NtmM8dMxpPONroNQ5U7AAK4lAACYBLxSuqWnm-uZl18OwQ"),
        ],
        "next": "speech"
    },

    "speech": {
        "title": "Рабочие звуки/звонкие качества",
        "videos": [
            ("Основные рабочие звуки А-И-У", "BAACAgIAAxkBAAIFumnhHaYAAbSLYje2d_N4qXiqopvf-AACE5IAAlNJEEsYt2qZlJZTgDsE"),
            ("Звонкие качества", "BAACAgIAAxkBAAII92nhfu2ymq0kDxyoMFZzMzE289HsAAISlAACU0kQS5YS6-tgJdcyOwQ"),
            ("ГА ГА ГА, НА НА НА", "BAACAgIAAxkBAAIFxGnhJjXXG37cJfTWg273_KUveChxAAJtkgACU0kQSzn02yOQpEhqOwQ"),
            ("НИ НЭ НА НО НУ", "BAACAgIAAxkBAAIF2WnhM-7P38m-B0bGRnTgXnjwaCCKAAISkwACU0kQS3g6-k1iAQt0OwQ"),
            ("Папайя", "BAACAgIAAxkBAAIF8GnhOty0hfema_C2945TJ3kRNfgQAAJYkwACU0kQSwcyvjHbyS5OOwQ"),
            ("Пицца", "BAACAgIAAxkBAAIGAAFp4T5pkmCPmMpA_K3_sWJ10OnAaQACcZMAAlNJEEtKFEH1OPL8EjsE"),
            ("Не мни мне мини", "BAACAgIAAxkBAAIGC2nhQso05PaTOuxMqgbfmUWKu4vxAAKDkwACU0kQS-5qfczcBdYHOwQ"),
        ],
        "next": "belting"
    },

    "belting": {
        "title": "Народный/Бэлтинг",
        "videos": [
            ("Народный звук (Бэлтинг)", "BAACAgIAAxkBAAIGMWnhRgSBfkkdzEi3cD4n4yJtEXDgAAKMkwACU0kQS3E571ltEh5sOwQ"),
            ("Народный Э", "BAACAgIAAxkBAAIGUmnhSHqm0EHi9zr-xIMSYOGxVI-9AAKRkwACU0kQSzHyfk-FkhYYOwQ"),
            ("Народный О", "BAACAgIAAxkBAAIGWGnhUD31UYfwrNP7fGRatPn43RISAAKikwACU0kQS6RupTxsjvjcOwQ"),
            ("Стабильность народного звука", "BAACAgIAAxkBAAIGXGnhUIQJ0wHK3IzB1cALXp_wzQl_AAKlkwACU0kQS-5wZs_ul8x1OwQ"),
        ],
        "next": "vocal"
    },

    "vocal": {
        "title": "Вокальные упражнения",
        "videos": [
            ("Я не боюсь темноты", "BAACAgIAAxkBAAIGemnhUiaMGOab8Ngh5ki6b1aQHwJMAAKvkwACU0kQS_mkx39_mJTAOwQ"),
            ("Доброе утро", "BAACAgIAAxkBAAIGfmnhUrpdHCBV1an_Ka86Zz8EVBUHAAKxkwACU0kQS0U45H9dPJY4OwQ"),
            ("За волной волна", "BAACAgIAAxkBAAIGgmnhUx6A5owEQmTRrxoQlaKWCLCEAAKykwACU0kQS8vGmN3mpHqgOwQ"),
            ("Фифа", "BAACAgIAAxkBAAIGhmnhVGbMXxnIkK_POOn1yfzDxWmdAAK_kwACU0kQSwMyG1UvEm1vOwQ"),
            ("Как легко", "BAACAgIAAxkBAAIGimnhVOfQLrZYuaOwukhZ9LktdCFzAALDkwACU0kQS8d1HWfJFB1mOwQ"),
        ],
        "next": None
    }
}

# ------------------- UI -------------------

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Разогрев")],
        [KeyboardButton(text="Рабочие звуки/звонкие качества")],
        [KeyboardButton(text="Народный/Бэлтинг")],
        [KeyboardButton(text="Вокальные упражнения")],
    ],
    resize_keyboard=True
)

class StateData(StatesGroup):
    course = State()
    index = State()

def allowed(uid):
    return uid in users

def nav(course, idx):
    videos = COURSES[course]["videos"]
    if idx < len(videos) - 1:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton("Дальше", callback_data=f"next:{course}:{idx}")]]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("Завершить", callback_data=f"finish:{course}")]]
    )

def progress(idx, total):
    return f"{'█'*(idx+1)}{'░'*(total-idx-1)} {idx+1}/{total}"

# ------------------- START -------------------

@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    if not allowed(m.from_user.id):
        await m.answer("Доступ закрыт.")
        return

    await state.clear()
    await m.answer(f"Привет, {m.from_user.first_name} 👋")
    await m.answer("Выбери блок:", reply_markup=kb)

# ------------------- SELECT -------------------

@dp.message(F.text)
async def select(m: Message, state: FSMContext):
    if not allowed(m.from_user.id):
        return

    for key, data in COURSES.items():
        if data["title"] == m.text:
            await state.update_data(course=key, index=0)
            await send_video(m, key, 0)
            return

# ------------------- SEND VIDEO -------------------

async def send_video(target, course, idx):
    title, vid = COURSES[course]["videos"][idx]

    await target.answer_video(
        video=vid,
        caption=f"<b>{title}</b>\n\n{progress(idx, len(COURSES[course]['videos']))}",
        reply_markup=nav(course, idx)
    )

# ------------------- NEXT -------------------

@dp.callback_query(F.data.startswith("next"))
async def next(call: CallbackQuery, state: FSMContext):
    _, course, idx = call.data.split(":")
    idx = int(idx) + 1

    await state.update_data(course=course, index=idx)

    await call.message.delete()
    await send_video(call.message, course, idx)
    await call.answer()

# ------------------- FINISH -------------------

@dp.callback_query(F.data.startswith("finish"))
async def finish(call: CallbackQuery, state: FSMContext):
    _, course = call.data.split(":")

    user = call.from_user.first_name
    next_course = COURSES[course]["next"]

    await call.message.delete()

    # --- Warmup finish ---
    if course == "warmup":
        await call.message.answer(f"{user}, переходи к следующему блоку➡️")

    # --- Speech finish ---
    elif course == "speech":
        await call.message.answer(f"{user}, двигайся к следующему блоку➡️")

    # --- Belting finish ---
    elif course == "belting":
        await call.message.answer(
            'Пришло время реализовать полученные навыки на практике, переходи к блоку "Вокальные упражнения"🎤'
        )

    # --- Vocal finish ---
    elif course == "vocal":
        await call.message.answer(
            f"{user}, поздравляю с завершением тренировки!\n"
            "Для закрепления стойкого результата делайте эти практики регулярно.\n\n"
            "<b>С заботой о Вас, Юлия Золотых❤️</b>"
        )
        await state.clear()
        await call.answer()
        return

    # auto next course
    if next_course:
        await state.update_data(course=next_course, index=0)
        await send_video(call.message, next_course, 0)

    await call.answer()

# ------------------- RUN -------------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())