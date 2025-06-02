import os
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import telegram
from datetime import datetime

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Trading parameters
PARAMS = {
    'stocks': ['SPY', 'QQQ'],
    'crypto': ['BTC-USD', 'ETH-USD'],  # Using yfinance format
    'min_volume_ratio': 2.0,
    'min_price_change': 0.002,
    'sl_multiplier': 0.75,
    'tp_multiplier': 1.5
}

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def get_market_session():
    """Determine current market session"""
    hour = datetime.utcnow().hour
    if 0 <= hour < 9: return 'Asian'
    if 8 <= hour < 17: return 'London'
    if 13 <= hour < 22: return 'New York'
    return 'After Hours'

def calculate_volatility(data):
    """Simplified volatility calculation"""
    highs = data['High']
    lows = data['Low']
    closes = data['Close']
    tr = pd.concat([highs-lows, 
                   abs(highs-closes.shift()), 
                   abs(lows-closes.shift())], axis=1).max(axis=1)
    return tr.rolling(14).mean().iloc[-1] / closes.iloc[-1]

def scan_market(symbol):
    """Scan a single market for opportunities"""
    try:
        data = yf.download(symbol, period='1d', interval='5m', progress=False)
        if len(data) < 15: return None
        
        # Calculate metrics
        current = data.iloc[-1]
        prev_avg_volume = data['Volume'].iloc[:-1].mean()
        vol_ratio = current['Volume'] / prev_avg_volume
        price_change = (current['Close'] - current['Open']) / current['Open']
        
        if vol_ratio >= PARAMS['min_volume_ratio'] and abs(price_change) >= PARAMS['min_price_change']:
            direction = 'LONG' if price_change > 0 else 'SHORT'
            volatility = calculate_volatility(data)
            entry = round(current['Close'], 4)
            
            # Calculate risk levels
            if direction == 'LONG':
                sl = entry * (1 - volatility * PARAMS['sl_multiplier'])
                tp = entry * (1 + volatility * PARAMS['tp_multiplier'])
            else:
                sl = entry * (1 + volatility * PARAMS['sl_multiplier'])
                tp = entry * (1 - volatility * PARAMS['tp_multiplier'])
            
            return {
                'symbol': symbol,
                'entry': entry,
                'direction': direction,
                'sl': round(sl, 4),
                'tp': round(tp, 4),
                'session': get_market_session()
            }
    except Exception as e:
        print(f"Error scanning {symbol}: {str(e)}")
    return None

def generate_signals():
    """Generate trading signals for all markets"""
    signals = []
    for symbol in PARAMS['stocks'] + PARAMS['crypto']:
        if signal := scan_market(symbol):
            signals.append(signal)
    return signals[:3]  # Return max 3 best signals

def send_signals(signals):
    """Send signals to Telegram"""
    for signal in signals:
        msg = f"""📈 *Trade Signal* {'🔼' if signal['direction'] == 'LONG' else '🔽'}
