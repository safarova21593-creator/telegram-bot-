import asyncio
import contextlib
import json
import logging
import os
import re
import tempfile
import time
from typing import Any, Dict, List, TypedDict
from uuid import uuid4

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    User,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = os.getenv("DATA_FILE", "data.json")

# Необязательные file_id анимаций
START_ANIMATION_FILE_ID = os.getenv("START_ANIMATION_FILE_ID", "").strip()
BLOCK_TRANSITION_ANIMATION_FILE_ID = os.getenv("BLOCK_TRANSITION_ANIMATION_FILE_ID", "").strip()
FINISH_ANIMATION_FILE_ID = os.getenv("FINISH_ANIMATION_FILE_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не найдена")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

DEFAULT_ADMIN_ID = 470343161
MAX_VIDEO_TITLE_LENGTH = 120
MAX_BLOCK_TITLE_LENGTH = 80
CALLBACK_COOLDOWN_SECONDS = 0.8


class VideoItem(TypedDict):
    id: str
    title: str
    video: str


class ProfileItem(TypedDict):
    username: str
    first_name: str
    last_name: str


class AdminVideoFSM(StatesGroup):
    wait_video = State()
    wait_title = State()
    wait_block = State()


class AdminUserFSM(StatesGroup):
    wait_user_id = State()


class AdminBlockFSM(StatesGroup):
    wait_block_title = State()


DEFAULT_BLOCKS = {
    "warmup": "1️⃣ Разогрев",
    "voice": "2️⃣ Рабочие звуки/звонкие качества",
    "belt": "3️⃣ Народный/Бэлтинг",
    "practice": "4️⃣ Вокальные упражнения",
}

BLOCK_FINISH_MESSAGES = {
    "warmup": "{name}, переходи к следующему блоку 2️⃣",
    "voice": "{name}, двигайся к следующему блоку 3️⃣",
    "belt": 'Пришло время реализовать полученные навыки на практике, переходи к блоку "Вокальные упражнения" 🎤',
    "practice": (
        "{name}, поздравляю с завершением тренировки!\n"
        "Для закрепления стойкого результата делайте эти практики регулярно.\n\n"
        "<b>С заботой о Вас, Юлия Золотых ❤️</b>"
    ),
}
DEFAULT_FINISH_MESSAGE = "{name}, блок завершён ✅"

user_callback_ts: Dict[int, float] = {}


def default_data() -> Dict[str, Any]:
    return {
        "admins": [DEFAULT_ADMIN_ID],
        "allowed_users": [DEFAULT_ADMIN_ID],
        "profiles": {},
        "blocks": DEFAULT_BLOCKS.copy(),
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


def get_blocks() -> Dict[str, str]:
    return DATA.get("blocks", {})


def block_aliases() -> Dict[str, str]:
    return {title: key for key, title in get_blocks().items()}


def generate_video_id() -> str:
    return uuid4().hex[:16]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "_", text, flags=re.UNICODE)
    return text.strip("_") or "block"


def generate_block_key(title: str) -> str:
    base = slugify(title)
    blocks = get_blocks()
    key = base
    counter = 2
    while key in blocks:
        key = f"{base}_{counter}"
        counter += 1
    return key


def atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    directory = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=directory) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_name = tmp.name
    os.replace(temp_name, path)


def save_data(data: Dict[str, Any]) -> None:
    atomic_write_json(DATA_FILE, data)


def normalize_id_list(values: Any, fallback: List[int]) -> List[int]:
    if not isinstance(values, list):
        return fallback[:]

    result: List[int] = []
    for x in values:
        if isinstance(x, int):
            result.append(x)
        elif isinstance(x, str) and x.isdigit():
            result.append(int(x))

    result = sorted(set(result))
    return result or fallback[:]


