import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 470343161

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())


# ----------------------------
# ДАННЫЕ КУРСОВ (file_id вставляются вручную)
# ----------------------------
COURSES = {
    "warmup": {
        "title": "Разогрев",
        "videos": [
            {"title": "Разогрев 1", "file_id": "FILE_ID_1"},
            {"title": "Разогрев 2", "file_id": "FILE_ID_2"},
        ]
    },
    "speech": {
        "title": "Рабочие звуки/звонкие качества",
        "videos": [
            {"title": "Сила голоса", "file_id": "FILE_ID_3"},
            {"title": "Резонаторы", "file_id": "FILE_ID_4"},
        ]
    },
    "belting": {
        "title": "Народный/Бэлтинг",
        "videos": [
            {"title": "Бэлтинг база", "file_id": "FILE_ID_5"},
        ]
    },
    "vocal": {
        "title": "Вокальные упражнения",
        "videos": [
            {"title": "Упражнение 1", "file_id": "FILE_ID_6"},
        ]
    }
}

# ----------------------------
# ХРАНИЛИЩЕ ПОЛЬЗОВАТЕЛЕЙ (в памяти)
# ----------------------------
users = set()

# ----------------------------
# FSM
# ----------------------------
class CourseState(StatesGroup):
    choosing = State()
    in_course = State()


# ----------------------------
# UI
# ----------------------------
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Разогрев")],
        [KeyboardButton(text="Рабочие звуки/звонкие качества")],
        [KeyboardButton(text="Народный/Бэлтинг")],
        [KeyboardButton(text="Вокальные упражнения")],
    ],
    resize_keyboard=True
)


def progress_bar(index, total):
    filled = "█" * (index + 1)
    empty = "░" * (total - index - 1)
    return f"{filled}{empty} {index + 1}/{total}"


def get_nav_kb(course_key, index, total):
    buttons = []

    if index < total - 1:
        buttons.append(
            InlineKeyboardButton(text="Дальше", callback_data=f"next:{course_key}:{index}")
        )
    else:
        buttons.append(
            InlineKeyboardButton(text="Завершить", callback_data=f"finish:{course_key}")
        )

    return InlineKeyboardMarkup(inline_keyboard=[buttons])


# ----------------------------
# UTILS
# ----------------------------
async def typing(message: Message, text: str, delay: float = 0.8):
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(delay)
    await message.answer(text)


def is_admin(user_id: int):
    return user_id == ADMIN_ID


def is_allowed(user_id: int):
    return user_id in users or is_admin(user_id)


# ----------------------------
# START
# ----------------------------
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.answer("Доступ ограничен.")
        return

    await state.set_state(CourseState.choosing)

    await typing(message, "Привет 👋")
    await typing(message, "Выбери блок:")
    await message.answer("👇", reply_markup=main_kb)


# ----------------------------
# ВЫБОР БЛОКА
# ----------------------------
@dp.message(F.text.in_({
    "Разогрев",
    "Рабочие звуки/звонкие качества",
    "Народный/Бэлтинг",
    "Вокальные упражнения"
}))
async def select_course(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return

    for key, data in COURSES.items():
        if data["title"] == message.text:
            await state.update_data(course=key, index=0)
            await state.set_state(CourseState.in_course)

            await send_video(message, key, 0)
            return


# ----------------------------
# ОТПРАВКА ВИДЕО
# ----------------------------
async def send_video(message: Message, course_key: str, index: int):
    course = COURSES[course_key]
    video = course["videos"][index]

    caption = (
        f"<b>{video['title']}</b>\n\n"
        f"{progress_bar(index, len(course['videos']))}"
    )

    await message.answer_video(
        video=video["file_id"],
        caption=caption,
        reply_markup=get_nav_kb(course_key, index, len(course["videos"]))
    )


# ----------------------------
# CALLBACK NEXT
# ----------------------------
@dp.callback_query(F.data.startswith("next"))
async def next_video(call: CallbackQuery, state: FSMContext):
    _, course_key, index = call.data.split(":")
    index = int(index) + 1

    await state.update_data(index=index)

    await call.message.delete()
    await send_video(call.message, course_key, index)

    await call.answer()


# ----------------------------
# CALLBACK FINISH
# ----------------------------
@dp.callback_query(F.data.startswith("finish"))
async def finish_course(call: CallbackQuery, state: FSMContext):
    course_key = call.data.split(":")[1]

    next_map = {
        "warmup": "speech",
        "speech": "belting",
        "belting": "vocal",
        "vocal": None
    }

    await call.message.delete()

    next_course = next_map.get(course_key)

    if next_course:
        await call.message.answer(
            f"Блок завершён. Переход к следующему: <b>{COURSES[next_course]['title']}</b>"
        )
        await state.update_data(course=next_course, index=0)
        await send_video(call.message, next_course, 0)
    else:
        await call.message.answer("<b>Курс полностью завершён.</b> Финальный этап пройден.")


# ----------------------------
# ADMIN PANEL
# ----------------------------
@dp.message(Command("admin"))
async def admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "ADMIN PANEL:\n"
        "/add_user ID\n"
        "/remove_user ID"
    )


@dp.message(Command("add_user"))
async def add_user(message: Message):
    if not is_admin(message.from_user.id):
        return

    try:
        uid = int(message.text.split()[1])
        users.add(uid)
        await message.answer(f"User {uid} добавлен")
    except:
        await message.answer("Ошибка")


@dp.message(Command("remove_user"))
async def remove_user(message: Message):
    if not is_admin(message.from_user.id):
        return

    try:
        uid = int(message.text.split()[1])
        users.discard(uid)
        await message.answer(f"User {uid} удалён")
    except:
        await message.answer("Ошибка")


# ----------------------------
# RUN
# ----------------------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())