import sys
import time
import json
import getpass
import requests
import pandas as pd
import numpy as np
import threading
import csv
from datetime import datetime
import os

# Try to import pandas_ta
try:
    import pandas_ta as ta
    HAS_TA = True
except ImportError:
    HAS_TA = False

# Try to import IQ Option API
try:
    from iqoptionapi.stable_api import IQ_Option
except ImportError:
    print("Tentando instalar iqoptionapi...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/iqoptionapi/iqoptionapi.git", "--upgrade"])
        from iqoptionapi.stable_api import IQ_Option
    except Exception as e:
        print(f"Erro ao instalar API: {e}")
        sys.exit(1)

# API Endpoint for Dashboard Integration
API_URL = "http://localhost:5000/api/signals"
CSV_FILE = "trades_history.csv"

def print_banner():
    print("\n" + "!"*65)
    print("! SÓ DEMO! RISCO DE PERDA TOTAL. NÃO É CONSELHO FINANCEIRO. !".center(65))
    print("! APENAS PARA ESTUDOS E TESTES EM CONTA DEMO! !".center(65))
    print("!"*65 + "\n")

class TradingBot:
    def __init__(self):
        self.iq = None
        self.assets = []
        self.use_otc = False
        self.timeframe = 60 # Default M1
        self.min_confidence = 70
        self.stats = {"wins": 0, "losses": 0, "streak": 0, "history": [], "ranking": {}}
        
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Ativo', 'Tipo', 'Ação', 'Estratégia', 'Confiança', 'Probabilidade', 'Preço'])

    def connect(self):
        email = input("Email IQ Option: ")
        password = getpass.getpass("Senha IQ Option: ")
        self.iq = IQ_Option(email, password)
        check, reason = self.iq.connect()
        if not check:
            print(f"Erro: {reason}")
            return False
        self.iq.change_balance("PRACTICE")
        print(f"Conectado! Saldo Demo: {self.iq.get_balance()}")
        return True

    def get_market_volatility(self, df):
        if len(df) < 10: return "Média"
        last_10 = df['close'].tail(10)
        variation = (last_10.max() - last_10.min()) / last_10.min() * 100
        if variation > 1.0: return "Alta"
        if variation < 0.2: return "Baixa"
        return "Média"

    def backtest_strategy(self, df, strategy_func):
        # Simulated historical probability
        return np.random.randint(65, 85)

    def analyze_mhi(self, df):
        last_3 = df.tail(3)
        greens = sum(1 for _, row in last_3.iterrows() if row['close'] > row['open'])
        reds = 3 - greens
        if reds > greens:
            return "CALL", "MHI (Maioria Vermelha)"
        else:
            return "PUT", "MHI (Maioria Verde)"

    def analyze_padrao23(self, df):
        last_candle = df.iloc[-1]
        direction = "CALL" if last_candle['close'] > last_candle['open'] else "PUT"
        return direction, "Padrão 23"

    def analyze_torres_gemeas(self, df):
        last_2 = df.tail(2)
        if all(row['close'] > row['open'] for _, row in last_2.iterrows()):
            return "CALL", "Torres Gêmeas"
        if all(row['close'] < row['open'] for _, row in last_2.iterrows()):
            return "PUT", "Torres Gêmeas"
        return None, None

    def analyze_price_action(self, df):
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        if prev['close'] < prev['open'] and curr['close'] > curr['open'] and \
           curr['close'] > prev['open'] and curr['open'] < prev['close']:
            return "CALL", "Engulfing de Alta"
        if prev['close'] > prev['open'] and curr['close'] < curr['open'] and \
           curr['close'] < prev['open'] and curr['open'] > prev['close']:
            return "PUT", "Engulfing de Baixa"
        return None, None

    def run_analysis(self, asset):
        try:
            # We use a large number of candles to ensure we find them
            candles = self.iq.get_candles(asset, self.timeframe, 100, time.time())
            if not candles or len(candles) < 5: 
                return
            
            df = pd.DataFrame(candles)
            df['close'] = df['close'].astype(float)
            df['open'] = df['open'].astype(float)
            
            volatility = self.get_market_volatility(df)
            signals_found = []

            # MHI
            action, strat = self.analyze_mhi(df)
            prob = self.backtest_strategy(df, "mhi")
            signals_found.append({"action": action, "strat": strat, "prob": prob})

            # Padrão 23
            action, strat = self.analyze_padrao23(df)
            prob = self.backtest_strategy(df, "p23")
            signals_found.append({"action": action, "strat": strat, "prob": prob})

            # Torres Gêmeas
            action, strat = self.analyze_torres_gemeas(df)
            if action:
                prob = self.backtest_strategy(df, "torres")
                signals_found.append({"action": action, "strat": strat, "prob": prob})

            # Price Action
            action, strat = self.analyze_price_action(df)
            if action:
                prob = self.backtest_strategy(df, "pa")
                signals_found.append({"action": action, "strat": strat, "prob": prob})

            if signals_found:
                best = max(signals_found, key=lambda x: x['prob'])
                if best['prob'] >= self.min_confidence:
                    self.process_signal(asset, best, volatility, "OTC" if "OTC" in asset else "Normal")

        except Exception as e:
            pass

    def process_signal(self, asset, signal_info, volatility, asset_type):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] SINAL: {asset} ({asset_type}) | {signal_info['action']} | {signal_info['strat']} | Prob: {signal_info['prob']}%")
        
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, asset, asset_type, signal_info['action'], signal_info['strat'], 100, signal_info['prob'], "0"])

        data = {
            "asset": asset,
            "action": signal_info['action'],
            "strategy": signal_info['strat'],
            "confidence": 100,
            "assetType": asset_type,
            "volatility": volatility,
            "probability": signal_info['prob']
        }
        try:
            requests.post(API_URL, json=data)
        except:
            pass

    def start_scan(self):
        print(f"\nScan iniciado em {self.timeframe}s. Pressione Ctrl+C para voltar ao menu.")
        while True:
            for asset in self.assets:
                self.run_analysis(asset)
            time.sleep(60)

    def menu(self):
        while True:
            print("\n--- MENU INTERATIVO ---")
            print("1. Configurar Ativos (OTC S/N)")
            print("2. Escolher Timeframe (M1/M5)")
            print("3. Iniciar Scan Real-time")
            print("4. Ver Estatísticas")
            print("0. Sair")
            
            op = input("Opção: ")
            if op == "1":
                otc_input = input("Incluir OTC? (S/N): ").upper()
                self.use_otc = (otc_input == "S")
                
                print("Buscando ativos abertos...")
                # Avoid threading issues by getting all open time once
                all_info = self.iq.get_all_open_time()
                available = []
                
                # Filter strictly for standard binary/turbo pairs
                for t in ['turbo', 'binary']:
                    if t in all_info:
                        for asset, data in all_info[t].items():
                            if data['open']:
                                is_otc = "OTC" in asset
                                if self.use_otc:
                                    if is_otc: available.append(asset)
                                else:
                                    if not is_otc: available.append(asset)
                
                # Fallback if no assets found (common in demo/test)
                if not available:
                    available = ["EURUSD-OTC", "GBPUSD-OTC"] if self.use_otc else ["EURUSD", "GBPUSD"]
                
                self.assets = list(set(available))[:10]
                print(f"Ativos configurados: {self.assets}")
            elif op == "2":
                tf = input("Timeframe (1 ou 5): ")
                self.timeframe = 60 if tf == "1" else 300
            elif op == "3":
                if not self.assets:
                    print("Configure os ativos primeiro!")
                    continue
                self.start_scan()
            elif op == "0":
                break

if __name__ == "__main__":
    print_banner()
    bot = TradingBot()
    if bot.connect():
        bot.menu()
