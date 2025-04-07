
import logging
import asyncio
import os
import json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

google_creds_raw = os.getenv("GOOGLE_CREDENTIALS_JSON")
if google_creds_raw:
    with open("credentials.json", "w") as f:
        json.dump(json.loads(google_creds_raw), f)

# --- Google Sheets setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
sheet = client.open(SPREADSHEET_NAME).sheet1

# --- Telegram bot setup ---
TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

user_data = {}

start_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Пройти опрос")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    welcome_text = (
        "Привет! Я - Почелинцев Андрей 👋\n"
        "Тоже из бизнеса: команда, выручка, сложные решения. Всё как у тебя!\n\n"
        "23 апреля я выступаю на IT-конференции от RASA.\n Хочу, чтобы это был не доклад «про успех»,"
        "а разговор по делу — про то, **что болит** у предпринимателей сегодня.\n\n"
        "🔍 Я сделал этот бот, чтобы провести мини-аудит и понять:\n"
        "кто ты, что ты чувствуешь, где буксует твой бизнес и что можно изменить.\n\n"
        "5 вопросов. 15 секунд. Анонимно. По-честному.\n\n"
        "Готов? Жми «Пройти опрос» 👇"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=start_keyboard)

# Вопросы
@dp.message(F.text == "Пройти опрос")
async def q1(message: types.Message):
    user_data[message.from_user.id] = {}
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="до 25"), KeyboardButton(text="25-35")],
            [KeyboardButton(text="35-45"), KeyboardButton(text="45-55")],
            [KeyboardButton(text="старше 55")]
        ],
        resize_keyboard=True
    )
    await message.answer("1️⃣ Сколько тебе лет?", reply_markup=keyboard)

@dp.message(F.text.in_(["до 25", "25-35", "35-45", "45-55", "старше 55"]))
async def q2(message: types.Message):
    user_data[message.from_user.id]["age"] = message.text
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Торговля"), KeyboardButton(text="Промышленность/Производство")],
            [KeyboardButton(text="Строительство"), KeyboardButton(text="Услуги")],
            [KeyboardButton(text="Прочее")]
        ],
        resize_keyboard=True
    )
    await message.answer("2️⃣ В какой сфере твой бизнес?", reply_markup=keyboard)

@dp.message(F.text.in_(["Торговля", "Промышленность/Производство", "Строительство", "Услуги", "Прочее"]))
async def q3(message: types.Message):
    user_data[message.from_user.id]["industry"] = message.text
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="до 10"), KeyboardButton(text="11-30")],
            [KeyboardButton(text="31-100"), KeyboardButton(text="101 и более")]
        ],
        resize_keyboard=True
    )
    await message.answer("3️⃣ Количество человек в штате?", reply_markup=keyboard)

@dp.message(F.text.in_(["до 10", "11-30", "31-100", "101 и более"]))
async def q4(message: types.Message):
    user_data[message.from_user.id]["staff"] = message.text
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="до 1 млн"), KeyboardButton(text="1-10 млн")],
            [KeyboardButton(text="10-100 млн"), KeyboardButton(text="100-500 млн.")],
            [KeyboardButton(text="500-1.000 млн"), KeyboardButton(text="больше 1 млрд.")]
        ],
        resize_keyboard=True
    )
    await message.answer("4️⃣ Оборот бизнеса (выручка)?", reply_markup=keyboard)

@dp.message(F.text.in_(["до 1 млн", "1-10 млн", "10-100 млн", "100-500 млн.", "500-1.000 млн", "больше 1 млрд."]))
async def q5(message: types.Message):
    user_data[message.from_user.id]["revenue"] = message.text
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Кадры/HR"), KeyboardButton(text="Продажи")],
            [KeyboardButton(text="Финансы"), KeyboardButton(text="Управление")],
            [KeyboardButton(text="Гос.поддержка"), KeyboardButton(text="Автоматизация, ИИ")],
            [KeyboardButton(text="Личное развитие")],
            [KeyboardButton(text="✅ Завершить")]
        ],
        resize_keyboard=True
    )
    user_data[message.from_user.id]["pain"] = []
    await message.answer("5️⃣ Где болит или скоро начнёт болеть?\n\n(можно выбрать несколько, потом нажать «✅ Завершить»)", reply_markup=keyboard)

@dp.message(F.text.in_([
    "Кадры/HR", "Продажи", "Финансы", "Управление",
    "Гос.поддержка", "Автоматизация, ИИ", "Личное развитие"
]))
async def select_pain(message: types.Message):
    uid = message.from_user.id
    pain_list = user_data[uid]["pain"]
    if message.text not in pain_list:
        pain_list.append(message.text)
    await message.answer(f"✅ Добавлено: {message.text} (можно выбрать ещё, или нажми «✅ Завершить»)", reply_markup=message.reply_markup)

@dp.message(F.text == "✅ Завершить")
async def finish(message: types.Message):
    uid = message.from_user.id
    answers = user_data.get(uid, {})
    pain = ", ".join(answers.get("pain", []))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([
        str(uid),
        message.from_user.username or message.from_user.full_name,
        answers.get("age"),
        answers.get("industry"),
        answers.get("staff"),
        answers.get("revenue"),
        pain,
        now
    ])
    summary = (
    f"📋 *Результаты опроса:*\n\n"
    f"👤 Возраст: {answers.get('age')}\n"
    f"🏢 Сфера: {answers.get('industry')}\n"
    f"👥 Штат: {answers.get('staff')}\n"
    f"💰 Оборот: {answers.get('revenue')}\n"
    f"⚠️ Проблемные зоны: {pain}"
)

    await message.answer(summary, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "Спасибо! 🙌\n\nДо встречи 23 апреля.",
        parse_mode="Markdown"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
