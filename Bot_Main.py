# Bot_Main.py

import os
import logging
from typing import Dict, List
from dotenv import load_dotenv

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from telegram.constants import ParseMode

from XML_Data_Base import init_database, get_db

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен бота
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Не установлен TELEGRAM_BOT_TOKEN в переменных окружения")

# Список разрешенных пользователей
ALLOWED_USERS = {
    # : "admin_user",
    #: "family_member",
}

# Состояния для ConversationHandler
(
    MAIN_MENU,
    PRESERVES_MENU, PRODUCTS_MENU, ADD_MENU, SEARCH_MENU, STATS_MENU, HELP_MENU,
    ADD_PRESERVE_STEP1, ADD_PRESERVE_STEP2, ADD_PRESERVE_STEP3,
    ADD_PRESERVE_STEP4, ADD_PRESERVE_STEP5,
    ADD_PRODUCT_STEP1, ADD_PRODUCT_STEP2, ADD_PRODUCT_STEP3,
    SEARCH_PRESERVES_STEP1, SEARCH_PRESERVES_STEP2,
    MANAGE_LOCATIONS,
    REMOVE_PRESERVE_MENU, REMOVE_PRESERVE_STEP1, REMOVE_PRESERVE_STEP2, REMOVE_PRESERVE_STEP3,
    REMOVE_PRODUCT_MENU, REMOVE_PRODUCT_STEP1, REMOVE_PRODUCT_STEP2, REMOVE_PRODUCT_STEP3
) = range(26)

# Инициализируем базу данных
db = init_database()