def normalize_profiles(raw_profiles: Any) -> Dict[str, ProfileItem]:
    if not isinstance(raw_profiles, dict):
        return {}

    profiles: Dict[str, ProfileItem] = {}
    for user_id, profile in raw_profiles.items():
        if not str(user_id).isdigit() or not isinstance(profile, dict):
            continue

        profiles[str(user_id)] = {
            "username": str(profile.get("username", "")).strip(),
            "first_name": str(profile.get("first_name", "")).strip(),
            "last_name": str(profile.get("last_name", "")).strip(),
        }

    return profiles


def normalize_blocks(raw_blocks: Any) -> Dict[str, str]:
    blocks: Dict[str, str] = {}

    if isinstance(raw_blocks, dict):
        for key, title in raw_blocks.items():
            clean_key = str(key).strip()
            clean_title = str(title).strip()
            if not clean_key or not clean_title:
                continue
            blocks[clean_key] = clean_title[:MAX_BLOCK_TITLE_LENGTH]

    if not blocks:
        blocks = DEFAULT_BLOCKS.copy()

    return blocks


def normalize_videos(raw_videos: Any, blocks: Dict[str, str]) -> Dict[str, List[VideoItem]]:
    videos: Dict[str, List[VideoItem]] = {}

    if not isinstance(raw_videos, dict):
        raw_videos = {}

    for block in blocks:
        items = raw_videos.get(block, [])
        if not isinstance(items, list):
            items = []

        normalized: List[VideoItem] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "Без названия")).strip()
            video = str(item.get("video", "")).strip()
            item_id = str(item.get("id", "")).strip()

            if not video:
                continue
            if not title:
                title = "Без названия"
            if not item_id:
                item_id = generate_video_id()

            normalized.append({
                "id": item_id,
                "title": title[:MAX_VIDEO_TITLE_LENGTH],
                "video": video,
            })

        videos[block] = normalized

    return videos


def ensure_data_shape(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = default_data()

    old_allowed = normalize_id_list(data.get("allowed_users"), [DEFAULT_ADMIN_ID])
    admins = normalize_id_list(data.get("admins"), [old_allowed[0] if old_allowed else DEFAULT_ADMIN_ID])

    allowed_users = sorted(set(old_allowed + admins))
    profiles = normalize_profiles(data.get("profiles"))
    blocks = normalize_blocks(data.get("blocks"))
    videos = normalize_videos(data.get("videos"), blocks)

    normalized = {
        "admins": admins,
        "allowed_users": allowed_users,
        "profiles": profiles,
        "blocks": blocks,
        "videos": videos,
    }
    return normalized


def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        data = ensure_data_shape(default_data())
        save_data(data)
        return data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.exception("Ошибка чтения %s, загружаю данные по умолчанию", DATA_FILE)
        raw = default_data()

    data = ensure_data_shape(raw)
    save_data(data)
    return data


DATA = load_data()


def get_admins() -> set[int]:
    return {int(x) for x in DATA.get("admins", [])}


def get_allowed_users() -> set[int]:
    return {int(x) for x in DATA.get("allowed_users", [])}


def is_admin(user_id: int) -> bool:
    return user_id in get_admins()


def has_access(user_id: int) -> bool:
    return user_id in get_allowed_users()


def user_name(message_or_call: Message | CallbackQuery) -> str:
    first_name = message_or_call.from_user.first_name or "Пользователь"
    return first_name.strip()


def update_user_profile(user: User) -> None:
    profiles = DATA.setdefault("profiles", {})
    profiles[str(user.id)] = {
        "username": (user.username or "").strip(),
        "first_name": (user.first_name or "").strip(),
        "last_name": (user.last_name or "").strip(),
    }
    save_data(DATA)


def format_user_line(uid: int) -> str:
    profile = DATA.get("profiles", {}).get(str(uid), {})
    username = str(profile.get("username", "")).strip()
    first_name = str(profile.get("first_name", "")).strip()
    last_name = str(profile.get("last_name", "")).strip()

    role = " — админ" if is_admin(uid) else ""

    parts = [f"• <code>{uid}</code>"]
    if username:
        parts.append(f"@{username}")

    full_name = " ".join(x for x in [first_name, last_name] if x).strip()
    if full_name:
        parts.append(full_name)

    return " — ".join(parts) + role


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)] for text in get_blocks().values()],
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
            [InlineKeyboardButton(text="🧩 Добавить блок", callback_data="admin:add_block")],
            [InlineKeyboardButton(text="🗑 Удалить блок", callback_data="admin:remove_block_list")],
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
    rows = [[InlineKeyboardButton(text=title, callback_data=f"{prefix}:{block}")] for block, title in get_blocks().items()]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_removable_blocks_kb() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for block, title in get_blocks().items():
        rows.append([InlineKeyboardButton(text=title[:64], callback_data=f"admin:remove_block:{block}")])
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
        lines.append(format_user_line(uid))
    return "\n".join(lines)


