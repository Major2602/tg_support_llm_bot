# General
Support Telegram LLM Bot that uses Binance FAQ to answer user questions. The bot is available on https://t.me/test348527_bot.
### Model & Provider:
Qwen3.5-2B via Hugging Face Hub Inference Provider API.
### Backend
Render Cloud Hosting (connects with Telegram via webhook).
### Database
Neon PostgreSQL Database.
### FAQ Knowledge Base
Created from official Binance FAQ section with ChatGPT.
### Workflow:
1) Sends Hello message to user, describing functionality.
2) After receiving user's message bot is searching through its knowledgebase (PostgreSQL table) for answer (RAG implementation).
3) Bot automatically writes down user's message in PostreSQL database.
4) After each reply the user is suggested to estimate it with 3 buttons: "Yes", "No, contact support" and "Another question", with respective bot replies.