def check_access(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя доступ к боту."""
    return user_id in ALLOWED_USERS


def format_preserves_grouped(grouped_preserves: Dict[tuple, Dict]) -> str:
    """
    Форматирует сгруппированные закатки для отображения.
    """
    if not grouped_preserves:
        return "📭 Хранилище закаток пусто!"

    message_lines = []

    for key, group in sorted(grouped_preserves.items(), key=lambda x: x[1]['content']):
        # Формируем строку с информацией о закатке
        header = f"🥫 <b>{group['content']}</b> ({group['volume']}л, {group['note_description']})"
        total_info = f"📊 Всего: {group['total_quantity']} шт"

        # Формируем строку мест хранения
        locations_info = "📍 Места: "
        locations_list = []
        for loc in sorted(group['locations'], key=lambda x: x['location']):
            locations_list.append(f"{loc['location']} ({loc['quantity']} шт)")

        locations_info += ", ".join(locations_list)

        # Собираем все вместе
        message_lines.append(header)
        message_lines.append(total_info)
        message_lines.append(locations_info)
        message_lines.append("")  # Пустая строка для разделения

    return "\n".join(message_lines)


def format_products_grouped(grouped_products: Dict[str, Dict]) -> str:
    """
    Форматирует сгруппированные продукты для отображения.
    """
    if not grouped_products:
        return "🍚 Раздел продуктов пуст!"

    message_lines = []

    for name, group in sorted(grouped_products.items(), key=lambda x: x[0]):
        # Формируем строку с информацией о продукте
        header = f"🍚 <b>{group['name']}</b>"
        total_info = f"📊 Всего: {group['total_quantity']} шт"

        # Формируем строку мест хранения
        locations_info = "📍 Места: "
        locations_list = []
        for loc in sorted(group['locations'], key=lambda x: x['location']):
            locations_list.append(f"{loc['location']} ({loc['quantity']} шт)")

        locations_info += ", ".join(locations_list)

        # Собираем все вместе
        message_lines.append(header)
        message_lines.append(total_info)
        message_lines.append(locations_info)
        message_lines.append("")  # Пустая строка для разделения

    return "\n".join(message_lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user_id = update.effective_user.id

    if not check_access(user_id):
        await update.message.reply_text(
            "⛔ У вас нет доступа к этому боту.\n"
            "Обратитесь к администратору для получения доступа."
        )
        return ConversationHandler.END

    username = update.effective_user.username or update.effective_user.first_name

    # Главное меню
    keyboard = [
        [KeyboardButton("🥫 Закатки"), KeyboardButton("🍚 Продукты")],
        [KeyboardButton("➕ Добавить"), KeyboardButton("🔍 Поиск")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("ℹ️ Помощь")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_text = (
        f"👋 Привет, {username}!\n\n"
        "🤖 Я бот для управления домашним хранилищем.\n\n"
        "📱 <b>Используйте кнопки ниже для навигации:</b>"
    )

    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return MAIN_MENU


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню."""
    if not check_access(update.effective_user.id):
        return ConversationHandler.END

    text = update.message.text

    if text == "🥫 Закатки":
        return await preserves_menu(update, context)
    elif text == "🍚 Продукты":
        return await products_menu(update, context)
    elif text == "➕ Добавить":
        return await add_menu(update, context)
    elif text == "🔍 Поиск":
        return await search_menu(update, context)
    elif text == "📊 Статистика":
        return await stats_menu(update, context)
    elif text == "ℹ️ Помощь":
        return await help_menu(update, context)
    else:
        await update.message.reply_text("❓ Неизвестная команда. Используйте кнопки меню.")
        return MAIN_MENU


async def preserves_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню для работы с закатками."""
    keyboard = [
        [KeyboardButton("👁️ Просмотреть все"), KeyboardButton("➖ Удалить закатку")],
        [KeyboardButton("🔍 Найти закатки"), KeyboardButton("➕ Добавить закатку")],
        [KeyboardButton("🏠 Главное меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🥫 <b>Меню закаток</b>\n\n"
        "Выберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return PRESERVES_MENU


async def preserves_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню закаток."""
    text = update.message.text

    if text == "👁️ Просмотреть все":
        return await view_preserves(update, context)
    elif text == "➖ Удалить закатку":
        return await remove_preserve_menu(update, context)
    elif text == "🔍 Найти закатки":
        return await search_preserves_menu(update, context)
    elif text == "➕ Добавить закатку":
        return await add_preserve_menu(update, context)
    elif text == "🏠 Главное меню":
        return await start(update, context)
    else:
        await update.message.reply_text("❓ Неизвестная команда. Используйте кнопки меню.")
        return PRESERVES_MENU


async def products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню для работы с продуктами."""
    keyboard = [
        [KeyboardButton("👁️ Просмотреть все"), KeyboardButton("➖ Удалить продукт")],
        [KeyboardButton("➕ Добавить продукт"), KeyboardButton("🏠 Главное меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🍚 <b>Меню продуктов</b>\n\n"
        "Выберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return PRODUCTS_MENU


async def products_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню продуктов."""
    text = update.message.text

    if text == "👁️ Просмотреть все":
        return await view_products(update, context)
    elif text == "➖ Удалить продукт":
        return await remove_product_menu(update, context)
    elif text == "➕ Добавить продукт":
        return await add_product_menu(update, context)
    elif text == "🏠 Главное меню":
        return await start(update, context)
    else:
        await update.message.reply_text("❓ Неизвестная команда. Используйте кнопки меню.")
        return PRODUCTS_MENU


async def add_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню добавления."""
    keyboard = [
        [KeyboardButton("🥫 Добавить закатку"), KeyboardButton("🍚 Добавить продукт")],
        [KeyboardButton("📍 Управление местами"), KeyboardButton("🏠 Главное меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "➕ <b>Меню добавления</b>\n\n"
        "Выберите что добавить:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_MENU


async def add_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню добавления."""
    text = update.message.text

    if text == "🥫 Добавить закатку":
        return await add_preserve_menu(update, context)
    elif text == "🍚 Добавить продукт":
        return await add_product_menu(update, context)
    elif text == "📍 Управление местами":
        return await manage_locations(update, context)
    elif text == "🏠 Главное меню":
        return await start(update, context)
    else:
        await update.message.reply_text("❓ Неизвестная команда. Используйте кнопки меню.")
        return ADD_MENU


async def search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню поиска."""
    keyboard = [
        [KeyboardButton("🔍 Найти закатки"), KeyboardButton("🏠 Главное меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🔍 <b>Меню поиска</b>\n\n"
        "Выберите что искать:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return SEARCH_MENU


async def search_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню поиска."""
    text = update.message.text

    if text == "🔍 Найти закатки":
        return await search_preserves_menu(update, context)
    elif text == "🏠 Главное меню":
        return await start(update, context)
    else:
        await update.message.reply_text("❓ Неизвестная команда. Используйте кнопки меню.")
        return SEARCH_MENU


async def stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню статистики."""
    keyboard = [
        [KeyboardButton("📊 Показать статистику"), KeyboardButton("🏠 Главное меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "📊 <b>Меню статистики</b>\n\n"
        "Выберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return STATS_MENU


async def stats_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню статистики."""
    text = update.message.text

    if text == "📊 Показать статистику":
        return await show_stats(update, context)
    elif text == "🏠 Главное меню":
        return await start(update, context)
    else:
        await update.message.reply_text("❓ Неизвестная команда. Используйте кнопки меню.")
        return STATS_MENU


async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню помощи."""
    help_text = (
        "📚 <b>Справка по боту:</b>\n\n"

        "🥫 <b>Закатки:</b>\n"
        "- Автоматически группируются по названию, объему и типу\n"
        "- При добавлении в существующее место - количество суммируется\n"
        "- Можно удалять закатки по количеству\n\n"

        "🍚 <b>Продукты:</b>\n"
        "- Группируются по названию\n"
        "- При добавлении в существующее место - количество суммируется\n"
        "- Можно удалять продукты по количеству\n\n"

        "📍 <b>Места хранения:</b>\n"
        "- Добавляются автоматически при добавлении предметов\n"
        "- Используйте кнопки для выбора мест\n\n"

        "📱 <b>Управление:</b>\n"
        "- Используйте кнопки для навигации\n"
        "- Все изменения сохраняются автоматически"
    )

    keyboard = [[KeyboardButton("🏠 Главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return HELP_MENU


async def help_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню помощи."""
    text = update.message.text

    if text == "🏠 Главное меню":
        return await start(update, context)
    else:
        await update.message.reply_text("❓ Неизвестная команда. Используйте кнопки меню.")
        return HELP_MENU


async def view_preserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все закатки в хранилище."""
    grouped_preserves = db.get_preserves_grouped()

    if not grouped_preserves:
        message = "📭 Хранилище закаток пусто!"
    else:
        message = "🥫 <b>Закатки в хранилище:</b>\n\n"
        message += format_preserves_grouped(grouped_preserves)

    keyboard = [[KeyboardButton("🔙 Назад к закаткам"), KeyboardButton("🏠 Главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return PRESERVES_MENU


async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все продукты в хранилище."""
    grouped_products = db.get_products_grouped()

    if not grouped_products:
        message = "🍚 Раздел продуктов пуст!"
    else:
        message = "🍚 <b>Продукты в хранилище:</b>\n\n"
        message += format_products_grouped(grouped_products)

    keyboard = [[KeyboardButton("🔙 Назад к продуктам"), KeyboardButton("🏠 Главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return PRODUCTS_MENU


async def add_preserve_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс добавления закатки."""
    context.user_data.clear()

    # Получаем историю названий закаток
    preserve_history = db.get_preserve_history()

    # Показываем только историю, без стандартных значений
    keyboard = []
    for content in preserve_history:
        keyboard.append([KeyboardButton(content)])

    if preserve_history:
        keyboard.append([KeyboardButton("✏️ Ввести новое")])
    else:
        # Если истории нет, просто предлагаем ввести
        await update.message.reply_text(
            "🥫 <b>Добавление закатки - Шаг 1/5</b>\n\n"
            "ℹ️ <b>Примечание:</b> Если закатка с таким же названием, объемом и местом уже есть, количество будет увеличено.\n\n"
            "Введите содержимое закатки:",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRESERVE_STEP1

    keyboard.append([KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🥫 <b>Добавление закатки - Шаг 1/5</b>\n\n"
        "ℹ️ <b>Примечание:</b> Если закатка с таким же названием, объемом и местом уже есть, количество будет увеличено.\n\n"
        "Выберите содержимое закатки из истории или введите новое:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRESERVE_STEP1


async def add_preserve_step1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор содержимого закатки."""
    text = update.message.text

    if text == "🔙 Назад":
        return await add_menu(update, context)
    elif text == "✏️ Ввести новое":
        await update.message.reply_text(
            "✏️ Введите содержимое закатки:",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRESERVE_STEP1

    context.user_data['preserve_content'] = text

    # Получаем доступные объемы из таблицы
    volumes = db.get_available_volumes()

    if not volumes:
        await update.message.reply_text(
            "❌ Нет доступных объемов в справочнике.\n"
            "Добавьте объемы в таблицу Excel в столбце H.",
            parse_mode=ParseMode.HTML
        )
        return await start(update, context)

    keyboard = []
    for vol in volumes:
        keyboard.append([KeyboardButton(f"{vol} л")])

    keyboard.append([KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Содержимое: <b>{text}</b>\n\n"
        "🥫 <b>Добавление закатки - Шаг 2/5</b>\n\n"
        "Выберите объем закатки:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRESERVE_STEP2


async def add_preserve_step1_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод своего содержимого закатки."""
    text = update.message.text

    if text in ["🔙 Назад", "✏️ Ввести новое"]:
        return await add_preserve_menu(update, context)

    content = text.strip()

    if not content:
        await update.message.reply_text("❌ Содержимое не может быть пустым. Введите еще раз:")
        return ADD_PRESERVE_STEP1

    context.user_data['preserve_content'] = content

    volumes = db.get_available_volumes()

    if not volumes:
        await update.message.reply_text(
            "❌ Нет доступных объемов в справочнике.\n"
            "Добавьте объемы в таблицу Excel в столбце H.",
            parse_mode=ParseMode.HTML
        )
        return await start(update, context)

    keyboard = []
    for vol in volumes:
        keyboard.append([KeyboardButton(f"{vol} л")])

    keyboard.append([KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Содержимое: <b>{content}</b>\n\n"
        "🥫 <b>Добавление закатки - Шаг 2/5</b>\n\n"
        "Выберите объем закатки:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRESERVE_STEP2


async def add_preserve_step2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор объема закатки."""
    text = update.message.text

    if text == "🔙 Назад":
        return await add_preserve_menu(update, context)

    try:
        volume = float(text.replace(" л", ""))
        context.user_data['preserve_volume'] = volume

        # Получаем доступные примечания из таблицы
        notes = db.get_available_notes()

        if not notes:
            await update.message.reply_text(
                "❌ Нет доступных типов в справочнике.\n"
                "Добавьте типы в таблицу Excel в столбцах J-K.",
                parse_mode=ParseMode.HTML
            )
            return await start(update, context)

        keyboard = []
        for code, desc in notes.items():
            keyboard.append([KeyboardButton(f"{desc}")])

        keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Содержимое: <b>{context.user_data['preserve_content']}</b>\n"
            f"✅ Объем: <b>{volume} л</b>\n\n"
            "🥫 <b>Добавление закатки - Шаг 3/5</b>\n\n"
            "Выберите тип продукта:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRESERVE_STEP3

    except ValueError:
        await update.message.reply_text("❌ Ошибка при выборе объема. Попробуйте еще раз:")
        return ADD_PRESERVE_STEP2


async def add_preserve_step3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор примечания закатки."""
    text = update.message.text

    if text == "🔙 Назад":
        volumes = db.get_available_volumes()
        keyboard = []
        for vol in volumes:
            keyboard.append([KeyboardButton(f"{vol} л")])

        keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Содержимое: <b>{context.user_data['preserve_content']}</b>\n\n"
            "Выберите объем закатки:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRESERVE_STEP2

    notes = db.get_available_notes()
    note_code = None
    for code, desc in notes.items():
        if desc == text:
            note_code = code
            break

    if not note_code:
        await update.message.reply_text("❌ Ошибка при выборе типа. Попробуйте еще раз:")
        return ADD_PRESERVE_STEP3

    context.user_data['preserve_note'] = note_code
    context.user_data['preserve_note_desc'] = text

    quantities = ["1", "2", "3", "5", "10", "15", "20"]
    keyboard = []
    for i in range(0, len(quantities), 3):
        row = quantities[i:i + 3]
        keyboard.append([KeyboardButton(qty) for qty in row])

    keyboard.append([KeyboardButton("✏️ Ввести другое"), KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Содержимое: <b>{context.user_data['preserve_content']}</b>\n"
        f"✅ Объем: <b>{context.user_data['preserve_volume']} л</b>\n"
        f"✅ Тип: <b>{text}</b>\n\n"
        "🥫 <b>Добавление закатки - Шаг 4/5</b>\n\n"
        "Выберите количество закаток:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRESERVE_STEP4


async def add_preserve_step4_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор количества закаток."""
    text = update.message.text

    if text == "🔙 Назад":
        notes = db.get_available_notes()
        keyboard = []
        for code, desc in notes.items():
            keyboard.append([KeyboardButton(f"{desc}")])

        keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Содержимое: <b>{context.user_data['preserve_content']}</b>\n"
            f"✅ Объем: <b>{context.user_data['preserve_volume']} л</b>\n\n"
            "Выберите тип продукта:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRESERVE_STEP3

    elif text == "✏️ Ввести другое":
        await update.message.reply_text(
            "✏️ Введите количество закаток (целое число):",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRESERVE_STEP4

    try:
        quantity = int(text)

        if quantity <= 0:
            await update.message.reply_text("❌ Количество должно быть положительным числом. Попробуйте еще раз:")
            return ADD_PRESERVE_STEP4

        context.user_data['preserve_quantity'] = quantity

        # Получаем доступные места из базы
        locations = db.get_available_locations()

        keyboard = []
        if locations:
            for loc in locations:
                keyboard.append([KeyboardButton(loc)])
            keyboard.append([KeyboardButton("➕ Добавить новое место"), KeyboardButton("🔙 Назад")])
        else:
            keyboard.append([KeyboardButton("➕ Добавить новое место")])
            keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Содержимое: <b>{context.user_data['preserve_content']}</b>\n"
            f"✅ Объем: <b>{context.user_data['preserve_volume']} л</b>\n"
            f"✅ Тип: <b>{context.user_data['preserve_note_desc']}</b>\n"
            f"✅ Количество: <b>{quantity} шт</b>\n\n"
            "🥫 <b>Добавление закатки - Шаг 5/5</b>\n\n"
            "Выберите место хранения:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRESERVE_STEP5

    except ValueError:
        await update.message.reply_text("❌ Введите целое число. Попробуйте еще раз:")
        return ADD_PRESERVE_STEP4


async def add_preserve_step4_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод своего количества закаток."""
    try:
        quantity = int(update.message.text.strip())

        if quantity <= 0:
            await update.message.reply_text("❌ Количество должно быть положительным числом. Попробуйте еще раз:")
            return ADD_PRESERVE_STEP4

        context.user_data['preserve_quantity'] = quantity

        locations = db.get_available_locations()

        keyboard = []
        if locations:
            for loc in locations:
                keyboard.append([KeyboardButton(loc)])
            keyboard.append([KeyboardButton("➕ Добавить новое место"), KeyboardButton("🔙 Назад")])
        else:
            keyboard.append([KeyboardButton("➕ Добавить новое место")])
            keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Содержимое: <b>{context.user_data['preserve_content']}</b>\n"
            f"✅ Объем: <b>{context.user_data['preserve_volume']} л</b>\n"
            f"✅ Тип: <b>{context.user_data['preserve_note_desc']}</b>\n"
            f"✅ Количество: <b>{quantity} шт</b>\n\n"
            "🥫 <b>Добавление закатки - Шаг 5/5</b>\n\n"
            "Выберите место хранения:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRESERVE_STEP5

    except ValueError:
        await update.message.reply_text("❌ Введите целое число. Попробуйте еще раз:")
        return ADD_PRESERVE_STEP4


async def add_preserve_step5_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор места хранения закатки."""
    text = update.message.text

    if text == "🔙 Назад":
        quantities = ["1", "2", "3", "5", "10", "15", "20"]
        keyboard = []
        for i in range(0, len(quantities), 3):
            row = quantities[i:i + 3]
            keyboard.append([KeyboardButton(qty) for qty in row])

        keyboard.append([KeyboardButton("✏️ Ввести другое"), KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Содержимое: <b>{context.user_data['preserve_content']}</b>\n"
            f"✅ Объем: <b>{context.user_data['preserve_volume']} л</b>\n"
            f"✅ Тип: <b>{context.user_data['preserve_note_desc']}</b>\n\n"
            "Выберите количество закаток:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRESERVE_STEP4

    elif text == "➕ Добавить новое место":
        await update.message.reply_text(
            "➕ Введите новое место хранения:",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRESERVE_STEP5

    # Это новое место, введенное пользователем
    if 'new_location' in context.user_data:
        location = context.user_data['new_location']
        db.add_location(location)
        del context.user_data['new_location']
    else:
        location = text

    # Добавляем закатку в базу данных
    preserve_data = {
        'content': context.user_data['preserve_content'],
        'volume': context.user_data['preserve_volume'],
        'quantity': context.user_data['preserve_quantity'],
        'note_code': context.user_data['preserve_note'],
        'location': location
    }

    success = db.add_preserve(**preserve_data)

    if success:
        grouped_preserves = db.get_preserves_grouped()
        added_key = (preserve_data['content'], preserve_data['volume'], preserve_data['note_code'])

        if added_key in grouped_preserves:
            group = grouped_preserves[added_key]
            locations_str = []
            for loc in group['locations']:
                locations_str.append(f"{loc['location']} ({loc['quantity']} шт)")

            message = (
                "✅ <b>Закатка успешно добавлена!</b>\n\n"
                f"🥫 <b>Содержимое:</b> {preserve_data['content']}\n"
                f"📏 <b>Объем:</b> {preserve_data['volume']} л\n"
                f"🏷️ <b>Тип:</b> {context.user_data['preserve_note_desc']}\n\n"
                f"📊 <b>Текущее состояние:</b>\n"
                f"• Общее количество: {group['total_quantity']} шт\n"
                f"• Места хранения: {', '.join(locations_str)}"
            )
        else:
            message = "✅ <b>Закатка успешно добавлена!</b>"

        context.user_data.clear()
    else:
        message = "❌ Ошибка при добавлении закатки. Попробуйте еще раз."

    return await start(update, context)


async def add_preserve_step5_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод нового места хранения."""
    location = update.message.text.strip()

    if not location:
        await update.message.reply_text("❌ Место не может быть пустым. Введите еще раз:")
        return ADD_PRESERVE_STEP5

    context.user_data['new_location'] = location

    keyboard = [[KeyboardButton(location), KeyboardButton("🔙 Назад")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Новое место: <b>{location}</b>\n\n"
        "Нажмите на место для подтверждения или вернитесь назад:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRESERVE_STEP5


async def add_product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс добавления продукта."""
    context.user_data.clear()

    product_history = db.get_product_history()

    # Показываем только историю, без стандартных значений
    keyboard = []
    for item in product_history:
        keyboard.append([KeyboardButton(item)])

    if product_history:
        keyboard.append([KeyboardButton("✏️ Ввести новое")])
    else:
        # Если истории нет, просто предлагаем ввести
        await update.message.reply_text(
            "🍚 <b>Добавление продукта - Шаг 1/3</b>\n\n"
            "ℹ️ <b>Примечание:</b> Если продукт с таким же названием и местом уже есть, количество будет увеличено.\n\n"
            "Введите название продукта:",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRODUCT_STEP1

    keyboard.append([KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🍚 <b>Добавление продукта - Шаг 1/3</b>\n\n"
        "ℹ️ <b>Примечание:</b> Если продукт с таким же названием и местом уже есть, количество будет увеличено.\n\n"
        "Выберите название продукта из истории или введите новое:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRODUCT_STEP1


async def add_product_step1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор названия продукта."""
    text = update.message.text

    if text == "🔙 Назад":
        return await add_menu(update, context)
    elif text == "✏️ Ввести новое":
        await update.message.reply_text(
            "✏️ Введите название продукта:",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRODUCT_STEP1

    context.user_data['product_name'] = text

    quantities = ["1", "2", "3", "5", "10", "15", "20"]
    keyboard = []
    for i in range(0, len(quantities), 3):
        row = quantities[i:i + 3]
        keyboard.append([KeyboardButton(qty) for qty in row])

    keyboard.append([KeyboardButton("✏️ Ввести другое"), KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Название: <b>{text}</b>\n\n"
        "🍚 <b>Добавление продукта - Шаг 2/3</b>\n\n"
        "Выберите количество:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRODUCT_STEP2


async def add_product_step1_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод своего названия продукта."""
    text = update.message.text

    if text in ["🔙 Назад", "✏️ Ввести новое"]:
        return await add_product_menu(update, context)

    name = text.strip()

    if not name:
        await update.message.reply_text("❌ Название не может быть пустым. Введите еще раз:")
        return ADD_PRODUCT_STEP1

    context.user_data['product_name'] = name

    quantities = ["1", "2", "3", "5", "10", "15", "20"]
    keyboard = []
    for i in range(0, len(quantities), 3):
        row = quantities[i:i + 3]
        keyboard.append([KeyboardButton(qty) for qty in row])

    keyboard.append([KeyboardButton("✏️ Ввести другое"), KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Название: <b>{name}</b>\n\n"
        "🍚 <b>Добавление продукта - Шаг 2/3</b>\n\n"
        "Выберите количество:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRODUCT_STEP2


async def add_product_step2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор количества продуктов."""
    text = update.message.text

    if text == "🔙 Назад":
        return await add_product_menu(update, context)
    elif text == "✏️ Ввести другое":
        await update.message.reply_text(
            "✏️ Введите количество (целое число):",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRODUCT_STEP2

    try:
        quantity = int(text)

        if quantity <= 0:
            await update.message.reply_text("❌ Количество должно быть положительным числом. Попробуйте еще раз:")
            return ADD_PRODUCT_STEP2

        context.user_data['product_quantity'] = quantity

        # Получаем доступные места из базы
        locations = db.get_available_locations()

        keyboard = []
        if locations:
            for loc in locations:
                keyboard.append([KeyboardButton(loc)])
            keyboard.append([KeyboardButton("➕ Добавить новое место"), KeyboardButton("🔙 Назад")])
        else:
            keyboard.append([KeyboardButton("➕ Добавить новое место")])
            keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Название: <b>{context.user_data['product_name']}</b>\n"
            f"✅ Количество: <b>{quantity} шт</b>\n\n"
            "🍚 <b>Добавление продукта - Шаг 3/3</b>\n\n"
            "Выберите место хранения:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRODUCT_STEP3

    except ValueError:
        await update.message.reply_text("❌ Введите целое число. Попробуйте еще раз:")
        return ADD_PRODUCT_STEP2


async def add_product_step2_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод своего количества продуктов."""
    try:
        quantity = int(update.message.text.strip())

        if quantity <= 0:
            await update.message.reply_text("❌ Количество должно быть положительным числом. Попробуйте еще раз:")
            return ADD_PRODUCT_STEP2

        context.user_data['product_quantity'] = quantity

        locations = db.get_available_locations()

        keyboard = []
        if locations:
            for loc in locations:
                keyboard.append([KeyboardButton(loc)])
            keyboard.append([KeyboardButton("➕ Добавить новое место"), KeyboardButton("🔙 Назад")])
        else:
            keyboard.append([KeyboardButton("➕ Добавить новое место")])
            keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Название: <b>{context.user_data['product_name']}</b>\n"
            f"✅ Количество: <b>{quantity} шт</b>\n\n"
            "🍚 <b>Добавление продукта - Шаг 3/3</b>\n\n"
            "Выберите место хранения:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRODUCT_STEP3

    except ValueError:
        await update.message.reply_text("❌ Введите целое число. Попробуйте еще раз:")
        return ADD_PRODUCT_STEP2


async def add_product_step3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор места хранения продукта."""
    text = update.message.text

    if text == "🔙 Назад":
        quantities = ["1", "2", "3", "5", "10", "15", "20"]
        keyboard = []
        for i in range(0, len(quantities), 3):
            row = quantities[i:i + 3]
            keyboard.append([KeyboardButton(qty) for qty in row])

        keyboard.append([KeyboardButton("✏️ Ввести другое"), KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Название: <b>{context.user_data['product_name']}</b>\n\n"
            "Выберите количество:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        return ADD_PRODUCT_STEP2

    elif text == "➕ Добавить новое место":
        await update.message.reply_text(
            "➕ Введите новое место хранения:",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRODUCT_STEP3

    # Это новое место, введенное пользователем
    if 'new_location' in context.user_data:
        location = context.user_data['new_location']
        db.add_location(location)
        del context.user_data['new_location']
    else:
        location = text

    # Добавляем продукт в базу данных
    success = db.add_product(
        name=context.user_data['product_name'],
        quantity=context.user_data['product_quantity'],
        location=location
    )

    if success:
        grouped_products = db.get_products_grouped()
        product_name = context.user_data['product_name']

        if product_name in grouped_products:
            group = grouped_products[product_name]
            locations_str = []
            for loc in group['locations']:
                locations_str.append(f"{loc['location']} ({loc['quantity']} шт)")

            message = (
                "✅ <b>Продукт успешно добавлен!</b>\n\n"
                f"🍚 <b>Название:</b> {context.user_data['product_name']}\n\n"
                f"📊 <b>Текущее состояние:</b>\n"
                f"• Общее количество: {group['total_quantity']} шт\n"
                f"• Места хранения: {', '.join(locations_str)}"
            )
        else:
            message = "✅ <b>Продукт успешно добавлен!</b>"

        context.user_data.clear()
    else:
        message = "❌ Ошибка при добавлении продукта. Попробуйте еще раз."

    return await start(update, context)


async def add_product_step3_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод нового места хранения продукта."""
    location = update.message.text.strip()

    if not location:
        await update.message.reply_text("❌ Место не может быть пустым. Введите еще раз:")
        return ADD_PRODUCT_STEP3

    context.user_data['new_location'] = location

    keyboard = [[KeyboardButton(location), KeyboardButton("🔙 Назад")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Новое место: <b>{location}</b>\n\n"
        "Нажмите на место для подтверждения или вернитесь назад:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return ADD_PRODUCT_STEP3


# ========== ПОИСК ==========

async def search_preserves_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню поиска закаток."""
    context.user_data.clear()

    keyboard = [
        [KeyboardButton("🔍 Поиск по названию"), KeyboardButton("📏 По объему")],
        [KeyboardButton("🏷️ По типу"), KeyboardButton("📍 По месту")],
        [KeyboardButton("🔙 Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🔍 <b>Поиск закаток</b>\n\n"
        "Выберите критерий поиска:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    return SEARCH_PRESERVES_STEP1


async def search_preserves_step1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор критерия поиска."""
    text = update.message.text

    if text == "🔙 Назад":
        return await preserves_menu(update, context)

    context.user_data['search_criteria'] = {}

    if text == "🔍 Поиск по названию":
        preserve_history = db.get_preserve_history()

        keyboard = []
        for content in preserve_history:
            keyboard.append([KeyboardButton(content)])

        if preserve_history:
            keyboard.append([KeyboardButton("✏️ Ввести своё")])

        keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "🔍 <b>Поиск по названию</b>\n\n"
            "Выберите название или введите свое:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        context.user_data['search_type'] = 'content'
        return SEARCH_PRESERVES_STEP2

    elif text == "📏 По объему":
        volumes = db.get_available_volumes()
        keyboard = []
        for vol in volumes:
            keyboard.append([KeyboardButton(f"{vol} л")])

        keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "📏 <b>Поиск по объему</b>\n\n"
            "Выберите объем:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        context.user_data['search_type'] = 'volume'
        return SEARCH_PRESERVES_STEP2

    elif text == "🏷️ По типу":
        notes = db.get_available_notes()
        keyboard = []
        for code, desc in notes.items():
            keyboard.append([KeyboardButton(f"{desc}")])

        keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "🏷️ <b>Поиск по типу</b>\n\n"
            "Выберите тип:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        context.user_data['search_type'] = 'note'
        return SEARCH_PRESERVES_STEP2

    elif text == "📍 По месту":
        locations = db.get_available_locations()
        keyboard = []
        for loc in locations:
            keyboard.append([KeyboardButton(loc)])

        keyboard.append([KeyboardButton("🔙 Назад")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "📍 <b>Поиск по месту</b>\n\n"
            "Выберите место:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        context.user_data['search_type'] = 'location'
        return SEARCH_PRESERVES_STEP2

    return SEARCH_PRESERVES_STEP1


async def search_preserves_step2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает второй шаг поиска."""
    text = update.message.text

    if text == "🔙 Назад":
        return await search_preserves_menu(update, context)

    search_type = context.user_data.get('search_type')

    if text == "✏️ Ввести своё" and search_type == 'content':
        await update.message.reply_text(
            "✏️ Введите название для поиска:",
            parse_mode=ParseMode.HTML
        )
        return SEARCH_PRESERVES_STEP2

    # Определяем критерии поиска в зависимости от типа
    criteria = {}

    if search_type == 'content':
        criteria['content'] = text
    elif search_type == 'volume':
        try:
            volume = float(text.replace(" л", ""))
            criteria['volume_min'] = volume
            criteria['volume_max'] = volume
        except ValueError:
            await update.message.reply_text("❌ Ошибка при обработке объема. Попробуйте еще раз:")
            return SEARCH_PRESERVES_STEP2
    elif search_type == 'note':
        notes = db.get_available_notes()
        note_code = None
        for code, desc in notes.items():
            if desc == text:
                note_code = code
                break

        if note_code:
            criteria['note_code'] = note_code
        else:
            await update.message.reply_text("❌ Ошибка при обработке типа. Попробуйте еще раз:")
            return SEARCH_PRESERVES_STEP2
    elif search_type == 'location':
        criteria['location'] = text

    # Выполняем поиск
    results = db.search_preserves(**criteria)

    if not results:
        message = "🔍 По вашему запросу ничего не найдено."
    else:
        message = f"🔍 <b>Найдено групп закаток:</b> {len(results)}\n\n"
        message += format_preserves_grouped(results)

    keyboard = [[KeyboardButton("🔍 Новый поиск"), KeyboardButton("🏠 Главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    # Очищаем временные данные
    context.user_data.clear()

    return MAIN_MENU


async def search_preserves_step2_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод своего названия для поиска."""
    text = update.message.text

    if text == "🔙 Назад":
        return await search_preserves_menu(update, context)

    # Просто выполняем поиск по введенному названию
    results = db.search_preserves(content=text)

    if not results:
        message = "🔍 По вашему запросу ничего не найдено."
    else:
        message = f"🔍 <b>Найдено групп закаток:</b> {len(results)}\n\n"
        message += format_preserves_grouped(results)

    keyboard = [[KeyboardButton("🔍 Новый поиск"), KeyboardButton("🏠 Главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    # Очищаем временные данные
    context.user_data.clear()

    return MAIN_MENU


# ========== УДАЛЕНИЕ ==========

async def remove_preserve_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню удаления закаток."""
    context.user_data.clear()

    grouped_preserves = db.get_preserves_grouped()

    if not grouped_preserves:
        await update.message.reply_text(
            "📭 Нет закаток для удаления.",
            parse_mode=ParseMode.HTML
        )
        return await preserves_menu(update, context)

    # Создаем список для выбора
    preserves_list = []
    for key, group in grouped_preserves.items():
        preserves_list.append({
            'content': group['content'],
            'volume': group['volume'],
            'note_description': group['note_description'],
            'total_quantity': group['total_quantity']
        })

    # Сохраняем список в контексте
    context.user_data['preserves_list'] = preserves_list

    # Показываем первые 10 закаток для выбора
    keyboard = []
    for i, preserve in enumerate(preserves_list[:10], 1):
        keyboard.append([KeyboardButton(f"{i}. {preserve['content']} ({preserve['volume']}л)")])

    keyboard.append([KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    message = "🗑️ <b>Удаление закатки</b>\n\n"
    message += "Выберите закатку для удаления:\n\n"

    for i, preserve in enumerate(preserves_list[:10], 1):
        message += f"{i}. {preserve['content']} ({preserve['volume']}л, {preserve['note_description']}) - {preserve['total_quantity']} шт\n"

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return REMOVE_PRESERVE_STEP1


async def remove_preserve_step1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор закатки для удаления."""
    text = update.message.text

    if text == "🔙 Назад":
        return await preserves_menu(update, context)

    try:
        # Пытаемся извлечь номер из текста
        if text.startswith(tuple(str(i) for i in range(1, 11))):
            # Формат: "1. Помидоры (1л)"
            selected_num = int(text.split(".")[0])
            preserves_list = context.user_data.get('preserves_list', [])

            if 1 <= selected_num <= len(preserves_list):
                selected_preserve = preserves_list[selected_num - 1]

                # Сохраняем выбранную закатку
                context.user_data['selected_preserve'] = selected_preserve

                # Получаем детальную информацию о местах хранения
                grouped_preserves = db.get_preserves_grouped()
                for key, group in grouped_preserves.items():
                    if (group['content'] == selected_preserve['content'] and
                            group['volume'] == selected_preserve['volume']):
                        context.user_data['preserve_details'] = group
                        break

                # Создаем клавиатуру с местами
                group = context.user_data.get('preserve_details', {})
                keyboard = []

                if group and 'locations' in group:
                    for loc in group['locations']:
                        keyboard.append([KeyboardButton(f"{loc['location']} ({loc['quantity']} шт)")])

                keyboard.append([KeyboardButton("🗑️ Удалить все"), KeyboardButton("🔙 Назад")])

                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                message = (
                    f"🗑️ <b>Удаление закатки:</b> {selected_preserve['content']} ({selected_preserve['volume']}л)\n\n"
                    f"📊 Всего: {selected_preserve['total_quantity']} шт\n\n"
                    "Выберите место для удаления или удалите все:"
                )

                await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

                return REMOVE_PRESERVE_STEP2
            else:
                await update.message.reply_text("❌ Неверный номер. Попробуйте еще раз:")
                return REMOVE_PRESERVE_STEP1
        else:
            await update.message.reply_text("❌ Пожалуйста, выберите закатку из списка:")
            return REMOVE_PRESERVE_STEP1

    except (ValueError, IndexError):
        await update.message.reply_text("❌ Ошибка при выборе. Попробуйте еще раз:")
        return REMOVE_PRESERVE_STEP1


async def remove_preserve_step2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор места для удаления."""
    text = update.message.text

    if text == "🔙 Назад":
        return await remove_preserve_menu(update, context)

    selected_preserve = context.user_data.get('selected_preserve', {})
    preserve_details = context.user_data.get('preserve_details', {})

    if text == "🗑️ Удалить все":
        # Удаляем все экземпляры закатки
        if preserve_details and 'locations' in preserve_details:
            total_removed = 0
            success = True

            # Удаляем из каждого места
            for loc in preserve_details['locations']:
                # Находим код примечания
                notes = db.get_available_notes()
                note_code = None
                for code, desc in notes.items():
                    if desc == selected_preserve['note_description']:
                        note_code = code
                        break

                if note_code:
                    removed = db.remove_preserve(
                        content=selected_preserve['content'],
                        volume=selected_preserve['volume'],
                        note_code=note_code,
                        location=loc['location'],
                        quantity=loc['quantity']
                    )

                    if removed:
                        total_removed += loc['quantity']
                    else:
                        success = False

            if success and total_removed > 0:
                message = f"✅ Удалено {total_removed} шт закатки '{selected_preserve['content']}' ({selected_preserve['volume']}л)"
            else:
                message = "❌ Ошибка при удалении."

        context.user_data.clear()
        return await start(update, context)

    else:
        # Извлекаем название места из текста
        # Формат: "Кладовая (10 шт)"
        try:
            location = text.split(" (")[0]

            # Сохраняем выбранное место
            context.user_data['selected_location'] = location

            # Находим количество в этом месте
            quantity_in_location = 0
            if preserve_details and 'locations' in preserve_details:
                for loc in preserve_details['locations']:
                    if loc['location'] == location:
                        quantity_in_location = loc['quantity']
                        break

            if quantity_in_location > 0:
                # Создаем клавиатуру с количеством
                quantities = []
                if quantity_in_location >= 1:
                    quantities.append("1")
                if quantity_in_location >= 2:
                    quantities.append("2")
                if quantity_in_location >= 3:
                    quantities.append("3")
                if quantity_in_location >= 5:
                    quantities.append("5")
                if quantity_in_location >= 10:
                    quantities.append("10")

                keyboard = []
                for qty in quantities:
                    keyboard.append([KeyboardButton(f"{qty} шт")])

                keyboard.append([KeyboardButton(f"Все ({quantity_in_location} шт)"), KeyboardButton("🔙 Назад")])

                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                message = (
                    f"🗑️ <b>Удаление закатки:</b> {selected_preserve['content']} ({selected_preserve['volume']}л)\n"
                    f"📍 Место: {location}\n"
                    f"📦 Доступно: {quantity_in_location} шт\n\n"
                    "Выберите количество для удаления:"
                )

                await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

                return REMOVE_PRESERVE_STEP3
            else:
                await update.message.reply_text("❌ Ошибка: не найдено количество в этом месте.")
                return REMOVE_PRESERVE_STEP2

        except (ValueError, IndexError):
            await update.message.reply_text("❌ Ошибка при выборе места. Попробуйте еще раз:")
            return REMOVE_PRESERVE_STEP2


async def remove_preserve_step3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор количества для удаления."""
    text = update.message.text

    if text == "🔙 Назад":
        return await remove_preserve_step1_handler(update, context)

    selected_preserve = context.user_data.get('selected_preserve', {})
    selected_location = context.user_data.get('selected_location', '')

    try:
        if text.startswith("Все"):
            # Извлекаем количество из скобок
            quantity_str = text.split("(")[1].split(" ")[0]
            quantity_to_remove = int(quantity_str)
        else:
            # Формат: "5 шт"
            quantity_to_remove = int(text.split(" ")[0])

        # Находим код примечания
        notes = db.get_available_notes()
        note_code = None
        for code, desc in notes.items():
            if desc == selected_preserve['note_description']:
                note_code = code
                break

        if note_code:
            success = db.remove_preserve(
                content=selected_preserve['content'],
                volume=selected_preserve['volume'],
                note_code=note_code,
                location=selected_location,
                quantity=quantity_to_remove
            )

            if success:
                message = f"✅ Удалено {quantity_to_remove} шт закатки '{selected_preserve['content']}' ({selected_preserve['volume']}л) из {selected_location}"
            else:
                message = "❌ Ошибка при удалении."
        else:
            message = "❌ Ошибка: не найден тип закатки."

        context.user_data.clear()
        return await start(update, context)

    except (ValueError, IndexError):
        await update.message.reply_text("❌ Ошибка при выборе количества. Попробуйте еще раз:")
        return REMOVE_PRESERVE_STEP3


async def remove_product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню удаления продуктов."""
    context.user_data.clear()

    grouped_products = db.get_products_grouped()

    if not grouped_products:
        await update.message.reply_text(
            "🍚 Нет продуктов для удаления.",
            parse_mode=ParseMode.HTML
        )
        return await products_menu(update, context)

    # Создаем список для выбора
    products_list = []
    for name, group in grouped_products.items():
        products_list.append({
            'name': group['name'],
            'total_quantity': group['total_quantity']
        })

    # Сохраняем список в контексте
    context.user_data['products_list'] = products_list

    # Показываем первые 10 продуктов для выбора
    keyboard = []
    for i, product in enumerate(products_list[:10], 1):
        keyboard.append([KeyboardButton(f"{i}. {product['name']}")])

    keyboard.append([KeyboardButton("🔙 Назад")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    message = "🗑️ <b>Удаление продукта</b>\n\n"
    message += "Выберите продукт для удаления:\n\n"

    for i, product in enumerate(products_list[:10], 1):
        message += f"{i}. {product['name']} - {product['total_quantity']} шт\n"

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return REMOVE_PRODUCT_STEP1


async def remove_product_step1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор продукта для удаления."""
    text = update.message.text

    if text == "🔙 Назад":
        return await products_menu(update, context)

    try:
        # Пытаемся извлечь номер из текста
        if text.startswith(tuple(str(i) for i in range(1, 11))):
            # Формат: "1. Гречка"
            selected_num = int(text.split(".")[0])
            products_list = context.user_data.get('products_list', [])

            if 1 <= selected_num <= len(products_list):
                selected_product = products_list[selected_num - 1]

                # Сохраняем выбранный продукт
                context.user_data['selected_product'] = selected_product

                # Получаем детальную информацию о местах хранения
                grouped_products = db.get_products_grouped()
                for name, group in grouped_products.items():
                    if group['name'] == selected_product['name']:
                        context.user_data['product_details'] = group
                        break

                # Создаем клавиатуру с местами
                group = context.user_data.get('product_details', {})
                keyboard = []

                if group and 'locations' in group:
                    for loc in group['locations']:
                        keyboard.append([KeyboardButton(f"{loc['location']} ({loc['quantity']} шт)")])

                keyboard.append([KeyboardButton("🗑️ Удалить все"), KeyboardButton("🔙 Назад")])

                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                message = (
                    f"🗑️ <b>Удаление продукта:</b> {selected_product['name']}\n\n"
                    f"📊 Всего: {selected_product['total_quantity']} шт\n\n"
                    "Выберите место для удаления или удалите все:"
                )

                await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

                return REMOVE_PRODUCT_STEP2
            else:
                await update.message.reply_text("❌ Неверный номер. Попробуйте еще раз:")
                return REMOVE_PRODUCT_STEP1
        else:
            await update.message.reply_text("❌ Пожалуйста, выберите продукт из списка:")
            return REMOVE_PRODUCT_STEP1

    except (ValueError, IndexError):
        await update.message.reply_text("❌ Ошибка при выборе. Попробуйте еще раз:")
        return REMOVE_PRODUCT_STEP1


async def remove_product_step2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор места для удаления продукта."""
    text = update.message.text

    if text == "🔙 Назад":
        return await remove_product_menu(update, context)

    selected_product = context.user_data.get('selected_product', {})
    product_details = context.user_data.get('product_details', {})

    if text == "🗑️ Удалить все":
        # Удаляем все экземпляры продукта
        if product_details and 'locations' in product_details:
            total_removed = 0
            success = True

            # Удаляем из каждого места
            for loc in product_details['locations']:
                removed = db.remove_product(
                    name=selected_product['name'],
                    location=loc['location'],
                    quantity=loc['quantity']
                )

                if removed:
                    total_removed += loc['quantity']
                else:
                    success = False

            if success and total_removed > 0:
                message = f"✅ Удалено {total_removed} шт продукта '{selected_product['name']}'"
            else:
                message = "❌ Ошибка при удалении."

        context.user_data.clear()
        return await start(update, context)

    else:
        # Извлекаем название места из текста
        # Формат: "Кладовая (10 шт)"
        try:
            location = text.split(" (")[0]

            # Сохраняем выбранное место
            context.user_data['selected_location'] = location

            # Находим количество в этом месте
            quantity_in_location = 0
            if product_details and 'locations' in product_details:
                for loc in product_details['locations']:
                    if loc['location'] == location:
                        quantity_in_location = loc['quantity']
                        break

            if quantity_in_location > 0:
                # Создаем клавиатуру с количеством
                quantities = []
                if quantity_in_location >= 1:
                    quantities.append("1")
                if quantity_in_location >= 2:
                    quantities.append("2")
                if quantity_in_location >= 3:
                    quantities.append("3")
                if quantity_in_location >= 5:
                    quantities.append("5")
                if quantity_in_location >= 10:
                    quantities.append("10")

                keyboard = []
                for qty in quantities:
                    keyboard.append([KeyboardButton(f"{qty} шт")])

                keyboard.append([KeyboardButton(f"Все ({quantity_in_location} шт)"), KeyboardButton("🔙 Назад")])

                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                message = (
                    f"🗑️ <b>Удаление продукта:</b> {selected_product['name']}\n"
                    f"📍 Место: {location}\n"
                    f"📦 Доступно: {quantity_in_location} шт\n\n"
                    "Выберите количество для удаления:"
                )

                await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

                return REMOVE_PRODUCT_STEP3
            else:
                await update.message.reply_text("❌ Ошибка: не найдено количество в этом месте.")
                return REMOVE_PRODUCT_STEP2

        except (ValueError, IndexError):
            await update.message.reply_text("❌ Ошибка при выборе места. Попробуйте еще раз:")
            return REMOVE_PRODUCT_STEP2


async def remove_product_step3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор количества для удаления продукта."""
    text = update.message.text

    if text == "🔙 Назад":
        return await remove_product_step1_handler(update, context)

    selected_product = context.user_data.get('selected_product', {})
    selected_location = context.user_data.get('selected_location', '')

    try:
        if text.startswith("Все"):
            # Извлекаем количество из скобок
            quantity_str = text.split("(")[1].split(" ")[0]
            quantity_to_remove = int(quantity_str)
        else:
            # Формат: "5 шт"
            quantity_to_remove = int(text.split(" ")[0])

        success = db.remove_product(
            name=selected_product['name'],
            location=selected_location,
            quantity=quantity_to_remove
        )

        if success:
            message = f"✅ Удалено {quantity_to_remove} шт продукта '{selected_product['name']}' из {selected_location}"
        else:
            message = "❌ Ошибка при удалении."

        context.user_data.clear()
        return await start(update, context)

    except (ValueError, IndexError):
        await update.message.reply_text("❌ Ошибка при выборе количества. Попробуйте еще раз:")
        return REMOVE_PRODUCT_STEP3


# ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==========

async def manage_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление местами хранения."""
    locations = db.get_available_locations()

    if not locations:
        message = "📍 Нет сохраненных мест хранения."
    else:
        message = "📍 <b>Доступные места хранения:</b>\n\n"
        for i, location in enumerate(locations, 1):
            message += f"{i}. {location}\n"

    keyboard = [[KeyboardButton("🔙 Назад")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return MANAGE_LOCATIONS


async def manage_locations_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик управления местами."""
    text = update.message.text

    if text == "🔙 Назад":
        return await add_menu(update, context)
    else:
        return await start(update, context)


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику хранилища."""
    stats = db.get_statistics()

    message = (
        "📊 <b>Статистика хранилища</b>\n\n"
        f"🥫 <b>Всего закаток:</b> {stats['total_preserves']} шт\n"
        f"🍚 <b>Продуктов:</b> {stats['total_products']} шт\n"
        f"🎯 <b>Уникальных видов консервов:</b> {stats['unique_contents']}\n"
        f"📍 <b>Уникальных мест хранения:</b> {stats['unique_locations']}\n\n"
    )

    if stats['content_stats']:
        message += "<b>📈 По содержимому (топ-5):</b>\n"
        sorted_contents = sorted(stats['content_stats'].items(), key=lambda x: x[1], reverse=True)[:5]
        for content, count in sorted_contents:
            message += f"  • {content}: {count} шт\n"
        message += "\n"

    if stats['volume_stats']:
        message += "<b>📏 По объему:</b>\n"
        for volume, count in sorted(stats['volume_stats'].items()):
            message += f"  • {volume} л: {count} шт\n"

    keyboard = [[KeyboardButton("🔙 Назад"), KeyboardButton("🏠 Главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return STATS_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет текущую операцию."""
    return await start(update, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ошибки бота."""
    logger.error(f"Ошибка: {context.error}")

    if update and update.effective_message:
        return await start(update, context)

    return ConversationHandler.END


def main():
    """Основная функция для запуска бота."""
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],

            PRESERVES_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, preserves_menu_handler)],
            PRODUCTS_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, products_menu_handler)],
            ADD_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_menu_handler)],
            SEARCH_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_menu_handler)],
            STATS_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, stats_menu_handler)],
            HELP_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, help_menu_handler)],

            # Добавление закатки
            ADD_PRESERVE_STEP1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_preserve_step1_handler),
            ],
            ADD_PRESERVE_STEP2: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_preserve_step2_handler)],
            ADD_PRESERVE_STEP3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_preserve_step3_handler)],
            ADD_PRESERVE_STEP4: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_preserve_step4_handler),
            ],
            ADD_PRESERVE_STEP5: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_preserve_step5_handler),
            ],

            # Добавление продукта
            ADD_PRODUCT_STEP1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_step1_handler),
            ],
            ADD_PRODUCT_STEP2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_step2_handler),
            ],
            ADD_PRODUCT_STEP3: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_step3_handler),
            ],

            # Поиск закаток
            SEARCH_PRESERVES_STEP1: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_preserves_step1_handler)],
            SEARCH_PRESERVES_STEP2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_preserves_step2_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_preserves_step2_custom_handler)
            ],

            # Управление местами
            MANAGE_LOCATIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, manage_locations_handler)],

            # Удаление закаток
            REMOVE_PRESERVE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_preserve_menu)],
            REMOVE_PRESERVE_STEP1: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_preserve_step1_handler)],
            REMOVE_PRESERVE_STEP2: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_preserve_step2_handler)],
            REMOVE_PRESERVE_STEP3: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_preserve_step3_handler)],

            # Удаление продуктов
            REMOVE_PRODUCT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_product_menu)],
            REMOVE_PRODUCT_STEP1: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_product_step1_handler)],
            REMOVE_PRODUCT_STEP2: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_product_step2_handler)],
            REMOVE_PRODUCT_STEP3: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_product_step3_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()