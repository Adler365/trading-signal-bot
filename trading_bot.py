import os
import pandas as pd
import numpy as np
import yfinance as yf
from binance.spot import Spot
import requests
import telegram
from datetime import datetime
import pytz

# ===== CONFIGURATION =====
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

# Risk Management
SL_MULTIPLIER = 0.75
TP1_MULTIPLIER = 1.5
TP2_MULTIPLIER = 2.5

# Assets
STOCKS = ['SPY', 'QQQ']
CRYPTO = ['BTCUSDT', 'ETHUSDT']
FOREX = ['EURUSD', 'USDJPY']

# Sensitivity
MIN_VOLUME_RATIO = 2.5
MIN_PRICE_CHANGE = 0.003

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def get_sessions():
    utc_hour = datetime.utcnow().hour
    sessions = []
    if 0 <= utc_hour < 9: sessions.append('Asian')
    if 8 <= utc_hour < 17: sessions.append('London')
    if 13 <= utc_hour < 22: sessions.append('New York')
    return sessions

def calculate_atr(data):
    high = data['High']
    low = data['Low']
    close = data['Close']
    tr = pd.concat([high-low, 
                   abs(high-close.shift()), 
                   abs(low-close.shift())], axis=1).max(axis=1)
    return tr.rolling(14).mean().iloc[-1]

def scan_market(symbol, asset_type):
    try:
        if asset_type == 'crypto':
            client = Spot()
            klines = client.klines(symbol, '5m', limit=20)
            if len(klines) < 20: return None
            
            closes = [float(k[4]) for k in klines]
            entry = closes[-1]
            change = (closes[-1] - closes[-2]) / closes[-2]
            volumes = [float(k[5]) for k in klines]
            vol_ratio = volumes[-1] / np.mean(volumes[:-1])
            
            # Simplified ATR calculation
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            atr = calculate_atr(pd.DataFrame({'High': highs, 'Low': lows, 'Close': closes}))
            
        else:  # stocks/forex
            if asset_type == 'forex': symbol += "=X"
            data = yf.download(symbol, period='1d', interval='5m', progress=False)
            if len(data) < 15: return None
            
            entry = data['Close'].iloc[-1]
            change = (data['Close'].iloc[-1] - data['Open'].iloc[-1]) / data['Open'].iloc[-1]
            vol_ratio = data['Volume'].iloc[-1] / data['Volume'].iloc[:-1].mean()
            atr = calculate_atr(data)
        
        if vol_ratio >= MIN_VOLUME_RATIO and abs(change) >= MIN_PRICE_CHANGE:
            direction = 'LONG' if change > 0 else 'SHORT'
            volatility = atr / entry
            
            # Calculate TP/SL
            if direction == 'LONG':
                sl = entry * (1 - volatility * SL_MULTIPLIER)
                tp1 = entry * (1 + volatility * TP1_MULTIPLIER)
                tp2 = entry * (1 + volatility * TP2_MULTIPLIER)
            else:
                sl = entry * (1 + volatility * SL_MULTIPLIER)
                tp1 = entry * (1 - volatility * TP1_MULTIPLIER)
                tp2 = entry * (1 - volatility * TP2_MULTIPLIER)
                
            return {
                'symbol': symbol.replace("=X", ""),
                'entry': round(entry, 4),
                'direction': direction,
                'sl': round(sl, 4),
                'tp1': round(tp1, 4),
                'tp2': round(tp2, 4),
                'session': get_sessions()
            }
            
    except Exception as e:
        print(f"Error scanning {symbol}: {str(e)}")
    return None

def generate_signals():
    signals = []
    for symbol in STOCKS:
        if signal := scan_market(symbol, 'stock'):
            signals.append(signal)
    for symbol in CRYPTO:
        if signal := scan_market(symbol, 'crypto'):
            signals.append(signal)
    for symbol in FOREX:
        if signal := scan_market(symbol, 'forex'):
            signals.append(signal)
    return signals[:5]  # Limit to 5 signals

def send_signals(signals):
    for signal in signals:
        msg = f"""🚀 *TRADE SIGNAL* {'🔼' if signal['direction'] == 'LONG' else '🔽'}
