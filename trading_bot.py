import os
import telegram

# 1. Get credentials
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 2. Verify token exists
if not TOKEN or ":" not in TOKEN:
    raise ValueError("Invalid token format. Get new one from @BotFather")

# 3. Initialize bot
try:
    bot = telegram.Bot(token=TOKEN)
    bot.send_message(
        chat_id=CHAT_ID,
        text="✅ *Bot is working!* \nNow we can add trading logic.",
        parse_mode='Markdown'
    )
    print("Success! Check Telegram.")
except Exception as e:
    print(f"Error: {str(e)}")
    print("Fix: 1) Create NEW bot 2) Update secrets 3) Check CHAT_ID")
