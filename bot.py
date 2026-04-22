import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = os.getenv("DATA_FILE", "data.json")

if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не найдена")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

BLOCKS = {
    "warmup": "1️⃣ Разогрев",
    "voice": "2️⃣ Рабочие звуки/звонкие качества",
    "belt": "3️⃣ Народный/Бэлтинг",
    "practice": "4️⃣ Вокальные упражнения",
}

BLOCK_ALIASES = {v: k for k, v in BLOCKS.items()}


def default_data() -> Dict[str, Any]:
    return {
        "allowed_users": [470343161],
        "videos": {
            "warmup": [],
            "voice": [],
            "belt": [],
            "practice": [],
        },
    }


def ensure_data_shape(data: Dict[str, Any]) -> Dict[str, Any]:
    if "allowed_users" not in data or not isinstance(data["allowed_users"], list):
        data["allowed_users"] = [470343161]

    if "videos" not in data or not isinstance(data["videos"], dict):
        # поддержка старого формата
        old = {k: data.get(k, []) for k in BLOCKS.keys()}
        data = {
            "allowed_users": data.get("allowed_users", [470343161]),
            "videos": old,
        }

    for block in BLOCKS.keys():
        data["videos"].setdefault(block, [])

    return data


def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        data = default_data()
        save_data(data)
        return data

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return ensure_data_shape(raw)


def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


DATA = load_data()
admin_state: Dict[int, Dict[str, Any]] = {}


def get_allowed_users() -> set[int]:
    return {int(x) for x in DATA.get("allowed_users", [])}


def is_admin(user_id: int) -> bool:
    users = get_allowed_users()
    if not users:
        return False
    return user_id == min(users)


def has_access(user_id: int) -> bool:
    return user_id in get_allowed_users()


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=name)] for name in BLOCKS.values()],
        resize_keyboard=True,
    )


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel")]]
    )


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Добавить видео", callback_data="admin:add_video")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users")],
            [InlineKeyboardButton(text="📂 Видео по блокам", callback_data="admin:list_blocks")],
        ]
    )


def admin_users_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="admin:user_add")],
            [InlineKeyboardButton(text="➖ Удалить пользователя", callback_data="admin:user_remove")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")],
        ]
    )


def admin_blocks_kb(prefix: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=title, callback_data=f"{prefix}:{key}")] for key, title in BLOCKS.items()]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def video_manage_kb(block: str, index: int, last: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="✅ Завершить" if last else "➡️ Дальше",
                callback_data=f"next:{block}:{index}",
            )
        ]
    ]
    if is_admin_view_block(block):
        pass
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_video_item_kb(block: str, index: int, total: int) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    nav_row: List[InlineKeyboardButton] = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:view:{block}:{index-1}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:view:{block}:{index+1}"))
    if nav_row:
        rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="🗑 Удалить видео", callback_data=f"admin:delete_video:{block}:{index}")])
    rows.append([InlineKeyboardButton(text="⬅️ К блокам", callback_data="admin:list_blocks")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_next(block: str, index: int) -> InlineKeyboardMarkup:
    total = len(DATA["videos"].get(block, []))
    last = index >= total - 1
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Завершить" if last else "Дальше",
                    callback_data=f"next:{block}:{index}",
                )
            ]
        ]
    )


def progress_text(block: str, index: int) -> str:
    total = len(DATA["videos"].get(block, []))
    if total == 0:
        return "0/0"
    done = index + 1
    bar = "🟩" * done + "⬜" * (total - done)
    return f"{bar} {done}/{total}"


def users_text() -> str:
    users = sorted(get_allowed_users())
    lines = ["<b>Список пользователей с доступом</b>"]
    for uid in users:
        role = " — админ" if is_admin(uid) else ""
        lines.append(f"• <code>{uid}</code>{role}")
    return "\n".join(lines)


def is_admin_view_block(block: str) -> bool:
    return block in BLOCKS


async def show_admin_panel(target: Message | CallbackQuery) -> None:
    text = (
        "<b>Админ-панель</b>\n\n"
        "Здесь можно:\n"
        "• добавлять видео\n"
        "• добавлять и удалять пользователей\n"
        "• просматривать и удалять видео из блоков"
    )
    if isinstance(target, Message):
        await target.answer(text, reply_markup=admin_main_kb())
    else:
        if target.message and target.message.video:
            await target.message.answer(text, reply_markup=admin_main_kb())
        else:
            await target.message.edit_text(text, reply_markup=admin_main_kb())


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    user_id = message.from_user.id
    if not has_access(user_id):
        await message.answer("Доступ к боту ограничен. Обратитесь к администратору.")
        return

    await message.answer(f"Привет, {message.from_user.first_name}!")
    await asyncio.sleep(1)
    await message.answer("Выбери блок:", reply_markup=main_kb())


