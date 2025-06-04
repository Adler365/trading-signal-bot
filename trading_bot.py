import os
import sys

print("🔍 Starting verification...")

# Get and validate token
TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
if not TOKEN or ":" not in TOKEN:
    print("""
❌ CRITICAL ERROR: Invalid token!
-------------------------------------
1. MUST create NEW bot with @BotFather:
   - Message @BotFather
   - Send /newbot
   - Follow ALL prompts
   - COPY the token

2. MUST add to GitHub Secrets:
   - Settings → Secrets → Actions
   - Name: TELEGRAM_TOKEN
   - Value: Your new token
-------------------------------------
Current token: '{}'
""".format(TOKEN))
    sys.exit(1)

# Verify connection
try:
    from telegram import Bot
    bot = Bot(token=TOKEN)
    print(f"✅ Valid token! Bot username: @{bot.get_me().username}")
except Exception as e:
    print(f"""
❌ Connection failed: {e}
-------------------------------------
Possible fixes:
1. Token MUST be from FRESH /newbot
2. No trailing spaces in secret
3. Secret name EXACTLY: TELEGRAM_TOKEN
""")
    sys.exit(1)
