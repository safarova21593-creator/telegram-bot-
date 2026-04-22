import asyncio
import logging
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

# -------------------- TOKEN --------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в переменных окружения")

# -------------------- INIT --------------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# -------------------- STORAGE --------------------

DATA_FILE = "data.json"

DEFAULT_DATA = {
    "admins": [470343161],   # основной админ
    "users": [470343161],    # разрешённые пользователи
    "videos": {
        "warmup": [],
        "voice": [],
        "belt": [],
        "practice": []
    }
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # подстраховка на случай старого файла
    if "admins" not in data:
        data["admins"] = [470343161]
    if "users" not in data:
        data["users"] = [470343161]
    if "videos" not in data:
        data["videos"] = {
            "warmup": [],
            "voice": [],
            "belt": [],
            "practice": []
        }

    for block in ["warmup", "voice", "belt", "practice"]:
        data["videos"].setdefault(block, [])

    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


DATA = load_data()

# -------------------- STATE --------------------

user_state = {}
admin_state = {}

# admin_state structure examples:
# {
#   user_id: {
#       "action": "add_video_wait_video"
#   }
# }
#
# {
#   user_id: {
#       "action": "add_video_wait_title",
#       "file_id": "..."
#   }
# }
#
# {
#   user_id: {
#       "action": "add_video_wait_block",
#       "file_id": "...",
#       "title": "..."
#   }
# }
#
# {
#   user_id: {
#       "action": "add_user_wait_id"
#   }
# }
#
# {
#   user_id: {
#       "action": "remove_user_wait_id"
#   }
# }


def is_admin(user_id: int) -> bool:
    return user_id in DATA["admins"]


def is_allowed(user_id: int) -> bool:
    return user_id in DATA["users"] or is_admin(user_id)


# -------------------- TEXTS --------------------

BLOCK_NAMES = {
    "warmup": "Разогрев",
    "voice": "Рабочие звуки/звонкие качества",
    "belt": "Народный/Бэлтинг",
    "practice": "Вокальные упражнения"
}

USER_BUTTON_TO_BLOCK = {
    "1️⃣ Разогрев": "warmup",
    "2️⃣ Рабочие звуки/звонкие качества": "voice",
    "3️⃣ Народный/Бэлтинг": "belt",
    "4️⃣ Вокальные упражнения": "practice"
}

BLOCK_CALLBACK_TO_KEY = {
    "warmup": "warmup",
    "voice": "voice",
    "belt": "belt",
    "practice": "practice"
}

# -------------------- KEYBOARDS --------------------

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
    last = index >= len(DATA["videos"].get(block, [])) - 1
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Завершить" if last else "Дальше",
                    callback_data=f"next:{block}:{index}"
                )
            ]
        ]
    )


def admin_main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить видео", callback_data="admin:add_video")],
            [InlineKeyboardButton(text="📋 Список видео", callback_data="admin:list_videos")],
            [InlineKeyboardButton(text="👤 Добавить пользователя", callback_data="admin:add_user")],
            [InlineKeyboardButton(text="🗑 Удалить пользователя", callback_data="admin:remove_user")],
            [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin:list_users")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin:close")]
        ]
    )


def choose_block_kb(prefix: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Разогрев", callback_data=f"{prefix}:warmup")],
            [InlineKeyboardButton(text="Рабочие звуки/звонкие качества", callback_data=f"{prefix}:voice")],
            [InlineKeyboardButton(text="Народный/Бэлтинг", callback_data=f"{prefix}:belt")],
            [InlineKeyboardButton(text="Вокальные упражнения", callback_data=f"{prefix}:practice")],
            [InlineKeyboardButton(text="⬅ Назад в админку", callback_data="admin:back")]
        ]
    )


def video_manage_kb(block: str, index: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Удалить видео",
                    callback_data=f"admin_delete_video:{block}:{index}"
                )
            ],
            [InlineKeyboardButton(text="⬅ К блокам", callback_data="admin:list_videos")]
        ]
    )


def progress_text(block, index):
    total = len(DATA["videos"].get(block, []))
    if total == 0:
        return "0/0"
    done = index + 1
    bar = "🟩" * done + "⬜" * (total - done)
    return f"{bar} {done}/{total}"


# -------------------- START --------------------

