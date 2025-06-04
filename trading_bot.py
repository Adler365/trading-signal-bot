import os
import telegram

print("🛠️ Starting verification...")

# 1. Get credentials with validation
TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()  # Remove any whitespace
CHAT_ID = os.getenv("CHAT_ID", "").strip()

if not TOKEN or ":" not in TOKEN:
    print("❌ CRITICAL ERROR: Invalid token format!")
    print("Token must be from @BotFather and contain ':'")
    print(f"Current token: '{TOKEN}'")
    print("👉 SOLUTION: Create NEW bot with /newbot")
    exit(1)

if not CHAT_ID or not CHAT_ID.isdigit():
    print("❌ CRITICAL ERROR: Invalid CHAT_ID!")
    print("Must be numeric (get from @userinfobot via /start)")
    print(f"Current CHAT_ID: '{CHAT_ID}'")
    exit(1)

# 2. Initialize bot
try:
    print(f"🔑 Attempting connection with token: {TOKEN[:5]}...{TOKEN[-5:]}")
    bot = telegram.Bot(token=TOKEN)
    print(f"✅ Connected to bot: @{bot.get_me().username}")
    
    # 3. Send test message
    bot.send_message(
        chat_id=int(CHAT_ID),
        text="🎉 *SUCCESS!* Bot is connected!\n\nNext: Add trading logic.",
        parse_mode='Markdown'
    )
    print(f"📩 Sent message to chat ID: {CHAT_ID}")
    
except Exception as e:
    print(f"❌ FATAL ERROR: {str(e)}")
    print("Possible fixes:")
    print("1. Token MUST be from FRESH /newbot")
    print("2. Secrets must EXACTLY match: TELEGRAM_TOKEN and CHAT_ID")
    print("3. No trailing spaces in secrets")
    exit(1)
