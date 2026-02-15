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
from openai import OpenAI

# Configuração de Logs
logging.getLogger('iqoptionapi').setLevel(logging.CRITICAL)

# API Endpoint for Dashboard Integration
API_URL = "http://localhost:5000/api/signals"
LOG_URL = "http://localhost:5000/api/logs"
CSV_FILE = "trades_history.csv"

# Replit AI Client
client = OpenAI(
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://api.replit.com/ai/v1"),
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY", "dummy-key")
)

def post_log(message):
    try:
        requests.post(LOG_URL, json={"message": message}, timeout=5)
    except:
        pass

def print_banner():
    msg = "QUANTUM SIGNALS PRO - MONITORAMENTO ATIVO"
    print("\n" + "█" * 65)
    print(msg.center(65))
    print("█ ANALISANDO ASSERTIVIDADE EM TEMPO REAL".center(65))
    print("█ OPERAÇÃO AUTOMÁTICA ATIVADA".center(65))
    print("█" * 65 + "\n")
    post_log(msg)

class TradingBot:
    def __init__(self):
        self.iq = None
        self.assets = ["GBPUSD-OTC", "EURUSD", "GBPUSD"]
        self.timeframe = 60  # M1
        self.min_confidence = 75 # Aumentado para maior assertividade com IA
        self.balance_type = "PRACTICE"
        self.trade_amount = 2.0
        self.martingale = 0
        self.stats = {"wins": 0, "losses": 0}
        self.strategy_performance = {
            "MHI 1": {"wins": 0, "losses": 0},
            "MHI 2": {"wins": 0, "losses": 0},
            "MHI 3": {"wins": 0, "losses": 0},
            "Padrão 23": {"wins": 0, "losses": 0},
            "Torres Gêmeas": {"wins": 0, "losses": 0},
            "AI Opinion": {"wins": 0, "losses": 0}
        }
        self.running = True
        self.active_trades = {}
        self.cooldowns = {}

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
                for method in ['get_server_timestamp', 'get_server_time']:
                    if hasattr(self.iq, method):
                        return getattr(self.iq, method)()
            return int(time.time())
        except:
            return int(time.time())

    def get_ai_opinion(self, asset, df):
        try:
            # Preparar dados simplificados para a IA
            last_candles = df.tail(5).to_dict('records')
            prompt = f"Analise estes últimos 5 candles de 1min para {asset}: {json.dumps(last_candles)}. Responda APENAS com um JSON contendo 'action' (CALL, PUT ou WAIT) e 'confidence' (0-100)."
            
            response = client.chat.completions.create(
                model="gpt-4o", # Model available via Replit AI integration
                messages=[{"role": "system", "content": "Você é um analista expert em Price Action."},
                          {"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.choices[0].message.content)
            post_log(f"IA Sugere: {result['action']} ({result['confidence']}%)")
            return result
        except Exception as e:
            post_log(f"Erro na análise de IA: {str(e)}")
            return {"action": "WAIT", "confidence": 0}

    def analyze_strategies(self, asset, df):
        strategies = []
        
        # IA Opinion como única estratégia
        ai_res = self.get_ai_opinion(asset, df)
        if ai_res['action'] != "WAIT":
            strategies.append({
                "name": "AI Opinion", 
                "action": ai_res['action'], 
                "conf": ai_res['confidence']
            })

        # Bônus de performance para a IA
        for s in strategies:
            perf = self.strategy_performance.get(s['name'], {"wins": 0, "losses": 0})
            total = perf['wins'] + perf['losses']
            if total > 0:
                s['conf'] += (perf['wins'] / total) * 20

        return strategies

    def execute_trade_pro(self, asset, action, strategy, amount, is_mg=False):
        self.active_trades[asset] = True
        post_log(f"Iniciando ordem: {asset} | {action} | ${amount} ({strategy})")
        if self.iq:
            try:
                check, trade_id = self.iq.buy(amount, asset, action.lower(), 1)
                if check:
                    threading.Thread(target=self.manage_trade, args=(trade_id, asset, action, strategy, amount, is_mg)).start()
                else:
                    post_log(f"Erro ao enviar ordem: {trade_id}")
                    if asset in self.active_trades: del self.active_trades[asset]
            except Exception as e:
                post_log(f"Erro na execução do trade: {str(e)}")
                if asset in self.active_trades: del self.active_trades[asset]

    def manage_trade(self, trade_id, asset, action, strategy, amount, is_mg):
        time.sleep(65)
        if self.iq:
            try:
                check, win_amount = self.iq.check_win_v4(trade_id)
                if win_amount > 0:
                    self.stats["wins"] += 1
                    self.strategy_performance[strategy]["wins"] += 1
                    self.save_result(asset, action, strategy, "WIN", win_amount)
                    self.cooldowns[asset] = time.time() + 120
                    post_log(f"WIN em {asset}! Lucro: ${win_amount}")
                elif win_amount < 0:
                    if self.martingale > 0 and not is_mg:
                        self.execute_trade_pro(asset, action, strategy, amount * 2.2, is_mg=True)
                    else:
                        self.stats["losses"] += 1
                        self.strategy_performance[strategy]["losses"] += 1
                        self.save_result(asset, action, strategy, "LOSS", -amount)
                        post_log(f"LOSS em {asset}!")
                
                if asset in self.active_trades: del self.active_trades[asset]
            except Exception as e:
                post_log(f"Erro ao gerenciar trade: {str(e)}")
                if asset in self.active_trades: del self.active_trades[asset]

    def save_result(self, asset, action, strategy, result, profit):
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%H:%M:%S"), asset, "OTC", action, strategy, result, profit])
        try:
            requests.post(API_URL, json={"asset": asset, "action": action, "strategy": strategy, "confidence": 100, "result": result, "price": str(profit)}, timeout=5)
        except: pass

    def start_engine(self):
        post_log(f"Motor de análise iniciado para: {', '.join(self.assets)}")
        while self.running:
            try:
                server_time = self.get_precision_time()
                now = datetime.fromtimestamp(server_time)
                if now.second == 58:
                    for asset in self.assets:
                        if asset in self.active_trades: continue
                        if asset in self.cooldowns and time.time() < self.cooldowns[asset]: continue
                        
                        candles = self.iq.get_candles(asset, 60, 10, server_time)
                        if candles and len(candles) >= 3:
                            df = pd.DataFrame(candles)
                            df['close'] = df['close'].astype(float)
                            df['open'] = df['open'].astype(float)
                            strategies = self.analyze_strategies(asset, df)
                            if strategies:
                                best = max(strategies, key=lambda x: x['conf'])
                                if best['conf'] >= self.min_confidence:
                                    self.execute_trade_pro(asset, best['action'], best['name'], self.trade_amount)
                    time.sleep(2)
                time.sleep(0.5)
            except Exception as e:
                post_log(f"Erro no loop: {str(e)}")
                time.sleep(1)

    def menu(self):
        while True:
            print(f"\nPLACAR: {self.stats['wins']}W - {self.stats['losses']}L | Conta: {self.balance_type}")
            print("1. Iniciar Operações Automáticas (Com IA)")
            print("2. Ajustar Valor Entrada (${self.trade_amount})")
            print("0. Sair")
            c = input("\n> ")
            if c == "1": self.start_engine()
            elif c == "2": self.trade_amount = float(input("Novo valor: "))
            elif c == "0": break

if __name__ == "__main__":
    print_banner()
    bot = TradingBot()
    if bot.connect(): bot.menu()