def user_remove_list_text() -> str:
    users = sorted(get_allowed_users())
    lines = ["<b>Выберите пользователя для удаления</b>"]
    for uid in users:
        lines.append(format_user_line(uid))
    return "\n".join(lines)


def user_remove_list_kb() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for uid in sorted(get_allowed_users()):
        if is_admin(uid):
            continue
        label = str(uid)
        profile = DATA.get("profiles", {}).get(str(uid), {})
        username = str(profile.get("username", "")).strip()
        if username:
            label = f"{uid} | @{username}"
        rows.append([InlineKeyboardButton(text=label[:64], callback_data=f"admin:remove_user:{uid}")])

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
                text="✅ Завершить блок" if last else "▶️ Следующее упражнение",
                callback_data=f"next:{block}:{index}",
            )
        ]]
    )


def find_video_index_by_id(block: str, item_id: str) -> int:
    items = DATA["videos"].get(block, [])
    for idx, item in enumerate(items):
        if str(item.get("id")) == str(item_id):
            return idx
    return -1


def update_callback_ts(user_id: int) -> bool:
    now = time.monotonic()
    last = user_callback_ts.get(user_id, 0.0)
    if now - last < CALLBACK_COOLDOWN_SECONDS:
        return False
    user_callback_ts[user_id] = now
    return True


def is_last_block(block: str) -> bool:
    keys = list(get_blocks().keys())
    return bool(keys) and keys[-1] == block


async def safe_edit_or_send(call: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    if not call.message:
        return

    try:
        if not call.message.video and not call.message.animation:
            await call.message.edit_text(text, reply_markup=reply_markup)
        else:
            await call.message.answer(text, reply_markup=reply_markup)
            with contextlib.suppress(Exception):
                await call.message.delete()
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=reply_markup)
    except Exception:
        logger.exception("Ошибка safe_edit_or_send")
        await call.message.answer(text, reply_markup=reply_markup)


async def show_admin_panel(target: Message | CallbackQuery) -> None:
    text = (
        "<b>Админ-панель</b>\n\n"
        "Здесь можно:\n"
        "• добавлять видео\n"
        "• добавлять блоки\n"
        "• удалять блоки\n"
        "• добавлять пользователей\n"
        "• удалять пользователей по кнопке\n"
        "• просматривать и удалять видео из блоков"
    )

    if isinstance(target, Message):
        await target.answer(text, reply_markup=admin_main_kb())
    else:
        await safe_edit_or_send(target, text, admin_main_kb())


async def maybe_send_animation(chat_id: int, file_id: str, caption: str | None = None) -> bool:
    if not file_id:
        return False
    try:
        await bot.send_animation(chat_id=chat_id, animation=file_id, caption=caption)
        return True
    except Exception:
        logger.exception("Не удалось отправить animation")
        return False


async def send_transition_text(chat_id: int, text: str, delay: float = 0.7) -> None:
    msg = await bot.send_message(chat_id, text)
    await asyncio.sleep(delay)
    with contextlib.suppress(Exception):
        await msg.delete()


