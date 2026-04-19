import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import json
import random
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = '@EventsSearch'

bot = telebot.TeleBot(TOKEN)

# ===== СОСТОЯНИЕ =====
user_mode = {}

# ===== САЙТЫ =====
sites = [
    ("🎬 Кино Globus", "https://kino.s-globus.ru/"),
    ("🎟 Квесты", "https://xn--b1alfrj.xn--b1acdcqi5ci.xn--p1ai"),
]

# ===== МЕНЮ =====
def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎯 Квесты", "🌐 Квесты с сайта")
    markup.add("🎬 Фильм", "🌐 Сайты")
    return markup

# ===== МЕНЮ КВЕСТОВ =====
def quest_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➡️ Ещё квест")
    markup.add("🔙 Назад")
    return markup

# ===== МЕНЮ ФИЛЬМОВ =====
def movie_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➡️ Ещё фильм")
    markup.add("🔙 Назад")
    return markup

# ===== ТРЕЙЛЕР =====
def get_trailer_link(title):
    query = title.replace(" ", "+") + "+трейлер"
    return f"https://www.youtube.com/results?search_query={query}"

# ===== ФИЛЬМЫ =====
def get_movies():
    url = "https://kino.s-globus.ru/"

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        films = []

        for film in soup.find_all('div', class_='film'):
            title = film.get_text(strip=True)

            img_tag = film.find('img')
            image = None

            if img_tag:
                image = img_tag.get('src')
                if image and image.startswith('/'):
                    image = "https://kino.s-globus.ru" + image

            films.append({
                "title": title,
                "image": image
            })

        return films

    except:
        return []

# ===== КВЕСТЫ С САЙТА =====
def get_quests_from_site():
    base_url = "https://xn--b1alfrj.xn--b1acdcqi5ci.xn--p1ai"

    try:
        response = requests.get(base_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        quests = []

        links = soup.find_all('a', href=True)
        quest_links = []

        for link in links:
            href = link['href']
            if "/quest" in href:
                full_url = base_url + href
                if full_url not in quest_links:
                    quest_links.append(full_url)

        for url in quest_links[:10]:
            try:
                r = requests.get(url, timeout=10)
                s = BeautifulSoup(r.text, 'html.parser')

                title_tag = s.find('h1')
                title = title_tag.get_text(strip=True) if title_tag else "Без названия"

                data = {}
                for dt in s.find_all('dt'):
                    key = dt.get_text(strip=True)
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        data[key] = dd.get_text(strip=True)

                desc_block = s.find('div', class_='mb-5')
                description = "Описание отсутствует"

                if desc_block:
                    p = desc_block.find('p')
                    if p:
                        description = p.get_text(strip=True)

                text = f"🎯 {title}\n\n"

                if "Цена" in data:
                    text += f"💸 Цена: {data['Цена']}\n"
                if "Команда" in data:
                    text += f"👥 Игроки: {data['Команда']}\n"
                if "Время" in data:
                    text += f"⏱ Время: {data['Время']}\n"

                text += f"\n📖 {description}"

                quests.append(text)

            except Exception as e:
                print("Ошибка квеста:", e)

        return quests

    except Exception as e:
        print("Ошибка парсинга:", e)
        return []

# ===== КВЕСТЫ ИЗ КАНАЛА =====
try:
    with open("quests.json", "r", encoding="utf-8") as f:
        quests = json.load(f)
except:
    quests = []

def save_quests():
    with open("quests.json", "w", encoding="utf-8") as f:
        json.dump(quests, f, ensure_ascii=False, indent=4)

@bot.channel_post_handler(content_types=['photo', 'text'])
def handle_channel_post(message):
    text = message.caption if message.caption else message.text
    photo_id = None

    if message.photo:
        photo_id = message.photo[-1].file_id

    quests.append({
        "text": text,
        "photo": photo_id
    })

    save_quests()
    print("✅ Сохранено из канала")

# ===== START =====
@bot.message_handler(commands=['start'])
def start(message):
    text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🎯 Я помогу тебе найти:\n"
        "• квесты\n"
        "• фильмы 🎬\n"
        "• сайты 🌐\n\n"
        "👇 Выбирай:"
    )

    bot.send_message(message.chat.id, text, reply_markup=menu())

# ===== КВЕСТЫ (КАНАЛ) =====
@bot.message_handler(func=lambda message: message.text == "🎯 Квесты")
def send_quest(message):
    user_mode[message.chat.id] = "channel"

    if not quests:
        bot.send_message(message.chat.id, "Пока нет квестов 😢")
        return

    quest = random.choice(quests)

    if quest["photo"]:
        bot.send_photo(message.chat.id, quest["photo"], caption=quest["text"], reply_markup=quest_menu())
    else:
        bot.send_message(message.chat.id, quest["text"], reply_markup=quest_menu())

# ===== КВЕСТЫ (САЙТ) =====
@bot.message_handler(func=lambda message: message.text == "🌐 Квесты с сайта")
def site_quests(message):
    user_mode[message.chat.id] = "site"

    bot.send_message(message.chat.id, "🔄 Загружаю...")

    quests_site = get_quests_from_site()

    if not quests_site:
        bot.send_message(message.chat.id, "❌ Не удалось получить квесты")
        return

    quest = random.choice(quests_site)
    bot.send_message(message.chat.id, quest, reply_markup=quest_menu())

# ===== ЕЩЁ КВЕСТ =====
@bot.message_handler(func=lambda message: message.text == "➡️ Ещё квест")
def more_quest(message):
    mode = user_mode.get(message.chat.id)

    if mode == "channel":
        send_quest(message)
    elif mode == "site":
        site_quests(message)
    else:
        bot.send_message(message.chat.id, "Сначала выбери раздел 👇", reply_markup=menu())

# ===== ФИЛЬМЫ =====
@bot.message_handler(func=lambda message: message.text == "🎬 Фильм")
def movie(message):
    user_mode[message.chat.id] = "movie"

    films = get_movies()

    if not films:
        bot.send_message(message.chat.id, "❌ Не удалось получить фильмы")
        return

    film = random.choice(films)
    trailer_link = get_trailer_link(film["title"])

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 Смотреть трейлер", url=trailer_link))

    try:
        if film["image"]:
            bot.send_photo(message.chat.id, film["image"], caption=f"🎬 {film['title']}", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, f"🎬 {film['title']}", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, f"🎬 {film['title']}", reply_markup=markup)

    bot.send_message(message.chat.id, "👇 Выбери:", reply_markup=movie_menu())

# ===== ЕЩЁ ФИЛЬМ =====
@bot.message_handler(func=lambda message: message.text == "➡️ Ещё фильм")
def more_movie(message):
    mode = user_mode.get(message.chat.id)

    if mode == "movie":
        movie(message)
    else:
        bot.send_message(message.chat.id, "Сначала выбери раздел 👇", reply_markup=menu())

# ===== САЙТЫ =====
@bot.message_handler(func=lambda message: message.text == "🌐 Сайты")
def show_sites(message):
    markup = types.InlineKeyboardMarkup()

    for name, url in sites:
        markup.add(types.InlineKeyboardButton(text=name, url=url))

    bot.send_message(message.chat.id, "Выбери:", reply_markup=markup)

# ===== НАЗАД =====
@bot.message_handler(func=lambda message: message.text == "🔙 Назад")
def back(message):
    bot.send_message(message.chat.id, "Главное меню 👇", reply_markup=menu())

# ===== ЗАПУСК =====
print("🚀 Бот запущен...")
bot.polling(none_stop=True)