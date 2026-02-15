import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def run_test():
    # Mock data for 15/02/2026 ~1.365xx
    base_price = 1.36500
    data = {
        'open': [base_price + i*0.00001 for i in range(60)],
        'close': [base_price + (i+1)*0.00001 for i in range(60)],
        'high': [base_price + (i+1.5)*0.00001 for i in range(60)],
        'low': [base_price + (i-0.5)*0.00001 for i in range(60)],
        'volume': [100 + i for i in range(60)]
    }
    df = pd.DataFrame(data)
    
    # Calculate indicators
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    last_candle = df.iloc[-1]
    
    print("--- TEST RESULTS (15/02/2026 MOCK DATA) ---")
    print(f"Price: {last_candle['close']:.5f}")
    print(f"EMA20: {last_candle['ema20']:.5f}")
    print(f"EMA50: {last_candle['ema50']:.5f}")
    print(f"RSI: {last_candle['rsi']:.2f}")
    
    # Logic verification
    action = "CALL" # Supposed AI Decision
    confidence = 85
    
    if action == 'CALL':
        if not (last_candle['close'] > last_candle['ema20'] and last_candle['rsi'] < 70):
            confidence -= 20
            print("Action: CALL | Result: LOW CONFLUENCE (-20% Confidence)")
        else:
            print("Action: CALL | Result: HIGH CONFLUENCE")
            
    print(f"Final Confidence: {confidence}%")

if __name__ == "__main__":
    run_test()
