import asyncio
import json
import logging
import os
from typing import Any, Dict, List

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
from aiogram.exceptions import TelegramBadRequest

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

BLOCK_FINISH_MESSAGES = {
    "warmup": "{name}, переходи к следующему блоку2️⃣",
    "voice": "{name}, двигайся к следующему блоку3️⃣",
    "belt": 'Пришло время реализовать полученные навыки на практике, переходи к блоку "Вокальные упражнения"🎤',
    "practice": (
        "{name}, поздравляю с завершением тренировки!\n"
        "Для закрепления стойкого результата делайте эти практики регулярно.\n\n"
        "<b>С заботой о Вас, Юлия Золотых❤️</b>"
    ),
}

admin_state: Dict[int, Dict[str, Any]] = {}


def default_data() -> Dict[str, Any]:
    return {
        "allowed_users": [470343161],
        "videos": {
            "warmup": [
                {"title": "Трель", "video": "BAACAgIAAxkBAAICvmmHnO8V9I3oytM_0IiWhjMTdJp-AAJ6qAACd5hBSKlSxJmdQJHBOgQ"},
                {"title": "Сирена", "video": "BAACAgIAAxkBAAIDIGmI_kAdS8HC05EHgVyGq9jQVaQoAAJQhQACV81JSEiL0QG73KRUOgQ"},
                {"title": "Режимы работы голосовых складок", "video": "BAACAgIAAxkBAAIFbWng_qo7u6OwFP5K_h-GczbCQcC8AAKAnQACU0kIS8ZNCKOp2pSzOwQ"},
                {"title": "Мягкое небо", "video": "BAACAgIAAxkBAAIHNGnhXL3xHKjyivh9gSnrA0Jse3GzAALdkwACU0kQS34mCZVfDDTvOwQ"},
                {"title": "NG", "video": "BAACAgIAAxkBAAIDH2mI-58aJh8VzvCnxpHtu9hxj0QhAAI5hQACV81JSDK87Yy0XYZdOgQ"},
                {"title": "NG/A, NG/Э", "video": "BAACAgIAAxkBAAIEymneqa_G3NtmM8dMxpPONroNQ5U7AAK4lAACYBLxSuqWnm-uZl18OwQ"},
            ],
            "voice": [
                {"title": "Основные рабочие звуки А-И-У", "video": "BAACAgIAAxkBAAIFumnhHaYAAbSLYje2d_N4qXiqopvf-AACE5IAAlNJEEsYt2qZlJZTgDsE"},
                {"title": "Звонкие качества", "video": "BAACAgIAAxkBAAII92nhfu2ymq0kDxyoMFZzMzE289HsAAISlAACU0kQS5YS6-tgJdcyOwQ"},
                {"title": "ГА ГА ГА, НА НА НА", "video": "BAACAgIAAxkBAAIFxGnhJjXXG37cJfTWg273_KUveChxAAJtkgACU0kQSzn02yOQpEhqOwQ"},
                {"title": "НИ НЭ НА НО", "video": "BAACAgIAAxkBAAIF2WnhM-7P38m-B0bGRnTgXnjwaCCKAAISkwACU0kQS3g6-k1iAQt0OwQ"},
                {"title": "Папайя", "video": "BAACAgIAAxkBAAIF8GnhOty0hfema_C2945TJ3kRNfgQAAJYkwACU0kQSwcyvjHbyS5OOwQ"},
                {"title": "Пицца", "video": "BAACAgIAAxkBAAIGAAFp4T5pkmCPmMpA_K3_sWJ10OnAaQACcZMAAlNJEEtKFEH1OPL8EjsE"},
                {"title": "Не мни мне мини", "video": "BAACAgIAAxkBAAIGC2nhQso05PaTOuxMqgbfmUWKu4vxAAKDkwACU0kQS-5qfczcBdYHOwQ"},
            ],
            "belt": [
                {"title": "Народный звук (Бэлтинг), объяснение", "video": "BAACAgIAAxkBAAIGMWnhRgSBfkkdzEi3cD4n4yJtEXDgAAKMkwACU0kQS3E571ltEh5sOwQ"},
                {"title": "Народный Э", "video": "BAACAgIAAxkBAAIGUmnhSHqm0EHi9zr-xIMSYOGxVI-9AAKRkwACU0kQSzHyfk-FkhYYOwQ"},
                {"title": "Народный О", "video": "BAACAgIAAxkBAAIGWGnhUD31UYfwrNP7fGRatPn43RISAAKikwACU0kQS6RupTxsjvjcOwQ"},
                {"title": "Стабильность народного звука", "video": "BAACAgIAAxkBAAIGXGnhUIQJ0wHK3IzB1cALXp_wzQl_AAKlkwACU0kQS-5wZs_ul8x1OwQ"},
            ],
            "practice": [
                {"title": "Я не боюсь темноты", "video": "BAACAgIAAxkBAAIGemnhUiaMGOab8Ngh5ki6b1aQHwJMAAKvkwACU0kQS_mkx39_mJTAOwQ"},
                {"title": "Доброе утро", "video": "BAACAgIAAxkBAAIGfmnhUrpdHCBV1an_Ka86Zz8EVBUHAAKxkwACU0kQS0U45H9dPJY4OwQ"},
                {"title": "За волной волна", "video": "BAACAgIAAxkBAAIGgmnhUx6A5owEQmTRrxoQlaKWCLCEAAKykwACU0kQS8vGmN3mpHqgOwQ"},
                {"title": "Фифа", "video": "BAACAgIAAxkBAAIGhmnhVGbMXxnIkK_POOn1yfzDxWmdAAK_kwACU0kQSwMyG1UvEm1vOwQ"},
                {"title": "Как легко", "video": "BAACAgIAAxkBAAIGimnhVOfQLrZYuaOwukhZ9LktdCFzAALDkwACU0kQS8d1HWfJFB1mOwQ"},
            ],
        },
    }


