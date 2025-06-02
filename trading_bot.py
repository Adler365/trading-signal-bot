import os
import pandas as pd
import numpy as np
import yfinance as yf
from binance.spot import Spot
import requests
import telegram
from datetime import datetime, timedelta
import pytz

# Configuration
STOCK_SYMBOLS = ['SPY', 'QQQ', 'TSLA', 'NVDA', 'GOLD']
CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT']
FOREX_PAIRS = ['EURUSD', 'USDJPY', 'GBPUSD', 'XAUUSD']
COMMODITIES = ['CL=F', 'GC=F', 'SI=F', 'NG=F']

# Telegram setup
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Risk parameters
SL_MULTIPLIER = 0.75
TP1_MULTIPLIER = 1.5
TP2_MULTIPLIER = 2.5

def get_market_session():
    """Detect active trading sessions"""
    sessions = []
    utc_hour = datetime.utcnow().hour
    
    # Asian session (00:00-09:00 UTC)
    if 0 <= utc_hour < 9:
        sessions.append('Asian')
    
    # London session (08:00-17:00 UTC)
    if 8 <= utc_hour < 17:
        sessions.append('London')
    
    # New York session (13:00-22:00 UTC)
    if 13 <= utc_hour < 22:
        sessions.append('New York')
    
    return sessions

def calculate_risk_levels(entry, direction, volatility):
    """Calculate TP/SL based on volatility"""
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
        'volatility': round(volatility * 100, 2)  # as percentage
    }

def calculate_atr(data):
    """Calculate Average True Range (ATR)"""
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    # Calculate TR components
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    # True Range is max of the three
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR (14-period)
    return tr.rolling(14).mean().iloc[-1]

def scan_yfinance(symbol, asset_type):
    """Scan stocks, commodities, or forex using yfinance"""
    try:
        # Fetch data
        data = yf.download(symbol, period='1d', interval='5m', progress=False)
        if len(data) < 15: 
            return None
            
        # Calculate volatility (ATR)
        atr = calculate_atr(data)
        volatility = atr / data['Close'].iloc[-1]
        
        # Volume spike detection
        avg_volume = data['Volume'].iloc[:-1].mean()
        current_volume = data['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Price movement
        price_change = (data['Close'].iloc[-1] - data['Open'].iloc[-1]) / data['Open'].iloc[-1]
        
        if volume_ratio > 2.5 and abs(price_change) > 0.003:
            direction = 'LONG' if price_change > 0 else 'SHORT'
            entry = round(data['Close'].iloc[-1], 4)
            
            # Calculate risk levels
            risk = calculate_risk_levels(entry, direction, volatility)
            
            return {
                'symbol': symbol,
                'entry': entry,
                'direction': direction,
                'volume_ratio': round(volume_ratio, 2),
                'session': get_market_session(),
                'type': asset_type,
                'sl': risk['sl'],
                'tp1': risk['tp1'],
                'tp2': risk['tp2'],
                'volatility': risk['volatility']
            }
    except Exception as e:
        print(f"Error scanning {symbol}: {str(e)}")
        return None

def scan_crypto(symbol):
    """Scan cryptocurrency for signals"""
    try:
        client = Spot()
        klines = client.klines(symbol, '5m', limit=20)
        
        if len(klines) < 20:
            return None
            
        # Extract data
        opens = [float(k[1]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        closes = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        
        # Calculate volatility (ATR)
        true_ranges = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            true_ranges.append(max(hl, hc, lc))
        
        atr = sum(true_ranges[-14:]) / 14
        volatility = atr / closes[-1]
        
        # Volume spike detection
        avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Price change
        price_change = (closes[-1] - opens[-1]) / opens[-1]
        
        if volume_ratio > 2.5 and abs(price_change) > 0.003:
            direction = 'LONG' if price_change > 0 else 'SHORT'
            entry = round(closes[-1], 4)
            
            # Calculate risk levels
            risk = calculate_risk_levels(entry, direction, volatility)
            
            return {
                'symbol': symbol,
                'entry': entry,
                'direction': direction,
                'volume_ratio': round(volume_ratio, 2),
                'session': get_market_session(),
                'type': 'Crypto',
                'sl': risk['sl'],
                'tp1': risk['tp1'],
                'tp2': risk['tp2'],
                'volatility': risk['volatility']
            }
    except Exception as e:
        print(f"Error scanning {symbol}: {str(e)}")
        return None

def generate_signals():
    """Generate trading signals"""
    signals = []
    
    # Scan all markets
    for symbol in STOCK_SYMBOLS:
        if signal := scan_yfinance(symbol, 'Stock'):
            signals.append(signal)
    
    for symbol in CRYPTO_SYMBOLS:
        if signal := scan_crypto(symbol):
            signals.append(signal)
    
    for symbol in FOREX_PAIRS:
        if signal := scan_yfinance(symbol + "=X", 'Forex'):
            signals.append(signal)
    
    for symbol in COMMODITIES:
        if signal := scan_yfinance(symbol, 'Commodity'):
            signals.append(signal)
    
    # Sort by strongest signal
    signals.sort(key=lambda x: x['volume_ratio'], reverse=True)
    return signals[:1]  # Return top 1 signal per run

def send_telegram_signals(signals):
    """Send formatted signals with TP/SL to Telegram"""
    for signal in signals:
        # Format direction emoji
        direction_emoji = "🔼" if signal['direction'] == 'LONG' else "🔽"
        
        # Create risk management table
        risk_table = (
            f"┌────────────────┬──────────────┐\n"
            f"│ Stop Loss      │ {signal['sl']:>12} │\n"
            f"├────────────────┼──────────────┤\n"
            f"│ Take Profit 1  │ {signal['tp1']:>12} │\n"
            f"├────────────────┼──────────────┤\n"
            f"│ Take Profit 2  │ {signal['tp2']:>12} │\n"
            f"└────────────────┴──────────────┘"
        )
        
        message = (
            f"🚀 *TRADE SIGNAL* {direction_emoji}\n"
            f"```\n"
            f"Type: {signal['type']}\n"
            f"Asset: {signal['symbol']}\n"
            f"Direction: {signal['direction']}\n"
            f"Entry: {signal['entry']}\n"
            f"Volatility: {signal['volatility']}%\n"
            f"Volume Spike: {signal.get('volume_ratio', 'N/A')}x\n"
            f"Session: {', '.join(signal['session'])}\n"
            f"Time: {datetime.utcnow().strftime('%H:%M:%S')} UTC\n"
            f"```\n"
            f"*RISK MANAGEMENT*\n"
            f"```\n"
            f"{risk_table}\n"
            f"```"
        )
        
        bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode='MarkdownV2'
        )

if __name__ == "__main__":
    signals = generate_signals()
    if signals:
        send_telegram_signals(signals)
    else:
        print("No signals found")
