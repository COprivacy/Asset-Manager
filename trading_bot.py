import sys
import time
import json
import getpass
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# Try to import pandas_ta, else use manual calculation
try:
    import pandas_ta as ta
    HAS_TA = True
except ImportError:
    HAS_TA = False
    print("Aviso: pandas_ta não encontrado. Usando cálculos manuais.")

# Try to import IQ Option API
try:
    from iqoptionapi.stable_api import IQ_Option
except ImportError:
    print("Erro crítico: Biblioteca 'iqoptionapi' não encontrada.")
    print("Tentando instalar versão community...")
    import subprocess
    try:
        # Try installing dependencies first
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client==0.56.0"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/iqoptionapi/iqoptionapi.git", "--upgrade"])
        from iqoptionapi.stable_api import IQ_Option
    except Exception as e:
        print(f"Falha ao instalar iqoptionapi: {e}")
        # Mock for testing if install fails
        class MockIQ:
            def __init__(self, e, p): pass
            def connect(self): return True, None
            def change_balance(self, b): pass
            def get_balance(self): return 10000
            def get_all_open_time(self): return {'turbo': {'EURUSD': {'open': True}}}
            def get_candles(self, a, t, c, x): 
                # Generate fake candles for testing
                return [{'close': 1.1000 + (i*0.0001), 'open': 1.1000} for i in range(100)]
        IQ_Option = MockIQ
        print("Usando Mock IQ Option para demonstração (instalação falhou).")

# API Endpoint for Dashboard Integration
API_URL = "http://localhost:5000/api/signals"

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_sma(series, period):
    return series.rolling(window=period).mean()

def print_banner():
    print("\n" + "="*60)
    print("APENAS PARA ESTUDOS E TESTES EM CONTA DEMO!".center(60))
    print("TRADING ENVOLVE RISCO TOTAL DE PERDA DE CAPITAL.".center(60))
    print("NÃO USE DINHEIRO REAL SEM TESTAR MUITO!".center(60))
    print("="*60 + "\n")

def connect_iq():
    print("Login na IQ Option:")
    email = input("Email: ")
    password = getpass.getpass("Senha: ")
    
    try:
        Iq = IQ_Option(email, password)
        check, reason = Iq.connect()
        
        if check:
            print(f"\nConectado com sucesso!")
            Iq.change_balance("PRACTICE")
            print(f"Saldo DEMO: {Iq.get_balance()}")
            return Iq
        else:
            print(f"\nErro ao conectar: {reason}")
            sys.exit(1)
    except Exception as e:
        print(f"Erro na conexão: {e}")
        sys.exit(1)

def get_open_assets(Iq):
    print("Buscando ativos abertos...")
    try:
        all_assets = Iq.get_all_open_time()
        open_assets = []
        
        # Filter for 'turbo' (binary) or 'digital'
        for type_name in ['turbo', 'binary']:
            if type_name in all_assets:
                for asset_name, data in all_assets[type_name].items():
                    if data['open']:
                        open_assets.append(asset_name)
                        
        return list(set(open_assets))
    except:
        return ['EURUSD', 'GBPUSD', 'USDJPY'] # Fallback

def analyze_asset(Iq, asset, timeframe=60):
    try:
        # Get candles
        candles = Iq.get_candles(asset, timeframe, 100, time.time())
        if not candles:
            return None
            
        df = pd.DataFrame(candles)
        df['close'] = df['close'].astype(float)
        
        # Strategies
        current_rsi = 50
        sma9_curr = 0
        sma21_curr = 0
        
        if HAS_TA:
            rsi = ta.rsi(df['close'], length=14)
            current_rsi = rsi.iloc[-1]
            sma9 = ta.sma(df['close'], length=9)
            sma21 = ta.sma(df['close'], length=21)
            sma9_curr = sma9.iloc[-1]
            sma21_curr = sma21.iloc[-1]
            sma9_prev = sma9.iloc[-2]
            sma21_prev = sma21.iloc[-2]
        else:
            rsi = calculate_rsi(df['close'], 14)
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50
            sma9 = calculate_sma(df['close'], 9)
            sma21 = calculate_sma(df['close'], 21)
            sma9_curr = sma9.iloc[-1] if not sma9.empty else 0
            sma21_curr = sma21.iloc[-1] if not sma21.empty else 0
            sma9_prev = sma9.iloc[-2] if len(sma9) > 1 else 0
            sma21_prev = sma21.iloc[-2] if len(sma21) > 1 else 0

        signal = None
        strategy_name = ""
        confidence = 0
        
        # Logic
        if current_rsi < 30:
            signal = "CALL"
            strategy_name = "RSI Oversold"
            confidence = 70
        elif current_rsi > 70:
            signal = "PUT"
            strategy_name = "RSI Overbought"
            confidence = 70
            
        # SMA Crossover
        if sma9_curr > sma21_curr and sma9_prev <= sma21_prev:
            if signal == "CALL":
                signal = "CALL"
                strategy_name = "RSI + SMA Cross"
                confidence = 85
            else:
                signal = "CALL"
                strategy_name = "SMA Cross"
                confidence = 65
        elif sma9_curr < sma21_curr and sma9_prev >= sma21_prev:
            if signal == "PUT":
                signal = "PUT"
                strategy_name = "RSI + SMA Cross"
                confidence = 85
            else:
                signal = "PUT"
                strategy_name = "SMA Cross"
                confidence = 65
                
        if signal and confidence >= 65:
            return {
                "asset": asset,
                "action": signal,
                "strategy": strategy_name,
                "confidence": confidence,
                "price": str(df['close'].iloc[-1])
            }
            
    except Exception as e:
        print(f"Erro ao analisar {asset}: {e}")
        
    return None

def post_signal(signal_data):
    try:
        requests.post(API_URL, json=signal_data)
    except:
        pass # Ignore API errors

def main_loop(Iq, assets):
    print("\nIniciando análise em tempo real...")
    print("Pressione Ctrl+C para parar.")
    
    while True:
        for asset in assets:
            print(f"Analisando {asset}...", end='\r')
            signal = analyze_asset(Iq, asset)
            
            if signal:
                print(f"\nSINAL ENCONTRADO: {signal['asset']} | {signal['action']} | {signal['strategy']} ({signal['confidence']}%)")
                post_signal(signal)
                
        time.sleep(60)

def interactive_menu(Iq):
    while True:
        print("\n--- MENU ---")
        print("1. Listar e escolher ativos")
        print("2. Iniciar scan em tempo real (EURUSD, GBPUSD...)")
        print("0. Sair")
        
        choice = input("Opção: ")
        
        if choice == "1":
            assets = get_open_assets(Iq)
            print(f"Ativos disponíveis: {', '.join(assets[:10])}...")
            selected = input("Digite ativos separados por vírgula (ex: EURUSD,GBPUSD) ou ENTER para top 5: ")
            if not selected:
                selected_assets = assets[:5]
            else:
                selected_assets = [a.strip().upper() for a in selected.split(',')]
            
            print(f"Ativos selecionados: {selected_assets}")
            main_loop(Iq, selected_assets)
            
        elif choice == "2":
            assets = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD']
            main_loop(Iq, assets)
            
        elif choice == "0":
            break

if __name__ == "__main__":
    print_banner()
    try:
        iq_session = connect_iq()
        interactive_menu(iq_session)
    except KeyboardInterrupt:
        print("\nEncerrando...")
    except Exception as e:
        print(f"\nErro fatal: {e}")