@dp.message(CommandStart())
async def start(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Доступ к боту ограничен, обратитесь к администратору")
        return

    await message.answer(f"Привет, {message.from_user.first_name}")
    await asyncio.sleep(1)
    await message.answer("Выбери блок:", reply_markup=main_kb)


# -------------------- ADMIN PANEL --------------------

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели")
        return

    await message.answer(
        "Админ-панель",
        reply_markup=admin_main_kb()
    )


@dp.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    admin_state.pop(call.from_user.id, None)

    await call.message.edit_text(
        "Админ-панель",
        reply_markup=admin_main_kb()
    )
    await call.answer()


@dp.callback_query(F.data == "admin:close")
async def admin_close(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    admin_state.pop(call.from_user.id, None)
    await call.message.edit_text("Админ-панель закрыта")
    await call.answer()


# -------------------- ADMIN: ADD VIDEO --------------------

@dp.callback_query(F.data == "admin:add_video")
async def admin_add_video(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    admin_state[call.from_user.id] = {"action": "add_video_wait_video"}

    await call.message.edit_text(
        "Отправьте видео для добавления.\n\nПосле этого бот попросит ввести название.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="admin:back")]
            ]
        )
    )
    await call.answer()


@dp.message(F.video)
async def receive_video(message: Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    state = admin_state.get(user_id)
    if not state or state.get("action") != "add_video_wait_video":
        return

    admin_state[user_id] = {
        "action": "add_video_wait_title",
        "file_id": message.video.file_id
    }

    await message.answer("Введите название видео")


@dp.message(F.text)
async def admin_text_flow(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # -------- USER ACCESS CHECK --------
    if not is_allowed(user_id):
        await message.answer("Доступ к боту ограничен, обратитесь к администратору")
        return

    # -------- ADMIN STATES --------
    if is_admin(user_id):
        state = admin_state.get(user_id)

        if state:
            action = state.get("action")

            if action == "add_video_wait_title":
                admin_state[user_id] = {
                    "action": "add_video_wait_block",
                    "file_id": state["file_id"],
                    "title": text
                }

                await message.answer(
                    f"Название сохранено: {text}\n\nТеперь выберите блок:",
                    reply_markup=choose_block_kb("admin_choose_block")
                )
                return

            if action == "add_user_wait_id":
                try:
                    new_user_id = int(text)
                except ValueError:
                    await message.answer("Нужно отправить числовой user_id")
                    return

                if new_user_id not in DATA["users"]:
                    DATA["users"].append(new_user_id)
                    save_data(DATA)
                    await message.answer(f"Пользователь {new_user_id} добавлен")
                else:
                    await message.answer("Этот пользователь уже есть в списке")

                admin_state.pop(user_id, None)
                await message.answer("Админ-панель", reply_markup=admin_main_kb())
                return

            if action == "remove_user_wait_id":
                try:
                    remove_user_id = int(text)
                except ValueError:
                    await message.answer("Нужно отправить числовой user_id")
                    return

                if remove_user_id in DATA["admins"]:
                    await message.answer("Нельзя удалить администратора")
                    return

                if remove_user_id in DATA["users"]:
                    DATA["users"].remove(remove_user_id)
                    save_data(DATA)
                    await message.answer(f"Пользователь {remove_user_id} удалён")
                else:
                    await message.answer("Такого пользователя нет в списке")

                admin_state.pop(user_id, None)
                await message.answer("Админ-панель", reply_markup=admin_main_kb())
                return

    # -------- USER MENU --------
    if text in USER_BUTTON_TO_BLOCK:
        block = USER_BUTTON_TO_BLOCK[text]
        await send_video(message, block, 0)
        return

    # -------- FALLBACK --------
    await message.answer("Выбери нужный блок из меню")


@dp.callback_query(F.data.startswith("admin_choose_block:"))
async def admin_choose_block(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    state = admin_state.get(call.from_user.id)
    if not state or state.get("action") != "add_video_wait_block":
        await call.answer("Сначала добавьте видео заново")
        return

    block = call.data.split(":")[1]

    DATA["videos"].setdefault(block, []).append({
        "title": state["title"],
        "video": state["file_id"]
    })
    save_data(DATA)

    title = state["title"]
    admin_state.pop(call.from_user.id, None)

    await call.message.edit_text(
        f"Видео сохранено.\n\n"
        f"Название: {title}\n"
        f"Блок: {BLOCK_NAMES.get(block, block)}",
        reply_markup=admin_main_kb()
    )
    await call.answer()


# -------------------- ADMIN: USERS --------------------

@dp.callback_query(F.data == "admin:add_user")
async def admin_add_user(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    admin_state[call.from_user.id] = {"action": "add_user_wait_id"}

    await call.message.edit_text(
        "Отправьте user_id пользователя, которого нужно добавить.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="admin:back")]
            ]
        )
    )
    await call.answer()


@dp.callback_query(F.data == "admin:remove_user")
async def admin_remove_user(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    admin_state[call.from_user.id] = {"action": "remove_user_wait_id"}

    await call.message.edit_text(
        "Отправьте user_id пользователя, которого нужно удалить.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="admin:back")]
            ]
        )
    )
    await call.answer()


@dp.callback_query(F.data == "admin:list_users")
async def admin_list_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    users_text = "\n".join([str(uid) for uid in DATA["users"]]) if DATA["users"] else "Список пуст"
    admins_text = "\n".join([str(uid) for uid in DATA["admins"]]) if DATA["admins"] else "Список пуст"

    text = (
        f"Администраторы:\n{admins_text}\n\n"
        f"Пользователи:\n{users_text}"
    )

    await call.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="admin:back")]
            ]
        )
    )
    await call.answer()


# -------------------- ADMIN: VIDEO LIST --------------------

