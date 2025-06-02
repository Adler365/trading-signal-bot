import os
import pandas as pd
import numpy as np
import yfinance as yf
from binance.spot import Spot
import requests
import telegram
from datetime import datetime, timedelta
import pytz

# ======================
# CUSTOMIZATION SECTION
# ======================

# 1. RISK PARAMETERS
SL_MULTIPLIER = 0.75    # Stop Loss: 0.75 x ATR 
TP1_MULTIPLIER = 1.5    # Take Profit 1: 1.5 x ATR
TP2_MULTIPLIER = 2.5    # Take Profit 2: 2.5 x ATR
RISK_PER_TRADE = 0.01   # Risk 1% of capital per trade

# 2. SYMBOL LISTS
STOCK_SYMBOLS = ['SPY', 'QQQ', 'TSLA', 'NVDA', 'GOLD']
CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT']
FOREX_PAIRS = ['EURUSD', 'USDJPY', 'GBPUSD', 'XAUUSD']
COMMODITIES = ['CL=F', 'GC=F', 'SI=F', 'NG=F']

# 3. SIGNAL SENSITIVITY
MIN_VOLUME_RATIO = 2.5      # 2.5x average volume required
MIN_PRICE_CHANGE = 0.003    # 0.3% price movement required
ATR_PERIOD = 14             # 14-period Average True Range

# PRO TIP: Market-specific settings
MARKET_SETTINGS = {
    'stocks': {'volume_ratio': 2.5, 'price_change': 0.003},
    'crypto': {'volume_ratio': 3.0, 'price_change': 0.005},
    'forex': {'volume_ratio': 2.0, 'price_change': 0.002},
    'commodities': {'volume_ratio': 3.0, 'price_change': 0.004}
}

# ======================
# CORE SYSTEM
# ======================

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']
bot = telegram.Bot(token=TELEGRAM_TOKEN)

def get_market_session():
    """Detect active trading sessions with overlap logic"""
    sessions = []
    utc_now = datetime.utcnow()
    utc_hour = utc_now.hour + utc_now.minute/60
    
    # Session times (UTC)
    asian = (0 <= utc_hour < 9)
    london = (8 <= utc_hour < 17)
    ny = (13 <= utc_hour < 22)
    
    if asian: sessions.append('Asian')
    if london: sessions.append('London')
    if ny: sessions.append('New York')
    
    # Detect overlaps
    overlaps = []
    if london and ny: overlaps.append('LON-NY Overlap')
    if asian and london: overlaps.append('ASIA-LON Overlap')
    
    return {'sessions': sessions, 'overlaps': overlaps}

def calculate_risk_levels(entry, direction, volatility):
    """Dynamic risk calculation with volatility scaling"""
    if direction == 'LONG':
        sl = entry * (1 - volatility * SL_MULTIPLIER)
        tp1 = entry * (1 + volatility * TP1_MULTIPLIER)
        tp2 = entry * (1 + volatility * TP2_MULTIPLIER)
    else:
        sl = entry * (1 + volatility * SL_MULTIPLIER)
        tp1 = entry * (1 - volatility * TP1_MULTIPLIER)
        tp2 = entry * (1 - volatility * TP2_MULTIPLIER)
        
    return {
        'sl': round(sl, 4),
        'tp1': round(tp1, 4),
        'tp2': round(tp2, 4),
        'volatility_pct': round(volatility * 100, 2)
    }

def calculate_atr(data):
    """Enhanced ATR calculation with error handling"""
    try:
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return true_range.rolling(ATR_PERIOD).mean().iloc[-1]
    except:
        return np.nan

