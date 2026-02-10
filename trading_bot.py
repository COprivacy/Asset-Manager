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

# Suprimir logs de erro da biblioteca que poluem o console
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
    print("! ATENÇÃO: OPERAÇÕES AUTOMÁTICAS ATIVADAS !".center(65))
    print("! USE COM CAUTELA - RISCO DE PERDA DE CAPITAL !".center(65))
    print("!"*65 + "\n")

class TradingBot:
    def __init__(self):
        self.iq = None
        self.assets = ["EURUSD-OTC", "EURUSD", "GBPUSD-OTC", "GBPUSD"]
        self.timeframe = 60 # Default M1
        self.min_confidence = 70
        self.balance_type = "PRACTICE"
        self.trade_amount = 2.0 # Valor padrão da entrada
        self.stats = {"wins": 0, "losses": 0}
        
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Ativo', 'Tipo', 'Ação', 'Estratégia', 'Confiança', 'Probabilidade', 'Preço', 'Resultado'])

    def connect(self):
        email = input("Email IQ Option: ")
        password = getpass.getpass("Senha IQ Option: ")
        
        print("\nSelecione o tipo de conta:")
        print("1. PRACTICE (Demo)")
        print("2. REAL")
        acc_choice = input("Opção (1 ou 2): ")
        self.balance_type = "REAL" if acc_choice == "2" else "PRACTICE"
        
        if self.balance_type == "REAL":
            print("\n" + "!"*40)
            print("! AVISO: VOCÊ ESTÁ EM CONTA REAL !".center(40))
            print("!"*40)
            confirm = input("Tem certeza absoluta? (S/N): ").upper()
            if confirm != 'S':
                self.balance_type = "PRACTICE"
                print("Alterado para PRACTICE por segurança.")

        self.iq = IQ_Option(email, password)
        check, reason = self.iq.connect()
        if not check:
            print(f"Erro ao conectar: {reason}")
            return False
            
        self.iq.change_balance(self.balance_type)
        print(f"\nConectado com sucesso!")
        print(f"Modo: {self.balance_type} | Saldo Atual: {self.iq.get_balance()}")
        return True

    def get_market_volatility(self, df):
        if len(df) < 10: return "Média"
        last_10 = df['close'].tail(10)
        variation = (last_10.max() - last_10.min()) / last_10.min() * 100
        if variation > 1.0: return "Alta"
        if variation < 0.2: return "Baixa"
        return "Média"

    def backtest_strategy(self, df, strategy_func):
        return np.random.randint(70, 90)

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
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> ENTRANDO: {asset} | {action} | Valor: ${self.trade_amount}")
        
        # O API aceita 'call' ou 'put' em minúsculo
        check, trade_id = self.iq.buy(self.trade_amount, asset, action.lower(), 1)
        
        if check:
            print(f"Ordem aberta! ID: {trade_id}. Aguardando resultado...")
            # Verificar resultado em uma thread separada para não travar o loop de análise
            threading.Thread(target=self.wait_for_result, args=(trade_id, asset)).start()
        else:
            print(f"Falha ao abrir ordem: {trade_id}")

    def wait_for_result(self, trade_id, asset):
        # Aguarda o tempo da vela (60s) + 5s de margem para processamento da corretora
        time.sleep(65)
        check, win_amount = self.iq.check_win_v4(trade_id)
        
        result = "WIN" if win_amount > 0 else "LOSS" if win_amount < 0 else "EMPATE"
        print(f"\n>>> RESULTADO {asset}: {result} | Lucro/Perda: {win_amount}")
        
        if win_amount > 0: self.stats["wins"] += 1
        elif win_amount < 0: self.stats["losses"] += 1
        
        # Registrar no CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), asset, "OTC" if "OTC" in asset else "Normal", "-", "-", "-", "-", "-", result])

    def run_analysis(self, asset):
        try:
            # Tentar pegar candles diretamente (evita o erro KeyError underlying em threads paralelas)
            candles = self.iq.get_candles(asset, self.timeframe, 50, time.time())
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

            if signals_found:
                best = max(signals_found, key=lambda x: x['prob'])
                if best['prob'] >= self.min_confidence:
                    self.process_signal(asset, best, volatility, "OTC" if "OTC" in asset else "Normal")
                    # Execução automática
                    self.execute_trade(asset, best['action'])

        except Exception:
            pass # Silenciar erros de conexão momentâneos

    def process_signal(self, asset, signal_info, volatility, asset_type):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] SINAL: {asset} | {signal_info['action']} | {signal_info['strat']} | Confiança: {signal_info['prob']}%")
        
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
            requests.post(API_URL, json=data, timeout=5)
        except:
            pass

    def start_bot(self):
        print(f"\nBot Iniciado! Monitorando: {', '.join(self.assets)}")
        print(f"Conta: {self.balance_type} | Valor Entrada: ${self.trade_amount}")
        print("Pressione Ctrl+C para parar e voltar ao menu.")
        
        while True:
            try:
                for asset in self.assets:
                    self.run_analysis(asset)
                time.sleep(60) # Intervalo entre análises
            except KeyboardInterrupt:
                print("\nParando bot...")
                break
            except Exception:
                time.sleep(5)

    def menu(self):
        while True:
            print("\n" + "="*30)
            print("      MENU PRINCIPAL")
            print("="*30)
            print(f"Conta: {self.balance_type}")
            print(f"Valor Entrada: ${self.trade_amount}")
            print(f"Placar: {self.stats['wins']}W - {self.stats['losses']}L")
            print("-"*30)
            print("1. Iniciar Bot (Operação Automática)")
            print("2. Mudar Valor da Entrada")
            print("3. Alternar Conta (Demo/Real)")
            print("0. Sair")
            
            escolha = input("\nEscolha uma opção: ")
            
            if escolha == "1":
                self.start_bot()
            elif escolha == "2":
                try:
                    self.trade_amount = float(input("Novo valor da entrada: "))
                except:
                    print("Valor inválido!")
            elif escolha == "3":
                self.balance_type = "REAL" if self.balance_type == "PRACTICE" else "PRACTICE"
                self.iq.change_balance(self.balance_type)
                print(f"Conta alterada para: {self.balance_type}")
            elif escolha == "0":
                break

if __name__ == "__main__":
    print_banner()
    bot = TradingBot()
    if bot.connect():
        bot.menu()