def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_video_id(block: str, item: Dict[str, Any], index: int) -> str:
    title = str(item.get("title", "video")).strip().lower().replace(" ", "_")[:20]
    return f"{block}_{index + 1}_{title}"


def ensure_data_shape(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = default_data()

    if "allowed_users" not in data or not isinstance(data.get("allowed_users"), list):
        data["allowed_users"] = [470343161]

    if "videos" not in data or not isinstance(data.get("videos"), dict):
        old_videos = {}
        for block in BLOCKS:
            old_videos[block] = data.get(block, []) if isinstance(data.get(block, []), list) else []
        data = {"allowed_users": data.get("allowed_users", [470343161]), "videos": old_videos}

    for block in BLOCKS:
        items = data["videos"].get(block, [])
        if not isinstance(items, list):
            items = []
        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "Без названия")).strip()
            video = str(item.get("video", "")).strip()
            if not video:
                continue
            if not item.get("id"):
                item["id"] = generate_video_id(block, item, idx)
            normalized.append({
                "id": str(item["id"]),
                "title": title,
                "video": video,
            })
        data["videos"][block] = normalized

    data["allowed_users"] = sorted({int(x) for x in data.get("allowed_users", []) if str(x).isdigit() or isinstance(x, int)})
    if not data["allowed_users"]:
        data["allowed_users"] = [470343161]
    return data


def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        data = ensure_data_shape(default_data())
        save_data(data)
        return data

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    data = ensure_data_shape(raw)
    save_data(data)
    return data


DATA = load_data()


def get_allowed_users() -> set[int]:
    return {int(x) for x in DATA.get("allowed_users", [])}


def is_admin(user_id: int) -> bool:
    users = sorted(get_allowed_users())
    return bool(users) and user_id == users[0]


def has_access(user_id: int) -> bool:
    return user_id in get_allowed_users()


def user_name(message_or_call: Message | CallbackQuery) -> str:
    return (message_or_call.from_user.first_name or "Пользователь").strip()


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)] for text in BLOCKS.values()],
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
            [InlineKeyboardButton(text="🗑 Удалить пользователя", callback_data="admin:user_remove_list")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")],
        ]
    )


