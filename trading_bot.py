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
LOG_URL = "http://localhost:5000/api/logs"
CSV_FILE = "trades_history.csv"

def post_log(message):
    try:
        requests.post(LOG_URL, json={"message": message}, timeout=5)
    except:
        pass

def print_banner():
    msg = "QUANTUM SIGNALS PRO - MONITORAMENTO ATIVO"
    print("\n" + "█"*65)
    print(msg.center(65))
    print("█ ANALISANDO ASSERTIVIDADE EM TEMPO REAL".center(65))
    print("█ OPERAÇÃO AUTOMÁTICA ATIVADA".center(65))
    print("█"*65 + "\n")
    post_log(msg)

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
        post_log("Iniciando processo de login...")
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
            post_log(f"Erro de conexão: {reason}")
            print(f"Erro: {reason}")
            return False
            
        self.iq.change_balance(self.balance_type)
        balance = self.iq.get_balance()
        post_log(f"Conectado com sucesso! Modo: {self.balance_type} | Saldo: {balance}")
        print(f"Conectado! Saldo: {balance}")
        return True

    def get_precision_time(self):
        try:
            if self.iq:
                # Some versions use get_server_timestamp, others get_server_time
                for method in ['get_server_timestamp', 'get_server_time']:
                    if hasattr(self.iq, method):
                        return getattr(self.iq, method)()
            return int(time.time())
        except:
            return int(time.time())

    def analyze_strategies(self, asset, df):
        last_3 = df.tail(3)
        greens = sum(1 for _, row in last_3.iterrows() if row['close'] > row['open'])
        reds = 3 - greens
        
        strategies = []
        # MHI 1
        action = "CALL" if greens < reds else "PUT"
        strategies.append({"name": "MHI 1", "action": action, "conf": 80})
        
        # MHI 2
        action = "CALL" if greens > reds else "PUT"
        strategies.append({"name": "MHI 2", "action": action, "conf": 75})

        # Torres Gêmeas
        last_2 = df.tail(2)
        if all(row['close'] > row['open'] for _, row in last_2.iterrows()):
            strategies.append({"name": "Torres Gêmeas", "action": "CALL", "conf": 70})
        elif all(row['close'] < row['open'] for _, row in last_2.iterrows()):
            strategies.append({"name": "Torres Gêmeas", "action": "PUT", "conf": 70})

        # Adicionar bônus de performance
        for s in strategies:
            perf = self.strategy_performance.get(s['name'], {"wins": 0, "losses": 0})
            total = perf['wins'] + perf['losses']
            if total > 0:
                s['conf'] += (perf['wins'] / total) * 20

        post_log(f"Análise {asset}: {len(strategies)} estratégias verificadas.")
        return strategies

    def execute_trade_pro(self, asset, action, strategy, amount, is_mg=False):
        post_log(f"Iniciando ordem: {asset} | {action} | ${amount} ({strategy})")
        if self.iq:
            try:
                check, trade_id = self.iq.buy(amount, asset, action.lower(), 1)
                if check:
                    post_log(f"Ordem aceita pela corretora. ID: {trade_id}")
                    threading.Thread(target=self.manage_trade, args=(trade_id, asset, action, strategy, amount, is_mg)).start()
                else:
                    post_log(f"Erro ao enviar ordem: {trade_id}")
            except Exception as e:
                post_log(f"Erro na execução do trade: {str(e)}")

    def manage_trade(self, trade_id, asset, action, strategy, amount, is_mg):
        time.sleep(65)
        if self.iq:
            try:
                check, win_amount = self.iq.check_win_v4(trade_id)
                
                if win_amount > 0:
                    post_log(f"WIN em {asset}! Lucro: ${win_amount}")
                    self.stats["wins"] += 1
                    self.strategy_performance[strategy]["wins"] += 1
                    self.save_result(asset, action, strategy, "WIN", win_amount)
                elif win_amount < 0:
                    post_log(f"LOSS em {asset}! Perda: ${amount}")
                    if self.martingale > 0 and not is_mg:
                        post_log(f"Aplicando Martingale nível 1 em {asset}...")
                        self.execute_trade_pro(asset, action, strategy, amount * 2.2, is_mg=True)
                    else:
                        self.stats["losses"] += 1
                        self.strategy_performance[strategy]["losses"] += 1
                        self.save_result(asset, action, strategy, "LOSS", -amount)
                else:
                    post_log(f"EMPATE em {asset}.")
            except Exception as e:
                post_log(f"Erro ao gerenciar trade: {str(e)}")

    def save_result(self, asset, action, strategy, result, profit):
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%H:%M:%S"), asset, "OTC", action, strategy, result, profit])
        
        try:
            requests.post(API_URL, json={
                "asset": asset, "action": action, "strategy": strategy,
                "confidence": 100, "result": result, "price": str(profit)
            }, timeout=5)
        except: pass

    def start_engine(self):
        post_log(f"Motor de análise iniciado para ativos: {', '.join(self.assets)}")
        print(f"\nMotor Iniciado! Analisando Ciclos e Assertividade...")
        
        while self.running:
            try:
                server_time = self.get_precision_time()
                now = datetime.fromtimestamp(server_time)
                
                if now.second % 10 == 0:
                    print(f"Aguardando ciclo... {now.strftime('%H:%M:%S')}", end='\r')
                
                if now.second == 58:
                    post_log(f"Iniciando ciclo de análise para quadrante das {now.strftime('%H:%M')}")
                    for asset in self.assets:
                        if self.iq:
                            try:
                                candles = self.iq.get_candles(asset, 60, 10, server_time)
                                if not candles or len(candles) < 3:
                                    post_log(f"Aviso: {asset} não retornou candles suficientes.")
                                    continue
                                    
                                df = pd.DataFrame(candles)
                                df['close'] = df['close'].astype(float)
                                df['open'] = df['open'].astype(float)
                                
                                strategies = self.analyze_strategies(asset, df)
                                if not strategies: continue
                                
                                best = max(strategies, key=lambda x: x['conf'])
                                
                                if best['conf'] >= self.min_confidence:
                                    self.execute_trade_pro(asset, best['action'], best['name'], self.trade_amount)
                                else:
                                    post_log(f"Sinal fraco em {asset}: {best['name']} com {best['conf']}% de confiança.")
                            except Exception as e:
                                post_log(f"Erro ao analisar {asset}: {str(e)}")
                    
                    time.sleep(2)
                time.sleep(0.5)
            except KeyboardInterrupt:
                post_log("Motor parado pelo usuário.")
                self.running = False
            except Exception as e:
                post_log(f"Erro no loop principal: {str(e)}")
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
            elif c == "2":
                try:
                    self.trade_amount = float(input("Novo valor: "))
                except:
                    print("Valor inválido!")
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
