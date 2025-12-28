import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import urllib.parse
from deep_translator import GoogleTranslator

# --- НАСТРОЙКИ ---
API_TOKEN = '8532165561:AAEkxuEkDPmRkTIUA_lSihTP9uCg1NTVYBY'
JACKETT_API_KEY = '1g427zkpafg0e1gku58k63wf5rgavoce'
JACKETT_URL = 'http://127.0.0.1:9117/api/v2.0/indexers/all/results'

# Ссылка на твой Mini App (замени после деплоя на GitHub Pages или Vercel)
MINI_APP_BASE_URL = 'https://your-username.github.io/movie-app/'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("🍿 Привет! Напиши название фильма, и я найду его для просмотра в Mini App.")


@dp.message_handler()
async def search_movie(message: types.Message):
    await message.answer(f"🔍 Ищу '{message.text}' на всех языках...")

    # 1. Готовим список запросов (оригинал + перевод)
    queries = [message.text]
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(message.text)
        if translated.lower() != message.text.lower():
            queries.append(translated)
    except:
        pass

    all_results = []

    # 2. Опрашиваем Jackett для каждого варианта названия
    for q in queries:
        print(f"Запрос к Jackett: {q}")
        query_encoded = urllib.parse.quote(q)
        url = f"{JACKETT_URL}?apikey={JACKETT_API_KEY}&Query={query_encoded}&Category[]=2000"

        try:
            response = requests.get(url, timeout=15).json()
            batch = response.get('Results', [])
            all_results.extend(batch)
        except Exception as e:
            print(f"Ошибка при поиске '{q}': {e}")

    # 3. Фильтруем магниты из общего списка
    magnet_results = []
    for r in all_results:
        magnet = r.get('MagnetUri')
        link = r.get('Link', '')
        if not magnet and link and link.startswith('magnet:'):
            magnet = link

        if magnet:
            r['FinalMagnet'] = magnet
            magnet_results.append(r)

    print(f"Всего ответов: {len(all_results)} | Найдено магнитов: {len(magnet_results)}")

    if not magnet_results:
        await message.answer("❌ Магниты не найдены. Попробуй другое название.")
        return

    # 4. Убираем дубликаты (если один и тот же торрент нашелся дважды) и берем топ по сидам
    best_match = max(magnet_results, key=lambda x: x.get('Seeders', 0))

    title = best_match.get('Title')
    magnet = best_match.get('FinalMagnet')
    seeders = best_match.get('Seeders')
    size_gb = round(best_match.get('Size', 0) / (1024 ** 3), 2)

    # 5. Ссылка для Mini App
    encoded_magnet_param = urllib.parse.quote(magnet)
    web_app_url = f"{MINI_APP_BASE_URL}?magnet={encoded_magnet_param}"

    keyboard = InlineKeyboardMarkup()
    btn = InlineKeyboardButton(text="🎥 СМОТРЕТЬ В MINI APP", web_app=WebAppInfo(url=web_app_url))
    keyboard.add(btn)

    await message.answer(
        f"✅ **Нашел!**\n\n🎬 `{title}`\n📦 {size_gb} ГБ | 👥 Сиды: {seeders}\n\n"
        "Нажми на кнопку для запуска:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

if __name__ == '__main__':
    print("Бот запущен и готов искать магниты...")
    executor.start_polling(dp, skip_updates=True)