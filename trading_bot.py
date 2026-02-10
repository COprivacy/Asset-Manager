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
    print("█ QUANTUM SIGNALS PRO - OTC EDITION".center(65))
    print("█ ESTRATÉGIA: MHI 1/2 + CICLOS DE PRECISÃO".center(65))
    print("█ MODO: OPERAÇÃO AUTOMÁTICA COM ANTECIPAÇÃO DE DELAY".center(65))
    print("█"*65 + "\n")

class TradingBot:
    def __init__(self):
        self.iq = None
        self.assets = ["EURUSD-OTC", "GBPUSD-OTC", "EURUSD", "GBPUSD"]
        self.timeframe = 60 # M1
        self.min_confidence = 75
        self.balance_type = "PRACTICE"
        self.trade_amount = 2.0
        self.martingale = 1 # 0 para desativar, 1 para nível 1
        self.stats = {"wins": 0, "losses": 0}
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

        self.iq = IQ_Option(email, password)
        check, reason = self.iq.connect()
        if not check:
            print(f"Erro: {reason}")
            return False
            
        self.iq.change_balance(self.balance_type)
        print(f"Conectado! Saldo: {self.iq.get_balance()}")
        return True

    def get_precision_time(self):
        # Sincroniza com o servidor da IQ Option para evitar delay
        return self.iq.get_server_time()

    def analyze_mhi_plus(self, df):
        # MHI 1: Analisa as últimas 3 velas do quadrante de 5
        # Estratégia vencedora em OTC: Seguir a minoria do quadrante
        last_3 = df.tail(3)
        greens = sum(1 for _, row in last_3.iterrows() if row['close'] > row['open'])
        reds = 3 - greens
        
        if greens < reds:
            return "CALL", "MHI 1 (Minoria Verde)", 82
        else:
            return "PUT", "MHI 1 (Minoria Vermelha)", 82

    def execute_trade_pro(self, asset, action, strategy, amount, is_mg=False):
        # Antecipação de Delay: Entrar 1-2 segundos antes do fechamento da vela
        # Para M1, o fechamento é nos 00s. Entramos nos 58-59s.
        
        print(f"\n>>> PREPARANDO ENTRADA: {asset} | {action} | ${amount} {'(MG1)' if is_mg else ''}")
        
        # Loop de precisão de microssegundos
        while True:
            now = self.get_precision_time()
            seconds = datetime.fromtimestamp(now).second
            if seconds >= 58: # Entra no segundo 58-59 para bater no 00 certinho
                break
            time.sleep(0.1)

        check, trade_id = self.iq.buy(amount, asset, action.lower(), 1)
        if check:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ordem Aberta! ID: {trade_id}")
            threading.Thread(target=self.manage_trade, args=(trade_id, asset, action, strategy, amount, is_mg)).start()
        else:
            print(f"Erro: {trade_id}")

    def manage_trade(self, trade_id, asset, action, strategy, amount, is_mg):
        time.sleep(62) # Espera a vela fechar
        check, win_amount = self.iq.check_win_v4(trade_id)
        
        if win_amount > 0:
            print(f"WIN! {asset} | +${win_amount}")
            self.stats["wins"] += 1
            self.save_result(asset, action, strategy, "WIN", win_amount)
        elif win_amount < 0:
            print(f"LOSS! {asset} | -${amount}")
            if self.martingale > 0 and not is_mg:
                print("Aplicando Martingale Nível 1...")
                self.execute_trade_pro(asset, action, strategy, amount * 2.2, is_mg=True)
            else:
                self.stats["losses"] += 1
                self.save_result(asset, action, strategy, "LOSS", -amount)
        else:
            print(f"EMPATE {asset}")

    def save_result(self, asset, action, strategy, result, profit):
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%H:%M:%S"), asset, "OTC", action, strategy, result, profit])
        
        # Update dashboard
        try:
            requests.post(API_URL, json={
                "asset": asset, "action": action, "strategy": strategy,
                "confidence": 100, "result": result, "price": str(profit)
            })
        except: pass

    def start_engine(self):
        print(f"\nSistema Monitorando: {self.assets}")
        while self.running:
            try:
                # Sincronização de Ciclo: Analisa no segundo 50 de cada minuto
                now = datetime.fromtimestamp(self.get_precision_time())
                if now.second >= 45 and now.second <= 50:
                    for asset in self.assets:
                        candles = self.iq.get_candles(asset, 60, 10, time.time())
                        if not candles: continue
                        df = pd.DataFrame(candles)
                        df['close'] = df['close'].astype(float)
                        df['open'] = df['open'].astype(float)
                        
                        action, strat, conf = self.analyze_mhi_plus(df)
                        if conf >= self.min_confidence:
                            self.execute_trade_pro(asset, action, strat, self.trade_amount)
                    
                    time.sleep(10) # Evita re-analisar no mesmo minuto
                time.sleep(1)
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                time.sleep(5)

    def menu(self):
        while True:
            print(f"\nSTATUS: {self.stats['wins']}W - {self.stats['losses']}L | Conta: {self.balance_type}")
            print("1. Iniciar Motor Quantum PRO (OTC)")
            print("2. Ajustar Stake (Atual: ${self.trade_amount})")
            print("3. Alternar Martingale (Nível 1: {'ON' if self.martingale else 'OFF'})")
            print("0. Sair")
            
            c = input("\n> ")
            if c == "1": self.start_engine()
            elif c == "2": self.trade_amount = float(input("Stake: "))
            elif c == "3": self.martingale = 1 if self.martingale == 0 else 0
            elif c == "0": break

if __name__ == "__main__":
    from iqoptionapi.stable_api import IQ_Option
    print_banner()
    bot = TradingBot()
    if bot.connect(): bot.menu()
