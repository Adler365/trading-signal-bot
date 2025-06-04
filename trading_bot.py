import os
import sys
from telegram import Bot, TelegramError

print("🔍 Starting verification...")

TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

if not TOKEN or ":" not in TOKEN:
    print("\n❌ ERROR: Invalid Telegram token!")
    print("Please:")
    print("1. Create NEW bot with @BotFather (/newbot)")
    print("2. Add token to GitHub Secrets as 'TELEGRAM_TOKEN'")
    print(f"Current token: '{TOKEN}'\n")
    sys.exit(1)

try:
    bot = Bot(token=TOKEN)
    print(f"✅ Connected to bot: @{bot.get_me().username}")
    
    bot.send_message(
        chat_id=CHAT_ID,
        text="🚀 Bot connection successful!",
        parse_mode='Markdown'
    )
    print("📩 Sent test message to Telegram")
    
except TelegramError as e:
    print(f"\n❌ Telegram error: {e}")
    print("Possible fixes:")
    print("1. Token must be from FRESH /newbot")
    print("2. CHAT_ID must be your numeric ID from @userinfobot")
    print("3. No trailing spaces in secrets\n")
    sys.exit(1)
