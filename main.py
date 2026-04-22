import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import json

from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = '@EventsSearch'

bot = telebot.TeleBot(TOKEN)

user_mode = {}
quest_index = {}
movie_index = {}

def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎯 Квесты", "🌐 Квесты с сайта")
    markup.add("🎬 Фильм", "🌐 Сайты")
    return markup

def quest_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➡️ Ещё квест")
    markup.add("🔙 Назад")
    return markup

def movie_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➡️ Ещё фильм")
    markup.add("🔙 Назад")
    return markup

def get_movies():
    try:
        response = requests.get("https://kino.s-globus.ru/", timeout=10)
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

def get_quests_from_site():
    base_url = "https://xn--b1alfrj.xn--b1acdcqi5ci.xn--p1ai"

    try:
        response = requests.get(base_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        quests = []
        links = soup.find_all('a', href=True)

        for link in links:
            href = link['href']
            if "/quest" in href:
                url = base_url + href

                try:
                    r = requests.get(url, timeout=10)
                    s = BeautifulSoup(r.text, 'html.parser')

                    title = s.find('h1').get_text(strip=True)

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

                except:
                    continue

        return quests

    except Exception as e:
        print("Ошибка парсинга:", e)
        return []

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
    photo_id = message.photo[-1].file_id if message.photo else None

    quests.append({"text": text, "photo": photo_id})
    save_quests()

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Привет! Выбери:", reply_markup=menu())

@bot.message_handler(func=lambda message: "Квесты" in message.text and "с сайта" not in message.text)
def send_quest(message):
    user_mode[message.chat.id] = "channel"

    if not quests:
        bot.send_message(message.chat.id, "Нет квестов 😢")
        return

    import random
    quest = random.choice(quests)

    if quest["photo"]:
        bot.send_photo(message.chat.id, quest["photo"], caption=quest["text"], reply_markup=quest_menu())
    else:
        bot.send_message(message.chat.id, quest["text"], reply_markup=quest_menu())

@bot.message_handler(func=lambda message: "Квесты с сайта" in message.text)
def site_quests(message):
    user_mode[message.chat.id] = "site"

    loading = bot.send_message(message.chat.id, "🔄 Загружаю...")

    quests_site = get_quests_from_site()

    try:
        bot.delete_message(message.chat.id, loading.message_id)
    except:
        pass

    if not quests_site:
        bot.send_message(message.chat.id, "Ошибка загрузки")
        return

    chat_id = message.chat.id

    if chat_id not in quest_index:
        quest_index[chat_id] = 0

    quest = quests_site[quest_index[chat_id]]

    quest_index[chat_id] += 1
    if quest_index[chat_id] >= len(quests_site):
        quest_index[chat_id] = 0

    bot.send_message(message.chat.id, quest, reply_markup=quest_menu())

@bot.message_handler(func=lambda message: "Ещё квест" in message.text)
def more_quest(message):
    if user_mode.get(message.chat.id) == "site":
        site_quests(message)
    else:
        send_quest(message)

@bot.message_handler(func=lambda message: "Фильм" in message.text)
def movie(message):
    user_mode[message.chat.id] = "movie"

    loading = bot.send_message(message.chat.id, "🔄 Загружаю фильмы...")

    films = get_movies()

    try:
        bot.delete_message(message.chat.id, loading.message_id)
    except:
        pass

    if not films:
        bot.send_message(message.chat.id, "❌ Нет фильмов")
        return

    chat_id = message.chat.id

    if chat_id not in movie_index:
        movie_index[chat_id] = 0

    film = films[movie_index[chat_id]]

    movie_index[chat_id] += 1
    if movie_index[chat_id] >= len(films):
        movie_index[chat_id] = 0

    try:
        if film["image"]:
            bot.send_photo(message.chat.id, film["image"], caption=f"🎬 {film['title']}")
        else:
            bot.send_message(message.chat.id, f"🎬 {film['title']}")
    except:
        bot.send_message(message.chat.id, f"🎬 {film['title']}")

    bot.send_message(message.chat.id, "👇 Выбери:", reply_markup=movie_menu())

@bot.message_handler(func=lambda message: "Ещё фильм" in message.text)
def more_movie(message):
    movie(message)

@bot.message_handler(func=lambda message: "Сайты" in message.text)
def show_sites(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 Кино", url="https://kino.s-globus.ru/"))
    markup.add(types.InlineKeyboardButton("🎟 Квесты", url="https://xn--b1alfrj.xn--b1acdcqi5ci.xn--p1ai"))
    bot.send_message(message.chat.id, "Выбери:", reply_markup=markup)

@bot.message_handler(func=lambda message: "Назад" in message.text)
def back(message):
    bot.send_message(message.chat.id, "Главное меню 👇", reply_markup=menu())

print("Запущен")
bot.polling(none_stop=True)