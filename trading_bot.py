import os
import telegram

# Get credentials from environment
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Initialize bot
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Send test message
bot.send_message(
    chat_id=CHAT_ID,
    text="🚀 Bot is working!",
    parse_mode='Markdown'
)

print("Success! Message sent.")