def scan_asset(symbol, asset_type):
    """Unified scanning function for all asset types"""
    try:
        # PRO TIP: Market-specific sensitivity
        settings = MARKET_SETTINGS.get(asset_type.lower(), {})
        min_volume = settings.get('volume_ratio', MIN_VOLUME_RATIO)
        min_change = settings.get('price_change', MIN_PRICE_CHANGE)
        
        if asset_type == 'Crypto':
            client = Spot()
            klines = client.klines(symbol, '5m', limit=20)
            
            if len(klines) < 20: return None
            
            # Process crypto data
            closes = [float(k[4]) for k in klines]
            opens = [float(k[1]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            
            current_price = closes[-1]
            price_change = (closes[-1] - opens[-1]) / opens[-1]
            avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
            current_volume = volumes[-1]
            
        else:  # Stocks/Forex/Commodities
            if asset_type == 'Forex':
                symbol += "=X"  # Yahoo Finance format
            
            data = yf.download(symbol, period='1d', interval='5m', progress=False)
            if len(data) < 15: return None
            
            current_price = data['Close'].iloc[-1]
            price_change = (data['Close'].iloc[-1] - data['Open'].iloc[-1]) / data['Open'].iloc[-1]
            avg_volume = data['Volume'].iloc[:-1].mean()
            current_volume = data['Volume'].iloc[-1]
            highs = data['High']
            lows = data['Low']
            closes = data['Close']
        
        # Calculate volatility
        atr = calculate_atr(pd.DataFrame({
            'High': highs, 'Low': lows, 'Close': closes
        }))
        if pd.isna(atr) or atr == 0:
            return None
            
        volatility = atr / current_price
        
        # Volume analysis
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Signal detection
        if volume_ratio >= min_volume and abs(price_change) >= min_change:
            direction = 'LONG' if price_change > 0 else 'SHORT'
            risk = calculate_risk_levels(current_price, direction, volatility)
            
            return {
                'symbol': symbol.replace("=X", ""),
                'entry': round(current_price, 4),
                'direction': direction,
                'volume_ratio': round(volume_ratio, 2),
                'session': get_market_session(),
                'type': asset_type,
                'sl': risk['sl'],
                'tp1': risk['tp1'],
                'tp2': risk['tp2'],
                'volatility_pct': risk['volatility_pct'],
                'time': datetime.utcnow().strftime('%H:%M:%S UTC')
            }
            
    except Exception as e:
        print(f"Error scanning {symbol}: {str(e)}")
    return None

def generate_signals():
    """Generate signals with rate limiting"""
    signals = []
    
    # Scan all markets
    for symbol in STOCK_SYMBOLS:
        if signal := scan_asset(symbol, 'Stock'):
            signals.append(signal)
    
    for symbol in CRYPTO_SYMBOLS:
        if signal := scan_asset(symbol, 'Crypto'):
            signals.append(signal)
    
    for symbol in FOREX_PAIRS:
        if signal := scan_asset(symbol, 'Forex'):
            signals.append(signal)
    
    for symbol in COMMODITIES:
        if signal := scan_asset(symbol, 'Commodity'):
            signals.append(signal)
    
    # Sort by signal strength
    signals.sort(key=lambda x: x['volume_ratio'], reverse=True)
    return signals[:5]  # Max 5 signals per run

def send_telegram_signals(signals):
    """Professional Telegram formatting"""
    for signal in signals:
        emoji = "🔼" if signal['direction'] == 'LONG' else "🔽"
        
        message = (
            f"🚀 *TRADE SIGNAL* {emoji}\n"
            f"```\n"
            f"Type: {signal['type']}\n"
            f"Asset: {signal['symbol']}\n"
            f"Direction: {signal['direction']}\n"
            f"Entry: {signal['entry']}\n"
            f"Volatility: {signal['volatility_pct']}%\n"
            f"Volume Spike: {signal['volume_ratio']}x\n"
            f"Session: {', '.join(signal['session']['sessions']}\n"
            f"Time: {signal['time']}\n"
            f"```\n"
            f"*RISK MANAGEMENT*\n"
            f"```\n"
            f"┌────────────────┬──────────────┐\n"
            f"│ Stop Loss      │ {signal['sl']:>12} │\n"
            f"├────────────────┼──────────────┤\n"
            f"│ Take Profit 1  │ {signal['tp1']:>12} │\n"
            f"├────────────────┼──────────────┤\n"
            f"│ Take Profit 2  │ {signal['tp2']:>12} │\n"
            f"└────────────────┴──────────────┘\n"
            f"```"
        )
        
        try:
            bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            print(f"Telegram send error: {str(e)}")

if __name__ == "__main__":
    signals = generate_signals()
    if signals:
        send_telegram_signals(signals)
    else:
        print(f"{datetime.utcnow().isoformat()} - No signals found")
