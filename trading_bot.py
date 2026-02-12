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

# Configuração de Logs
logging.getLogger('iqoptionapi').setLevel(logging.CRITICAL)

# API Endpoint for Dashboard Integration
API_URL = "http://localhost:5000/api/signals"
CSV_FILE = "trades_history.csv"

def print_banner():
    print("\n" + "█"*65)
    print("█ QUANTUM SIGNALS PRO - ESTRATÉGIA DINÂMICA".center(65))
    print("█ ANALISANDO ASSERTIVIDADE EM TEMPO REAL".center(65))
    print("█ OPERAÇÃO AUTOMÁTICA ATIVADA".center(65))
    print("█"*65 + "\n")

class TradingBot:
    def __init__(self):
        self.iq = None
        self.assets = ["EURUSD-OTC", "GBPUSD-OTC", "EURUSD", "GBPUSD"]
        self.timeframe = 60 # M1
        self.min_confidence = 70
        self.balance_type = "PRACTICE"
        self.trade_amount = 2.0
        self.martingale = 1
        self.stats = {"wins": 0, "losses": 0}
        self.strategy_performance = {
            "MHI 1": {"wins": 0, "losses": 0},
            "MHI 2": {"wins": 0, "losses": 0},
            "MHI 3": {"wins": 0, "losses": 0},
            "Padrão 23": {"wins": 0, "losses": 0},
            "Torres Gêmeas": {"wins": 0, "losses": 0}
        }
        self.running = True
        
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Ativo', 'Tipo', 'Ação', 'Estratégia', 'Resultado', 'Lucro'])

    def connect(self):
        email = input("Email: ")
        password = getpass.getpass("Senha: ")
        
        print("\n1. PRACTICE (Demo) | 2. REAL")
        acc_choice = input("Opção: ")
        self.balance_type = "REAL" if acc_choice == "2" else "PRACTICE"
        
        if self.balance_type == "REAL":
            confirm = input("!!! CONTA REAL ATIVADA. CONFIRMAR? (S/N): ").upper()
            if confirm != 'S': self.balance_type = "PRACTICE"

        from iqoptionapi.stable_api import IQ_Option
        self.iq = IQ_Option(email, password)
        check, reason = self.iq.connect()
        if not check:
            print(f"Erro: {reason}")
            return False
            
        self.iq.change_balance(self.balance_type)
        print(f"Conectado! Saldo: {self.iq.get_balance()}")
        return True

    def get_precision_time(self):
        return self.iq.get_server_time()

    def analyze_strategies(self, df):
        # MHI 1: Minoria das últimas 3 velas do quadrante de 5
        last_3 = df.tail(3)
        greens = sum(1 for _, row in last_3.iterrows() if row['close'] > row['open'])
        reds = 3 - greens
        
        strategies = []
        
        # MHI 1 (Minoria)
        action = "CALL" if greens < reds else "PUT"
        strategies.append({"name": "MHI 1", "action": action, "conf": 80})
        
        # MHI 2 (Minoria da 2ª vela do quadrante) - Simplificado
        action = "CALL" if greens > reds else "PUT"
        strategies.append({"name": "MHI 2", "action": action, "conf": 75})

        # Torres Gêmeas
        last_2 = df.tail(2)
        if all(row['close'] > row['open'] for _, row in last_2.iterrows()):
            strategies.append({"name": "Torres Gêmeas", "action": "CALL", "conf": 70})
        elif all(row['close'] < row['open'] for _, row in last_2.iterrows()):
            strategies.append({"name": "Torres Gêmeas", "action": "PUT", "conf": 70})

        # Filtrar pela melhor performance histórica do bot nesta sessão
        for s in strategies:
            perf = self.strategy_performance.get(s['name'], {"wins": 0, "losses": 0})
            total = perf['wins'] + perf['losses']
            if total > 0:
                s['conf'] += (perf['wins'] / total) * 20 # Bônus de assertividade real

        return strategies

    def execute_trade_pro(self, asset, action, strategy, amount, is_mg=False):
        # Otimização de tempo para evitar delay (entrada aos 58s)
        print(f"\n>>> EXECUTANDO: {asset} | {action} | ${amount} ({strategy})")
        
        check, trade_id = self.iq.buy(amount, asset, action.lower(), 1)
        if check:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ordem Aberta! ID: {trade_id}")
            threading.Thread(target=self.manage_trade, args=(trade_id, asset, action, strategy, amount, is_mg)).start()
        else:
            print(f"Erro na Corretora: {trade_id}")

    def manage_trade(self, trade_id, asset, action, strategy, amount, is_mg):
        time.sleep(62)
        check, win_amount = self.iq.check_win_v4(trade_id)
        
        if win_amount > 0:
            print(f"WIN! {asset} | {strategy}")
            self.stats["wins"] += 1
            self.strategy_performance[strategy]["wins"] += 1
            self.save_result(asset, action, strategy, "WIN", win_amount)
        elif win_amount < 0:
            print(f"LOSS! {asset} | {strategy}")
            if self.martingale > 0 and not is_mg:
                print("Iniciando Martingale...")
                self.execute_trade_pro(asset, action, strategy, amount * 2.2, is_mg=True)
            else:
                self.stats["losses"] += 1
                self.strategy_performance[strategy]["losses"] += 1
                self.save_result(asset, action, strategy, "LOSS", -amount)
        else:
            print(f"EMPATE {asset}")

    def save_result(self, asset, action, strategy, result, profit):
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%H:%M:%S"), asset, "OTC", action, strategy, result, profit])
        
        try:
            requests.post(API_URL, json={
                "asset": asset, "action": action, "strategy": strategy,
                "confidence": 100, "result": result, "price": str(profit)
            })
        except: pass

    def start_engine(self):
        print(f"\nMotor Iniciado! Analisando Ciclos e Assertividade...")
        while self.running:
            try:
                now = datetime.fromtimestamp(self.get_precision_time())
                # Análise precisa: 2 segundos antes de fechar o minuto (no segundo 58)
                if now.second == 58:
                    for asset in self.assets:
                        candles = self.iq.get_candles(asset, 60, 10, time.time())
                        if not candles: continue
                        df = pd.DataFrame(candles)
                        df['close'] = df['close'].astype(float)
                        df['open'] = df['open'].astype(float)
                        
                        strategies = self.analyze_strategies(df)
                        # Escolher a estratégia com maior confiança (baseada em lógica + performance real)
                        best = max(strategies, key=lambda x: x['conf'])
                        
                        if best['conf'] >= self.min_confidence:
                            self.execute_trade_pro(asset, best['action'], best['name'], self.trade_amount)
                    
                    time.sleep(2) # Espera passar para o próximo minuto
                time.sleep(0.5)
            except KeyboardInterrupt:
                self.running = False
            except Exception:
                time.sleep(1)

    def menu(self):
        while True:
            print(f"\nPLACAR: {self.stats['wins']}W - {self.stats['losses']}L | Conta: {self.balance_type}")
            print("1. Iniciar Operações Automáticas (Múltiplas Estratégias)")
            print("2. Ajustar Valor Entrada (Atual: ${self.trade_amount})")
            print("3. Ver Ranking de Estratégias")
            print("0. Sair")
            
            c = input("\n> ")
            if c == "1": self.start_engine()
            elif c == "2": self.trade_amount = float(input("Novo valor: "))
            elif c == "3":
                print("\nRanking de Assertividade (Sessão Atual):")
                for s, p in self.strategy_performance.items():
                    total = p['wins'] + p['losses']
                    rate = (p['wins']/total*100) if total > 0 else 0
                    print(f"{s}: {p['wins']}W - {p['losses']}L ({rate:.1f}%)")
            elif c == "0": break

if __name__ == "__main__":
    print_banner()
    bot = TradingBot()
    if bot.connect(): bot.menu()
