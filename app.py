import os
import re
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from huggingface_hub import InferenceClient

# 1. Configuration for Render & Neon
HF_TOKEN = os.getenv('HF_TOKEN')
API_TOKEN = os.getenv('TG_BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
WEBHOOK_HOST = os.getenv('RENDER_EXTERNAL_URL')
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

client = InferenceClient("Qwen/Qwen3.5-2B", token=HF_TOKEN, provider='featherless-ai')

# 2. PostgreSQL Database init
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_log (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            username TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    await conn.close()

# 3. Bot Logic
from aiogram.client.default import DefaultBotProperties
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
user_histories = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_histories[message.from_user.id] = [{"role": "system", "content": "You are a helpful assistant. Use the provided context to answer questions about Binance accurately. Use only HTML tags for formatting if needed (<b>bold</b>, <i>italic</i>)."}]
    await message.answer("Hello! I am support bot based on Qwen 3.5 via Hugging Face API and deployed on Render. You can ask me anything about Binance crypto serviсes. How can I help you? \n<i>Please note that due to Render limitations, the bot start can take up to 30 seconds.</i>")

@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    context = ""

    # RAG with PostgreSQL
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        search_term = f"%{text[:50]}%"
        row = await conn.fetchrow("SELECT answer FROM binance_faq WHERE question ILIKE $1 OR answer ILIKE $1 LIMIT 1", search_term)
        if row:
            context = f"Context from Binance FAQ: {row['answer']}\n"

        await conn.execute(
            "INSERT INTO chat_log (user_id, username, message) VALUES ($1, $2, $3)",
            user_id, message.from_user.username, text
        )
    finally:
        await conn.close()

    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": "You are a helpful assistant. Use the provided context to answer questions about Binance accurately. Use only HTML tags for formatting if needed (<b>bold</b>, <i>italic</i>)."}]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    augmented_content = f"{context}User: {text}"
    user_histories[user_id].append({"role": "user", "content": augmented_content})

    if len(user_histories[user_id]) > 9:
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-8:]

    try:
        response = client.chat_completion(
            messages=user_histories[user_id],
            max_tokens=512,
            temperature=0.7
        )

        response_text = response.choices[0].message.content
        formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response_text)
        user_histories[user_id].append({"role": "assistant", "content": response_text})

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Yes", callback_data="feedback_yes"))
        builder.row(types.InlineKeyboardButton(text="No, contact support", callback_data="feedback_no"))
        builder.row(types.InlineKeyboardButton(text="Another question", callback_data="feedback_another"))

        await message.answer(formatted_text)
        await message.answer("Was this answer helpful?", reply_markup=builder.as_markup())
    except Exception as e:
        await message.answer(f"API Error: {e}")

@dp.callback_query(F.data == "feedback_yes")
async def process_feedback_yes(callback: types.CallbackQuery):
    await callback.message.edit_text("Glad I could help!")
    await callback.answer()

@dp.callback_query(F.data == "feedback_no")
async def process_feedback_no(callback: types.CallbackQuery):
    await callback.message.answer("Your request is in progress, please wait")
    await callback.answer()

@dp.callback_query(F.data == "feedback_another")
async def process_feedback_another(callback: types.CallbackQuery):
    await callback.message.answer("Sure, what do you need help with?")
    await callback.answer()

async def on_startup(bot: Bot):
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)

def main():
    dp.startup.register(on_startup)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