@dp.callback_query(F.data == "admin:list_videos")
async def admin_list_videos(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    await call.message.edit_text(
        "Выберите блок для просмотра видео:",
        reply_markup=choose_block_kb("admin_list_block")
    )
    await call.answer()


@dp.callback_query(F.data.startswith("admin_list_block:"))
async def admin_list_block(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    block = call.data.split(":")[1]
    items = DATA["videos"].get(block, [])

    if not items:
        await call.message.edit_text(
            f"В блоке «{BLOCK_NAMES.get(block, block)}» пока нет видео.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ К блокам", callback_data="admin:list_videos")],
                    [InlineKeyboardButton(text="⬅ В админку", callback_data="admin:back")]
                ]
            )
        )
        await call.answer()
        return

    text = [f"Блок: {BLOCK_NAMES.get(block, block)}", ""]
    for i, item in enumerate(items, start=1):
        text.append(f"{i}. {item['title']}")

    await call.message.edit_text(
        "\n".join(text),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть 1-е видео", callback_data=f"admin_open_video:{block}:0")],
                [InlineKeyboardButton(text="⬅ К блокам", callback_data="admin:list_videos")],
                [InlineKeyboardButton(text="⬅ В админку", callback_data="admin:back")]
            ]
        )
    )
    await call.answer()


@dp.callback_query(F.data.startswith("admin_open_video:"))
async def admin_open_video(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    _, block, idx = call.data.split(":")
    idx = int(idx)

    items = DATA["videos"].get(block, [])
    if idx >= len(items):
        await call.answer("Видео не найдено")
        return

    item = items[idx]

    text = (
        f"Видео #{idx + 1}\n"
        f"Блок: {BLOCK_NAMES.get(block, block)}\n"
        f"Название: {item['title']}"
    )

    buttons = []

    row = []
    if idx > 0:
        row.append(InlineKeyboardButton(text="⬅ Предыдущее", callback_data=f"admin_open_video:{block}:{idx-1}"))
    if idx < len(items) - 1:
        row.append(InlineKeyboardButton(text="Следующее ➡", callback_data=f"admin_open_video:{block}:{idx+1}"))
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🗑 Удалить это видео", callback_data=f"admin_delete_video:{block}:{idx}")])
    buttons.append([InlineKeyboardButton(text="⬅ К списку блока", callback_data=f"admin_list_block:{block}")])

    try:
        await bot.send_video(
            chat_id=call.from_user.id,
            video=item["video"],
            caption=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            protect_content=True
        )
        await call.answer("Видео отправлено")
    except Exception as e:
        logging.exception(e)
        await call.answer("Ошибка отправки видео")


@dp.callback_query(F.data.startswith("admin_delete_video:"))
async def admin_delete_video(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    _, block, idx = call.data.split(":")
    idx = int(idx)

    items = DATA["videos"].get(block, [])
    if idx >= len(items):
        await call.answer("Видео не найдено")
        return

    deleted = items.pop(idx)
    save_data(DATA)

    await call.message.answer(
        f"Удалено видео:\n{deleted['title']}"
    )

    remaining = DATA["videos"].get(block, [])
    if remaining:
        await call.message.answer(
            f"Осталось видео в блоке «{BLOCK_NAMES.get(block, block)}»: {len(remaining)}"
        )
    else:
        await call.message.answer(
            f"В блоке «{BLOCK_NAMES.get(block, block)}» больше нет видео"
        )

    await call.answer("Видео удалено")


# -------------------- BLOCK START --------------------

@dp.message(F.text == "1️⃣ Разогрев")
async def warmup(message: Message):
    await send_video(message, "warmup", 0)


@dp.message(F.text == "2️⃣ Рабочие звуки/звонкие качества")
async def voice(message: Message):
    await send_video(message, "voice", 0)


@dp.message(F.text == "3️⃣ Народный/Бэлтинг")
async def belt(message: Message):
    await send_video(message, "belt", 0)


@dp.message(F.text == "4️⃣ Вокальные упражнения")
async def practice(message: Message):
    await send_video(message, "practice", 0)


# -------------------- SEND VIDEO --------------------

async def send_video(message_or_call, block, index):
    user_id = message_or_call.from_user.id

    items = DATA["videos"].get(block, [])

    if not items:
        await bot.send_message(user_id, "В этом блоке пока нет упражнений")
        return

    if index < 0 or index >= len(items):
        await bot.send_message(user_id, "Видео не найдено")
        return

    item = items[index]
    caption = f"<b>{item['title']}</b>\n\n{progress_text(block, index)}"

    await bot.send_video(
        chat_id=user_id,
        video=item["video"],
        caption=caption,
        parse_mode="HTML",
        reply_markup=inline_next(block, index),
        protect_content=True
    )


# -------------------- CALLBACK NEXT --------------------

@dp.callback_query(F.data.startswith("next:"))
async def next_step(call: CallbackQuery):
    _, block, idx = call.data.split(":")
    idx = int(idx)

    next_idx = idx + 1
    items = DATA["videos"].get(block, [])

    if next_idx < len(items):
        await send_video(call, block, next_idx)
    else:
        await bot.send_message(call.from_user.id, "Блок завершён")

    await call.answer()


# -------------------- RUN --------------------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())