async def send_admin_video_preview(call: CallbackQuery, block: str, index: int) -> None:
    if not call.message:
        return

    items = DATA["videos"].get(block, [])
    if not items:
        await call.message.answer("В этом блоке больше нет видео.", reply_markup=admin_blocks_kb("admin:block"))
        return

    index = max(0, min(index, len(items) - 1))
    item = items[index]
    caption = (
        f"<b>{item['title']}</b>\n"
        f"Блок: {get_blocks().get(block, block)}\n"
        f"Позиция: {index + 1}/{len(items)}"
    )

    await call.message.answer_video(
        video=item["video"],
        caption=caption,
        reply_markup=admin_video_item_kb(block, str(item["id"]), index, len(items)),
        protect_content=False,
    )

    with contextlib.suppress(Exception):
        if not call.message.video and not call.message.animation:
            await call.message.delete()


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
    caption = (
        f"<b>{item['title']}</b>\n"
        f"Блок: {get_blocks().get(block, block)}\n\n"
        f"{progress_text(block, index)}"
    )

    await bot.send_video(
        chat_id=user_id,
        video=item["video"],
        caption=caption,
        reply_markup=inline_next(block, index),
        protect_content=True,
    )


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    update_user_profile(message.from_user)

    if not has_access(message.from_user.id):
        await message.answer("Доступ к боту ограничен. Обратитесь к администратору: @juliavoice_coach.")
        return

    await message.answer(f"Приветствую, {message.from_user.first_name}! ✨")
    await send_transition_text(message.from_user.id, "Подготавливаю тренировку…")
    await maybe_send_animation(message.from_user.id, START_ANIMATION_FILE_ID, "Готово к тренировке 🎤")
    await message.answer("Выбери блок:", reply_markup=main_kb())


@dp.message(Command("admin"))
async def admin_handler(message: Message, state: FSMContext) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return

    await state.clear()
    await show_admin_panel(message)


@dp.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery, state: FSMContext) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await show_admin_panel(call)
    await call.answer()


@dp.callback_query(F.data == "admin:cancel")
async def admin_cancel(call: CallbackQuery, state: FSMContext) -> None:
    update_user_profile(call.from_user)
    await state.clear()
    await safe_edit_or_send(call, "Действие отменено.", admin_main_kb())
    await call.answer("Отменено")


@dp.callback_query(F.data == "admin:add_block")
async def admin_add_block(call: CallbackQuery, state: FSMContext) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminBlockFSM.wait_block_title)
    await safe_edit_or_send(
        call,
        "Отправьте название нового блока.\n\nНапример: <b>5️⃣ Дыхание</b>",
        cancel_kb(),
    )
    await call.answer()


@dp.message(AdminBlockFSM.wait_block_title, F.text)
async def admin_receive_block_title(message: Message, state: FSMContext) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        return

    title = (message.text or "").strip()

    if not title:
        await message.answer("Название блока не может быть пустым.", reply_markup=cancel_kb())
        return

    if len(title) > MAX_BLOCK_TITLE_LENGTH:
        await message.answer(
            f"Название блока слишком длинное. Максимум {MAX_BLOCK_TITLE_LENGTH} символов.",
            reply_markup=cancel_kb(),
        )
        return

    if title in get_blocks().values():
        await message.answer("Такой блок уже существует.", reply_markup=cancel_kb())
        return

    block_key = generate_block_key(title)
    DATA["blocks"][block_key] = title
    DATA["videos"].setdefault(block_key, [])
    save_data(DATA)

    logger.info("Admin %s added block %s (%s)", message.from_user.id, title, block_key)

    await state.clear()
    await message.answer(
        f"Блок добавлен:\n• <b>{title}</b>\n• key: <code>{block_key}</code>",
        reply_markup=admin_main_kb(),
    )


