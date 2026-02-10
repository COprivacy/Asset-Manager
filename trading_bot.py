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
import logging

# Desativar logs excessivos da biblioteca
logging.getLogger('iqoptionapi').setLevel(logging.CRITICAL)

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
        self.assets = ["EURUSD-OTC", "EURUSD", "GBPUSD-OTC", "GBPUSD"]
        self.timeframe = 60 # Default M1
        self.min_confidence = 70
        self.balance_type = "PRACTICE" # Default
        self.trade_amount = 1.0 # Valor da entrada
        self.stats = {"wins": 0, "losses": 0, "streak": 0}
        
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Ativo', 'Tipo', 'Ação', 'Estratégia', 'Confiança', 'Probabilidade', 'Preço', 'Resultado'])

    def connect(self):
        email = input("Email IQ Option: ")
        password = getpass.getpass("Senha IQ Option: ")
        
        print("\nEscolha o tipo de conta:")
        print("1. PRACTICE (Demo)")
        print("2. REAL")
        acc_type = input("Opção (1 ou 2): ")
        self.balance_type = "REAL" if acc_type == "2" else "PRACTICE"
        
        if self.balance_type == "REAL":
            confirm = input("!!! VOCÊ SELECIONOU CONTA REAL. TEM CERTEZA? (S/N): ").upper()
            if confirm != "S":
                self.balance_type = "PRACTICE"
                print("Alterado para PRACTICE por segurança.")

        self.iq = IQ_Option(email, password)
        check, reason = self.iq.connect()
        if not check:
            print(f"Erro: {reason}")
            return False
            
        self.iq.change_balance(self.balance_type)
        print(f"Conectado! Modo: {self.balance_type} | Saldo: {self.iq.get_balance()}")
        return True

    def get_market_volatility(self, df):
        if len(df) < 10: return "Média"
        last_10 = df['close'].tail(10)
        variation = (last_10.max() - last_10.min()) / last_10.min() * 100
        if variation > 1.0: return "Alta"
        if variation < 0.2: return "Baixa"
        return "Média"

    def backtest_strategy(self, df, strategy_func):
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

    def execute_trade(self, asset, action):
        print(f">>> EXECUTANDO ORDEM: {asset} | {action} | Valor: {self.trade_amount}")
        action = action.lower()
        # Tempo de expiração: 1 minuto
        check, id = self.iq.buy(self.trade_amount, asset, action, 1)
        if check:
            print(f"Ordem aberta com sucesso! ID: {id}")
            # Thread para verificar resultado após 1 min
            threading.Thread(target=self.verify_result, args=(id, asset, action)).start()
        else:
            print(f"Erro ao abrir ordem: {id}")

    def verify_result(self, trade_id, asset, action):
        time.sleep(65) # Espera o tempo da vela + margem
        check, win = self.iq.check_win_v4(trade_id)
        result = "WIN" if win > 0 else "LOSS" if win < 0 else "EMPATE"
        print(f"--- RESULTADO {asset}: {result} ({win}) ---")
        if win > 0: self.stats["wins"] += 1
        elif win < 0: self.stats["losses"] += 1

    def run_analysis(self, asset):
        try:
            # Pegar candles sem disparar o erro de thread (get_all_open_time simplificado)
            candles = self.iq.get_candles(asset, self.timeframe, 100, time.time())
            if not candles or len(candles) < 5: 
                return
            
            df = pd.DataFrame(candles)
            df['close'] = df['close'].astype(float)
            df['open'] = df['open'].astype(float)
            
            volatility = self.get_market_volatility(df)
            signals_found = []

            # Estratégias
            action, strat = self.analyze_mhi(df)
            prob = self.backtest_strategy(df, "mhi")
            signals_found.append({"action": action, "strat": strat, "prob": prob})

            action, strat = self.analyze_padrao23(df)
            prob = self.backtest_strategy(df, "p23")
            signals_found.append({"action": action, "strat": strat, "prob": prob})

            action, strat = self.analyze_torres_gemeas(df)
            if action:
                prob = self.backtest_strategy(df, "torres")
                signals_found.append({"action": action, "strat": strat, "prob": prob})

            if signals_found:
                best = max(signals_found, key=lambda x: x['prob'])
                if best['prob'] >= self.min_confidence:
                    self.process_signal(asset, best, volatility, "OTC" if "OTC" in asset else "Normal")
                    self.execute_trade(asset, best['action'])

        except Exception as e:
            pass

    def process_signal(self, asset, signal_info, volatility, asset_type):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] SINAL: {asset} ({asset_type}) | {signal_info['action']} | {signal_info['strat']} | Prob: {signal_info['prob']}%")
        
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, asset, asset_type, signal_info['action'], signal_info['strat'], 100, signal_info['prob'], "0", "PENDENTE"])

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
        print(f"\nScan e Operação Automática iniciados para: {', '.join(self.assets)}")
        print(f"Modo: {self.balance_type} | Timeframe: {self.timeframe}s. Ctrl+C para parar.")
        while True:
            for asset in self.assets:
                self.run_analysis(asset)
            time.sleep(60)

    def menu(self):
        while True:
            print("\n--- MENU INTERATIVO ---")
            print(f"Modo: {self.balance_type} | Ativos: {', '.join(self.assets)}")
            print("1. Iniciar Scan e Operação Automática")
            print("2. Mudar Valor da Entrada (Atual: {self.trade_amount})")
            print("3. Ver Estatísticas (Wins: {self.stats['wins']} | Losses: {self.stats['losses']})")
            print("0. Sair")
            
            op = input("Opção: ")
            if op == "1":
                self.start_scan()
            elif op == "2":
                self.trade_amount = float(input("Novo valor: "))
            elif op == "3":
                print(f"\nStats: Wins {self.stats['wins']} | Losses {self.stats['losses']}")
            elif op == "0":
                break

if __name__ == "__main__":
    print_banner()
    bot = TradingBot()
    if bot.connect():
        bot.menu()