@dp.message(Command("admin"))
async def admin_handler(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return
    await show_admin_panel(message)


@dp.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await show_admin_panel(call)
    await call.answer()


@dp.callback_query(F.data == "admin:cancel")
async def admin_cancel(call: CallbackQuery) -> None:
    admin_state.pop(call.from_user.id, None)
    await call.message.edit_text("Действие отменено.", reply_markup=admin_main_kb())
    await call.answer("Отменено")


@dp.callback_query(F.data == "admin:add_video")
async def admin_add_video(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    admin_state[call.from_user.id] = {"action": "add_video", "step": "wait_video"}
    await call.message.edit_text(
        "Отправьте видео, которое нужно добавить.",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@dp.callback_query(F.data == "admin:users")
async def admin_users(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await call.message.edit_text(users_text(), reply_markup=admin_users_kb())
    await call.answer()


@dp.callback_query(F.data == "admin:user_add")
async def admin_user_add(call: CallbackQuery) -> None:
    admin_state[call.from_user.id] = {"action": "user_add", "step": "wait_user_id"}
    await call.message.edit_text(
        "Введите Telegram ID пользователя, которому нужно открыть доступ.",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@dp.callback_query(F.data == "admin:user_remove")
async def admin_user_remove(call: CallbackQuery) -> None:
    admin_state[call.from_user.id] = {"action": "user_remove", "step": "wait_user_id"}
    await call.message.edit_text(
        "Введите Telegram ID пользователя, которого нужно удалить из доступа.",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@dp.callback_query(F.data == "admin:list_blocks")
async def admin_list_blocks(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    lines = ["<b>Блоки с видео</b>"]
    for key, title in BLOCKS.items():
        count = len(DATA["videos"].get(key, []))
        lines.append(f"• {title} — {count}")

    await call.message.edit_text("\n".join(lines), reply_markup=admin_blocks_kb("admin:block"))
    await call.answer()


@dp.callback_query(F.data.startswith("admin:block:"))
async def admin_open_block(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    block = call.data.split(":", 2)[2]
    items = DATA["videos"].get(block, [])
    if not items:
        await call.answer("В этом блоке пока нет видео", show_alert=True)
        return

    await send_admin_video_preview(call, block, 0)
    await call.answer()


@dp.callback_query(F.data.startswith("admin:view:"))
async def admin_view_video(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    _, _, block, index = call.data.split(":")
    await send_admin_video_preview(call, block, int(index))
    await call.answer()


@dp.callback_query(F.data.startswith("admin:delete_video:"))
async def admin_delete_video(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    _, _, _, block, index = call.data.split(":")
    index = int(index)
    items = DATA["videos"].get(block, [])

    if not (0 <= index < len(items)):
        await call.answer("Видео не найдено", show_alert=True)
        return

    removed = items.pop(index)
    save_data(DATA)

    if items:
        new_index = min(index, len(items) - 1)
        await call.message.answer(f"Удалено: <b>{removed['title']}</b>")
        await send_admin_video_preview(call, block, new_index)
    else:
        await call.message.answer(f"Удалено: <b>{removed['title']}</b>")
        await call.message.answer("В этом блоке больше нет видео.", reply_markup=admin_blocks_kb("admin:block"))

    await call.answer("Удалено")


@dp.message(F.video)
async def admin_receive_video(message: Message) -> None:
    user_id = message.from_user.id
    state = admin_state.get(user_id)

    if not is_admin(user_id):
        return

    if not state or state.get("action") != "add_video" or state.get("step") != "wait_video":
        return

    state["file_id"] = message.video.file_id
    state["step"] = "wait_title"
    await message.answer("Теперь отправьте название видео.", reply_markup=cancel_kb())


@dp.message(F.text)
async def text_router(message: Message) -> None:
    user_id = message.from_user.id

    if message.text in BLOCK_ALIASES:
        if not has_access(user_id):
            await message.answer("Доступ к боту ограничен. Обратитесь к администратору.")
            return
        block = BLOCK_ALIASES[message.text]
        await send_video(message, block, 0)
        return

    if not is_admin(user_id):
        return

    state = admin_state.get(user_id)
    if not state:
        return

    action = state.get("action")
    step = state.get("step")
    text = (message.text or "").strip()

    if action == "add_video" and step == "wait_title":
        state["title"] = text
        state["step"] = "wait_block"
        await message.answer(
            "Выберите блок для этого видео:",
            reply_markup=admin_blocks_kb("admin:save_video"),
        )
        return

    if action == "user_add" and step == "wait_user_id":
        if not text.isdigit():
            await message.answer("Нужно отправить только числовой Telegram ID.", reply_markup=cancel_kb())
            return

        new_user_id = int(text)
        allowed = get_allowed_users()
        if new_user_id in allowed:
            admin_state.pop(user_id, None)
            await message.answer("Этот пользователь уже есть в списке доступа.", reply_markup=admin_users_kb())
            return

        DATA["allowed_users"].append(new_user_id)
        DATA["allowed_users"] = sorted(set(DATA["allowed_users"]))
        save_data(DATA)
        admin_state.pop(user_id, None)
        await message.answer(
            f"Пользователь <code>{new_user_id}</code> добавлен.",
            reply_markup=admin_users_kb(),
        )
        return

    if action == "user_remove" and step == "wait_user_id":
        if not text.isdigit():
            await message.answer("Нужно отправить только числовой Telegram ID.", reply_markup=cancel_kb())
            return

        remove_user_id = int(text)
        if is_admin(remove_user_id):
            await message.answer("Главного администратора удалять нельзя.", reply_markup=admin_users_kb())
            admin_state.pop(user_id, None)
            return

        if remove_user_id not in get_allowed_users():
            await message.answer("Такого пользователя нет в списке доступа.", reply_markup=admin_users_kb())
            admin_state.pop(user_id, None)
            return

        DATA["allowed_users"] = [uid for uid in DATA["allowed_users"] if int(uid) != remove_user_id]
        save_data(DATA)
        admin_state.pop(user_id, None)
        await message.answer(
            f"Пользователь <code>{remove_user_id}</code> удалён.",
            reply_markup=admin_users_kb(),
        )
        return


@dp.callback_query(F.data.startswith("admin:save_video:"))
async def admin_save_video(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    block = call.data.split(":", 2)[2]
    state = admin_state.get(call.from_user.id)

    if not state or state.get("action") != "add_video":
        await call.answer("Сессия добавления не найдена", show_alert=True)
        return

    file_id = state.get("file_id")
    title = state.get("title")

    if not file_id or not title:
        await call.answer("Не хватает данных для сохранения", show_alert=True)
        return

    DATA["videos"].setdefault(block, []).append({
        "title": title,
        "video": file_id,
    })
    save_data(DATA)
    admin_state.pop(call.from_user.id, None)

    await call.message.edit_text(
        f"Сохранено в блок <b>{BLOCKS[block]}</b>:\n• {title}",
        reply_markup=admin_main_kb(),
    )
    await call.answer("Видео сохранено")


async def send_video(message_or_call: Message | CallbackQuery, block: str, index: int) -> None:
    user_id = message_or_call.from_user.id
    items = DATA["videos"].get(block, [])

    if not items:
        await bot.send_message(user_id, "В этом блоке пока нет упражнений.")
        return

    if not (0 <= index < len(items)):
        await bot.send_message(user_id, "Видео не найдено.")
        return

    item = items[index]
    caption = f"<b>{item['title']}</b>\n\n{progress_text(block, index)}"

    await bot.send_video(
        chat_id=user_id,
        video=item["video"],
        caption=caption,
        reply_markup=inline_next(block, index),
        protect_content=True,
    )


async def send_admin_video_preview(call: CallbackQuery, block: str, index: int) -> None:
    items = DATA["videos"].get(block, [])
    if not items:
        await call.message.answer("В этом блоке нет видео.", reply_markup=admin_blocks_kb("admin:block"))
        return

    item = items[index]
    caption = (
        f"<b>{item['title']}</b>\n"
        f"Блок: {BLOCKS[block]}\n"
        f"Позиция: {index + 1}/{len(items)}"
    )

    await call.message.answer_video(
        video=item["video"],
        caption=caption,
        reply_markup=admin_video_item_kb(block, index, len(items)),
        protect_content=False,
    )


@dp.callback_query(F.data.startswith("next:"))
async def next_step(call: CallbackQuery) -> None:
    if not has_access(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    _, block, idx = call.data.split(":")
    idx = int(idx)
    next_idx = idx + 1
    items = DATA["videos"].get(block, [])

    if next_idx < len(items):
        await send_video(call, block, next_idx)
    else:
        await bot.send_message(call.from_user.id, "Блок завершён ✅")

    await call.answer()


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
