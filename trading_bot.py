import os
import telegram

print("🛠️ Starting verification...")

# 1. Get token with validation
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN or ":" not in TOKEN:
    print("❌ INVALID TOKEN FORMAT!")
    print("Token must be from @BotFather and contain ':'")
    print(f"Current token: {TOKEN}")
    exit(1)

# 2. Initialize bot with error handling
try:
    print("🔑 Attempting connection...")
    bot = telegram.Bot(token=TOKEN)
    print("✅ Connection successful!")
    print(f"🤖 Bot username: {bot.get_me().username}")
except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")
    print("Possible fixes:")
    print("1. Token must be from NEW bot (use /newbot)")
    print("2. Secrets must be named EXACTLY: TELEGRAM_TOKEN")
    print("3. No spaces in token")
    exit(1)

# 3. Send test message
try:
    CHAT_ID = os.getenv("CHAT_ID")
    bot.send_message(
        chat_id=CHAT_ID,
        text="🎉 *CONNECTION WORKING!* \nNow we can add trading logic!",
        parse_mode='Markdown'
    )
    print("📩 Test message sent to Telegram!")
except Exception as e:
    print(f"❌ MESSAGE FAILED: {e}")
    print("Verify CHAT_ID secret exists")