@dp.message(AdminBlockFSM.wait_block_title)
async def admin_receive_block_title_invalid(message: Message) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        return

    await message.answer("Нужно отправить текстовое название блока.", reply_markup=cancel_kb())


@dp.callback_query(F.data == "admin:remove_block_list")
async def admin_remove_block_list(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    lines = ["<b>Выберите блок для удаления</b>"]
    for block, title in get_blocks().items():
        suffix = " — базовый" if block in DEFAULT_BLOCKS else ""
        count = len(DATA["videos"].get(block, []))
        lines.append(f"• {title} — {count} видео{suffix}")

    text = "\n".join(lines)
    await safe_edit_or_send(call, text, admin_removable_blocks_kb())
    await call.answer()


@dp.callback_query(F.data.startswith("admin:remove_block:"))
async def admin_remove_block(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    block = call.data.split(":", 2)[2]
    if block not in get_blocks():
        await call.answer("Блок не найден", show_alert=True)
        return

    if len(get_blocks()) <= 1:
        await call.answer("Нельзя удалить последний блок", show_alert=True)
        return

    title = get_blocks()[block]
    video_count = len(DATA["videos"].get(block, []))

    DATA["blocks"].pop(block, None)
    DATA["videos"].pop(block, None)
    save_data(DATA)

    logger.info(
        "Admin %s removed block %s (%s) with %s videos",
        call.from_user.id,
        title,
        block,
        video_count,
    )

    text = (
        f"Удалён блок <b>{title}</b>.\n"
        f"Вместе с ним удалено видео: <b>{video_count}</b>.\n\n"
        f"Оставшиеся блоки:"
    )
    lines = [text]
    for key, value in get_blocks().items():
        lines.append(f"• {value} — {len(DATA['videos'].get(key, []))}")
    await safe_edit_or_send(call, "\n".join(lines), admin_main_kb())
    await call.answer("Блок удалён")


@dp.callback_query(F.data == "admin:add_video")
async def admin_add_video(call: CallbackQuery, state: FSMContext) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminVideoFSM.wait_video)
    await safe_edit_or_send(call, "Отправьте видео, которое нужно добавить.", cancel_kb())
    await call.answer()


@dp.callback_query(F.data == "admin:users")
async def admin_users(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await safe_edit_or_send(call, users_text(), admin_users_kb())
    await call.answer()


@dp.callback_query(F.data == "admin:user_add")
async def admin_user_add(call: CallbackQuery, state: FSMContext) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminUserFSM.wait_user_id)
    text = users_text() + "\n\nВведите Telegram ID пользователя, которому нужно открыть доступ."
    await safe_edit_or_send(call, text, cancel_kb())
    await call.answer()


@dp.callback_query(F.data == "admin:user_remove_list")
async def admin_user_remove_list(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    text = user_remove_list_text()
    removable_users = [uid for uid in get_allowed_users() if not is_admin(uid)]
    if not removable_users:
        text += "\n\nНет пользователей для удаления."

    await safe_edit_or_send(call, text, user_remove_list_kb())
    await call.answer()


@dp.callback_query(F.data.startswith("admin:remove_user:"))
async def admin_remove_user(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    user_id_str = call.data.split(":", 2)[2]
    if not user_id_str.isdigit():
        await call.answer("Некорректный ID", show_alert=True)
        return

    remove_id = int(user_id_str)
    if is_admin(remove_id):
        await call.answer("Администратора удалять нельзя", show_alert=True)
        return

    if remove_id not in get_allowed_users():
        await call.answer("Пользователь не найден", show_alert=True)
        return

    DATA["allowed_users"] = [uid for uid in DATA["allowed_users"] if int(uid) != remove_id]
    save_data(DATA)

    logger.info("Admin %s removed user %s", call.from_user.id, remove_id)

    text = f"Пользователь <code>{remove_id}</code> удалён.\n\n" + user_remove_list_text()
    await safe_edit_or_send(call, text, user_remove_list_kb())
    await call.answer("Пользователь удалён")


@dp.callback_query(F.data == "admin:list_blocks")
async def admin_list_blocks(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    lines = ["<b>Блоки с видео</b>"]
    for block, title in get_blocks().items():
        lines.append(f"• {title} — {len(DATA['videos'].get(block, []))}")

    text = "\n".join(lines)
    await safe_edit_or_send(call, text, admin_blocks_kb("admin:block"))
    await call.answer()


@dp.callback_query(F.data.startswith("admin:block:"))
async def admin_open_block(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

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
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    parts = call.data.split(":")
    if len(parts) != 4:
        await call.answer("Ошибка навигации", show_alert=True)
        return

    _, _, block, index_str = parts
    if not index_str.isdigit():
        await call.answer("Ошибка индекса", show_alert=True)
        return

    await send_admin_video_preview(call, block, int(index_str))
    await call.answer()


@dp.callback_query(F.data.startswith("admin:delete_video:"))
async def admin_delete_video(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    parts = call.data.split(":")
    if len(parts) != 4:
        await call.answer("Ошибка удаления: неверный формат кнопки", show_alert=True)
        return

    _, _, block, item_id = parts

    index = find_video_index_by_id(block, item_id)
    items = DATA["videos"].get(block, [])

    if index < 0 or index >= len(items):
        await call.answer("Видео не найдено", show_alert=True)
        return

    removed = items.pop(index)
    save_data(DATA)

    logger.info(
        "Admin %s deleted video '%s' (%s) from block %s",
        call.from_user.id,
        removed["title"],
        removed["id"],
        block,
    )

    with contextlib.suppress(Exception):
        if call.message:
            await call.message.delete()

    await bot.send_message(call.from_user.id, f"Удалено: <b>{removed['title']}</b>")

    if items:
        next_index = min(index, len(items) - 1)
        await send_admin_video_preview(call, block, next_index)
    else:
        await bot.send_message(
            call.from_user.id,
            "В этом блоке больше нет видео.",
            reply_markup=admin_blocks_kb("admin:block"),
        )

    await call.answer("Удалено")


@dp.callback_query(AdminVideoFSM.wait_block, F.data.startswith("admin:save_video:"))
async def admin_save_video(call: CallbackQuery, state: FSMContext) -> None:
    update_user_profile(call.from_user)

    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    block = call.data.split(":", 2)[2]
    if block not in get_blocks():
        await call.answer("Неизвестный блок", show_alert=True)
        return

    state_data = await state.get_data()
    file_id = state_data.get("file_id")
    title = state_data.get("title")

    if not file_id or not title:
        await call.answer("Не хватает данных для сохранения", show_alert=True)
        return

    item: VideoItem = {
        "id": generate_video_id(),
        "title": title,
        "video": file_id,
    }

    DATA["videos"].setdefault(block, []).append(item)
    save_data(DATA)

    logger.info(
        "Admin %s added video '%s' (%s) to block %s",
        call.from_user.id,
        title,
        item["id"],
        block,
    )

    await state.clear()
    text = f"Сохранено в блок <b>{get_blocks()[block]}</b>:\n• {title}"
    await safe_edit_or_send(call, text, admin_main_kb())
    await call.answer("Видео сохранено")


@dp.message(AdminVideoFSM.wait_video, F.video)
async def admin_receive_video(message: Message, state: FSMContext) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        return

    await state.update_data(file_id=message.video.file_id)
    await state.set_state(AdminVideoFSM.wait_title)
    await message.answer("Теперь отправьте название видео.", reply_markup=cancel_kb())


@dp.message(AdminVideoFSM.wait_video)
async def admin_receive_video_invalid(message: Message) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужно отправить именно видео.", reply_markup=cancel_kb())


@dp.message(AdminVideoFSM.wait_title, F.text)
async def admin_receive_title(message: Message, state: FSMContext) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()

    if not text:
        await message.answer("Название не может быть пустым.", reply_markup=cancel_kb())
        return

    if len(text) > MAX_VIDEO_TITLE_LENGTH:
        await message.answer(
            f"Название слишком длинное. Максимум {MAX_VIDEO_TITLE_LENGTH} символов.",
            reply_markup=cancel_kb(),
        )
        return

    await state.update_data(title=text)
    await state.set_state(AdminVideoFSM.wait_block)
    await message.answer("Выберите блок для этого видео:", reply_markup=admin_blocks_kb("admin:save_video"))


@dp.message(AdminVideoFSM.wait_title)
async def admin_receive_title_invalid(message: Message) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужно отправить текстовое название видео.", reply_markup=cancel_kb())


@dp.message(AdminUserFSM.wait_user_id, F.text)
async def admin_receive_user_id(message: Message, state: FSMContext) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Нужно отправить только числовой Telegram ID.", reply_markup=cancel_kb())
        return

    new_user_id = int(text)
    if new_user_id in get_allowed_users():
        await state.clear()
        await message.answer(
            "Этот пользователь уже есть в списке доступа.\n\n" + users_text(),
            reply_markup=admin_users_kb(),
        )
        return

    DATA["allowed_users"].append(new_user_id)
    DATA["allowed_users"] = sorted(set(int(x) for x in DATA["allowed_users"]))
    save_data(DATA)

    logger.info("Admin %s added user %s", message.from_user.id, new_user_id)

    await state.clear()
    await message.answer(
        f"Пользователь <code>{new_user_id}</code> добавлен.\n\n" + users_text(),
        reply_markup=admin_users_kb(),
    )


@dp.message(AdminUserFSM.wait_user_id)
async def admin_receive_user_id_invalid(message: Message) -> None:
    update_user_profile(message.from_user)

    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужно отправить только числовой Telegram ID.", reply_markup=cancel_kb())


@dp.message(F.text)
async def text_router(message: Message, state: FSMContext) -> None:
    update_user_profile(message.from_user)

    user_id = message.from_user.id
    text = (message.text or "").strip()
    aliases = block_aliases()

    if text in aliases:
        if not has_access(user_id):
            await message.answer("Доступ к боту ограничен. Обратитесь к администратору.")
            return

        await state.clear()
        await send_transition_text(user_id, f"Открываю блок {text} ✨")
        await send_video(message, aliases[text], 0)
        return


@dp.callback_query(F.data.startswith("next:"))
async def next_step(call: CallbackQuery) -> None:
    update_user_profile(call.from_user)

    if not has_access(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    if not update_callback_ts(call.from_user.id):
        await call.answer("Слишком быстро. Попробуйте ещё раз.", show_alert=False)
        return

    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer("Ошибка перехода", show_alert=True)
        return

    _, block, idx_str = parts
    if block not in get_blocks() or not idx_str.isdigit():
        await call.answer("Ошибка перехода", show_alert=True)
        return

    idx = int(idx_str)
    next_idx = idx + 1
    items = DATA["videos"].get(block, [])

    with contextlib.suppress(Exception):
        if call.message:
            await call.message.edit_reply_markup(reply_markup=None)

    if next_idx < len(items):
        await send_transition_text(call.from_user.id, "Следующее упражнение…")
        await send_video(call, block, next_idx)
    else:
        await maybe_send_animation(call.from_user.id, BLOCK_TRANSITION_ANIMATION_FILE_ID, "Блок завершён ✨")
        finish_text = BLOCK_FINISH_MESSAGES.get(block, DEFAULT_FINISH_MESSAGE).format(name=user_name(call))
        await bot.send_message(call.from_user.id, finish_text)

        if is_last_block(block):
            await maybe_send_animation(call.from_user.id, FINISH_ANIMATION_FILE_ID, "Тренировка завершена 🎉")
        else:
            await bot.send_message(call.from_user.id, "Выберите блок:", reply_markup=main_kb())

    await call.answer()


async def main() -> None:
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())