def admin_blocks_kb(prefix: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=title, callback_data=f"{prefix}:{block}")] for block, title in BLOCKS.items()]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_video_item_kb(block: str, item_id: str, index: int, total: int) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    nav: List[InlineKeyboardButton] = []
    if index > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:view:{block}:{index - 1}"))
    if index < total - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:view:{block}:{index + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🗑 Удалить видео", callback_data=f"admin:delete_video:{block}:{item_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ К блокам", callback_data="admin:list_blocks")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def users_text() -> str:
    users = sorted(get_allowed_users())
    lines = ["<b>Список пользователей с доступом</b>"]
    for uid in users:
        role = " — админ" if is_admin(uid) else ""
        lines.append(f"• <code>{uid}</code>{role}")
    return "\n".join(lines)


def user_remove_list_text() -> str:
    users = sorted(get_allowed_users())
    lines = ["<b>Выберите пользователя для удаления</b>"]
    for uid in users:
        role = " — админ" if is_admin(uid) else ""
        lines.append(f"• <code>{uid}</code>{role}")
    return "\n".join(lines)


def user_remove_list_kb() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for uid in sorted(get_allowed_users()):
        if is_admin(uid):
            continue
        rows.append([InlineKeyboardButton(text=str(uid), callback_data=f"admin:remove_user:{uid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def progress_text(block: str, index: int) -> str:
    total = len(DATA["videos"].get(block, []))
    if total == 0:
        return "0/0"
    done = index + 1
    return f"{'🟩' * done}{'⬜' * (total - done)} {done}/{total}"


def inline_next(block: str, index: int) -> InlineKeyboardMarkup:
    total = len(DATA["videos"].get(block, []))
    last = index >= total - 1
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Завершить" if last else "Дальше",
                callback_data=f"next:{block}:{index}",
            )
        ]]
    )


async def safe_edit_or_send(call: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    try:
        if call.message and not call.message.video:
            await call.message.edit_text(text, reply_markup=reply_markup)
        else:
            await call.message.answer(text, reply_markup=reply_markup)
            if call.message:
                with contextlib.suppress(Exception):
                    await call.message.delete()
    except Exception:
        await call.message.answer(text, reply_markup=reply_markup)


async def show_admin_panel(target: Message | CallbackQuery) -> None:
    text = (
        "<b>Админ-панель</b>\n\n"
        "Здесь можно:\n"
        "• добавлять видео\n"
        "• добавлять пользователей\n"
        "• удалять пользователей по кнопке\n"
        "• просматривать и удалять видео из блоков"
    )
    if isinstance(target, Message):
        await target.answer(text, reply_markup=admin_main_kb())
    else:
        try:
            if target.message and not target.message.video:
                await target.message.edit_text(text, reply_markup=admin_main_kb())
            else:
                await target.message.answer(text, reply_markup=admin_main_kb())
        except TelegramBadRequest:
            await target.message.answer(text, reply_markup=admin_main_kb())


def find_video_index_by_id(block: str, item_id: str) -> int:
    items = DATA["videos"].get(block, [])
    for idx, item in enumerate(items):
        if str(item.get("id")) == str(item_id):
            return idx
    return -1


async def send_admin_video_preview(call: CallbackQuery, block: str, index: int) -> None:
    items = DATA["videos"].get(block, [])
    if not items:
        await call.message.answer("В этом блоке больше нет видео.", reply_markup=admin_blocks_kb("admin:block"))
        return

    index = max(0, min(index, len(items) - 1))
    item = items[index]
    caption = (
        f"<b>{item['title']}</b>\n"
        f"Блок: {BLOCKS[block]}\n"
        f"Позиция: {index + 1}/{len(items)}"
    )
    await call.message.answer_video(
        video=item["video"],
        caption=caption,
        reply_markup=admin_video_item_kb(block, str(item["id"]), index, len(items)),
        protect_content=False,
    )


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


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    if not has_access(message.from_user.id):
        await message.answer("Доступ к боту ограничен. Обратитесь к администратору: @juliavoice_coach.")
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
    if call.message and not call.message.video:
        await call.message.edit_text("Действие отменено.", reply_markup=admin_main_kb())
    else:
        await call.message.answer("Действие отменено.", reply_markup=admin_main_kb())
    await call.answer("Отменено")


@dp.callback_query(F.data == "admin:add_video")
async def admin_add_video(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    admin_state[call.from_user.id] = {"action": "add_video", "step": "wait_video"}
    if call.message and not call.message.video:
        await call.message.edit_text("Отправьте видео, которое нужно добавить.", reply_markup=cancel_kb())
    else:
        await call.message.answer("Отправьте видео, которое нужно добавить.", reply_markup=cancel_kb())
    await call.answer()


@dp.callback_query(F.data == "admin:users")
async def admin_users(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    if call.message and not call.message.video:
        await call.message.edit_text(users_text(), reply_markup=admin_users_kb())
    else:
        await call.message.answer(users_text(), reply_markup=admin_users_kb())
    await call.answer()


@dp.callback_query(F.data == "admin:user_add")
async def admin_user_add(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    admin_state[call.from_user.id] = {"action": "user_add", "step": "wait_user_id"}
    text = users_text() + "\n\nВведите Telegram ID пользователя, которому нужно открыть доступ."
    if call.message and not call.message.video:
        await call.message.edit_text(text, reply_markup=cancel_kb())
    else:
        await call.message.answer(text, reply_markup=cancel_kb())
    await call.answer()


@dp.callback_query(F.data == "admin:user_remove_list")
async def admin_user_remove_list(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    text = user_remove_list_text()
    if len(get_allowed_users()) <= 1:
        text += "\n\nНет пользователей для удаления."
    if call.message and not call.message.video:
        await call.message.edit_text(text, reply_markup=user_remove_list_kb())
    else:
        await call.message.answer(text, reply_markup=user_remove_list_kb())
    await call.answer()


@dp.callback_query(F.data.startswith("admin:remove_user:"))
async def admin_remove_user(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    user_id_str = call.data.split(":", 2)[2]
    if not user_id_str.isdigit():
        await call.answer("Некорректный ID", show_alert=True)
        return
    remove_id = int(user_id_str)
    if is_admin(remove_id):
        await call.answer("Главного администратора удалять нельзя", show_alert=True)
        return
    if remove_id not in get_allowed_users():
        await call.answer("Пользователь не найден", show_alert=True)
        return

    DATA["allowed_users"] = [uid for uid in DATA["allowed_users"] if int(uid) != remove_id]
    save_data(DATA)
    text = f"Пользователь <code>{remove_id}</code> удалён.\n\n" + user_remove_list_text()
    if call.message and not call.message.video:
        await call.message.edit_text(text, reply_markup=user_remove_list_kb())
    else:
        await call.message.answer(text, reply_markup=user_remove_list_kb())
    await call.answer("Пользователь удалён")


@dp.callback_query(F.data == "admin:list_blocks")
async def admin_list_blocks(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    lines = ["<b>Блоки с видео</b>"]
    for block, title in BLOCKS.items():
        lines.append(f"• {title} — {len(DATA['videos'].get(block, []))}")
    text = "\n".join(lines)
    if call.message and not call.message.video:
        await call.message.edit_text(text, reply_markup=admin_blocks_kb("admin:block"))
    else:
        await call.message.answer(text, reply_markup=admin_blocks_kb("admin:block"))
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
    _, _, block, index_str = call.data.split(":")
    await send_admin_video_preview(call, block, int(index_str))
    await call.answer()


@dp.callback_query(F.data.startswith("admin:delete_video:"))
async def admin_delete_video(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    parts = call.data.split(":")
    if len(parts) == 4:
        _, _, block, item_id = parts
    elif len(parts) == 5:
        _, _, _, block, item_id = parts
    else:
        await call.answer("Ошибка удаления: неверный формат кнопки", show_alert=True)
        return

    index = find_video_index_by_id(block, item_id)
    if index == -1 and item_id.isdigit():
        old_index = int(item_id)
        items = DATA["videos"].get(block, [])
        if 0 <= old_index < len(items):
            index = old_index

    items = DATA["videos"].get(block, [])
    if index < 0 or index >= len(items):
        await call.answer("Видео не найдено", show_alert=True)
        return

    removed = items.pop(index)
    save_data(DATA)

    with contextlib.suppress(Exception):
        if call.message:
            await call.message.delete()

    await bot.send_message(call.from_user.id, f"Удалено: <b>{removed['title']}</b>")
    if items:
        next_index = min(index, len(items) - 1)
        fake_call = call
        await send_admin_video_preview(fake_call, block, next_index)
    else:
        await bot.send_message(
            call.from_user.id,
            "В этом блоке больше нет видео.",
            reply_markup=admin_blocks_kb("admin:block"),
        )
    await call.answer("Удалено")


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

    item = {
        "id": generate_video_id(block, {"title": title}, len(DATA["videos"].get(block, []))),
        "title": title,
        "video": file_id,
    }
    DATA["videos"].setdefault(block, []).append(item)
    save_data(DATA)
    admin_state.pop(call.from_user.id, None)

    text = f"Сохранено в блок <b>{BLOCKS[block]}</b>:\n• {title}"
    if call.message and not call.message.video:
        await call.message.edit_text(text, reply_markup=admin_main_kb())
    else:
        await call.message.answer(text, reply_markup=admin_main_kb())
    await call.answer("Видео сохранено")


@dp.message(F.video)
async def admin_receive_video(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    state = admin_state.get(message.from_user.id)
    if not state or state.get("action") != "add_video" or state.get("step") != "wait_video":
        return
    state["file_id"] = message.video.file_id
    state["step"] = "wait_title"
    await message.answer("Теперь отправьте название видео.", reply_markup=cancel_kb())


@dp.message(F.text)
async def text_router(message: Message) -> None:
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if text in BLOCK_ALIASES:
        if not has_access(user_id):
            await message.answer("Доступ к боту ограничен. Обратитесь к администратору.")
            return
        await send_video(message, BLOCK_ALIASES[text], 0)
        return

    if not is_admin(user_id):
        return

    state = admin_state.get(user_id)
    if not state:
        return

    action = state.get("action")
    step = state.get("step")

    if action == "add_video" and step == "wait_title":
        state["title"] = text
        state["step"] = "wait_block"
        await message.answer("Выберите блок для этого видео:", reply_markup=admin_blocks_kb("admin:save_video"))
        return

    if action == "user_add" and step == "wait_user_id":
        if not text.isdigit():
            await message.answer("Нужно отправить только числовой Telegram ID.", reply_markup=cancel_kb())
            return
        new_user_id = int(text)
        if new_user_id in get_allowed_users():
            admin_state.pop(user_id, None)
            await message.answer("Этот пользователь уже есть в списке доступа.\n\n" + users_text(), reply_markup=admin_users_kb())
            return
        DATA["allowed_users"].append(new_user_id)
        DATA["allowed_users"] = sorted(set(int(x) for x in DATA["allowed_users"]))
        save_data(DATA)
        admin_state.pop(user_id, None)
        await message.answer(
            f"Пользователь <code>{new_user_id}</code> добавлен.\n\n" + users_text(),
            reply_markup=admin_users_kb(),
        )
        return


@dp.callback_query(F.data.startswith("next:"))
async def next_step(call: CallbackQuery) -> None:
    if not has_access(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    _, block, idx_str = call.data.split(":")
    idx = int(idx_str)
    next_idx = idx + 1
    items = DATA["videos"].get(block, [])
    if next_idx < len(items):
        await send_video(call, block, next_idx)
    else:
        finish_text = BLOCK_FINISH_MESSAGES.get(block, "Блок завершён ✅").format(name=user_name(call))
        await bot.send_message(call.from_user.id, finish_text)
        if block != "practice":
            await bot.send_message(call.from_user.id, "Выберите блок:", reply_markup=main_kb())
    await call.answer()


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    import contextlib
    asyncio.run(main())
