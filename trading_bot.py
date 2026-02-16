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
        self.timeframe = 60  # Tempo gráfico atual (em segundos)
        self.min_confidence = 75 
        self.balance_type = "PRACTICE"
        self.trade_amount = 2.0
        self.bankroll = 1000.0
        self.martingale = 0
        self.stats = {"wins": 0, "losses": 0}
        self.strategy_performance = {
            "AI Opinion": {"wins": 0, "losses": 0}
        }
        self.running = True
        self.active_trades = {}
        self.cooldowns = {}
        self.trade_log = []

        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Ativo', 'Tipo', 'Ação', 'Estratégia', 'Resultado', 'Lucro', 'Bankroll'])

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
        self.bankroll = float(balance)
        post_log(f"Conectado com sucesso! Modo: {self.balance_type} | Saldo: {balance}")
        print(f"Conectado! Saldo: {balance}")
        return True

    def get_precision_time(self):
        try:
            if self.iq:
                return self.iq.get_server_timestamp()
            return int(time.time())
        except:
            return int(time.time())

    def calculate_indicators(self, df):
        # 1. EMAs
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # 2. RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    def get_ai_opinion(self, asset, df):
        try:
            last_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]
            
            # Padrões de Candles
            is_hammer = (min(last_candle['open'], last_candle['close']) - last_candle['low']) > (abs(last_candle['open'] - last_candle['close']) * 2)
            is_engulfing_bull = (last_candle['close'] > prev_candle['open']) and (last_candle['open'] < prev_candle['close']) and (prev_candle['close'] < prev_candle['open'])
            is_engulfing_bear = (last_candle['close'] < prev_candle['open']) and (last_candle['open'] > prev_candle['close']) and (prev_candle['close'] > prev_candle['open'])
            
            patterns_info = f"Patterns: Hammer={is_hammer}, BullishEngulfing={is_engulfing_bull}, BearishEngulfing={is_engulfing_bear}"
            
            tf_desc = f"{self.timeframe // 60}min"
            last_candles = df.tail(10).to_dict('records') # Envia 10 candles para mais contexto
            
            prompt = f"Analise o gráfico de {tf_desc} para {asset}. Candles: {json.dumps(last_candles)}. " \
                     f"Indicadores: RSI={last_candle['rsi']:.2f}, EMA20={last_candle['ema20']:.5f}, EMA50={last_candle['ema50']:.5f}. " \
                     f"{patterns_info}. " \
                     f"Identifique Suportes/Resistências próximos. Considere a tendência das EMAs e RSI. " \
                     f"Decida entre CALL, PUT ou WAIT com % de confiança (0-100). " \
                     f"Responda EXATAMENTE neste formato: 'Pensamento: <breve lógica> JSON: {{\"action\": \"...\", \"confidence\": ...}}'"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": f"Você é um analista de trading profissional focado em {tf_desc}. Use Price Action, Volume e Indicadores Técnicos."},
                          {"role": "user", "content": prompt}]
            )
            
            raw_content = response.choices[0].message.content.strip()
            thought = "Não detalhado"
            json_part = raw_content
            
            if "JSON:" in raw_content:
                parts = raw_content.split("JSON:")
                thought = parts[0].replace("Pensamento:", "").strip()
                json_part = parts[1].strip()
            
            if json_part.startswith("```json"):
                json_part = json_part[7:-3].strip()
            elif json_part.startswith("```"):
                json_part = json_part[3:-3].strip()
                
            result = json.loads(json_part)
            
            # Confluência Extra
            price = last_candle['close']
            rsi = last_candle['rsi']
            ema20 = last_candle['ema20']
            
            if result['action'] == 'CALL':
                if not (price > ema20 and rsi < 70):
                    result['confidence'] -= 15
                    post_log(f"⚠️ {asset}: CALL sem confluência total (Preço vs EMA20 ou RSI)")
            elif result['action'] == 'PUT':
                if not (price < ema20 and rsi > 30):
                    result['confidence'] -= 15
                    post_log(f"⚠️ {asset}: PUT sem confluência total (Preço vs EMA20 ou RSI)")
            
            post_log(f"🧠 IA ({tf_desc}) {asset}: {thought}")
            post_log(f"🎯 Decisão: {result['action']} ({result['confidence']}%)")
            
            # Send analysis to dashboard even if it's WAIT
            try:
                requests.post(API_URL, json={
                    "asset": asset,
                    "action": result['action'],
                    "strategy": f"AI Opinion ({tf_desc})",
                    "confidence": result['confidence'],
                    "reasoning": thought,
                    "result": "ANALYZING"
                }, timeout=5)
            except: pass

            return result
        except Exception as e:
            post_log(f"Erro na análise de IA: {str(e)}")
            return {"action": "WAIT", "confidence": 0}

    def analyze_strategies(self, asset, df):
        df = self.calculate_indicators(df)
        ai_res = self.get_ai_opinion(asset, df)
        
        return [{
            "name": "AI Opinion", 
            "action": ai_res['action'], 
            "conf": ai_res['confidence']
        }]

    def execute_trade_pro(self, asset, action, strategy, amount, is_mg=False):
        self.trade_amount = max(2.0, self.bankroll * 0.01)
        amount = self.trade_amount if not is_mg else amount
        
        self.active_trades[asset] = True
        post_log(f"🚀 Ordem: {asset} | {action} | ${amount:.2f} (Stake 1%)")
        
        if self.iq:
            try:
                # Expiração automática baseada no timeframe selecionado
                duration = self.timeframe // 60
                check, trade_id = self.iq.buy(amount, asset, action.lower(), duration)
                if check:
                    threading.Thread(target=self.manage_trade, args=(trade_id, asset, action, strategy, amount, is_mg)).start()
                else:
                    post_log(f"Erro ao enviar ordem: {trade_id}")
                    if asset in self.active_trades: del self.active_trades[asset]
            except Exception as e:
                post_log(f"Erro na execução do trade: {str(e)}")
                if asset in self.active_trades: del self.active_trades[asset]

    def manage_trade(self, trade_id, asset, action, strategy, amount, is_mg):
        # Aguarda tempo de expiração + buffer
        time.sleep(self.timeframe + 5)
        if self.iq:
            try:
                check, win_amount = self.iq.check_win_v4(trade_id)
                if win_amount > 0:
                    self.stats["wins"] += 1
                    self.bankroll += win_amount
                    self.strategy_performance[strategy]["wins"] += 1
                    self.save_result(asset, action, strategy, "WIN", win_amount)
                    self.cooldowns[asset] = time.time() + (self.timeframe * 2)
                    post_log(f"✅ WIN em {asset}! Lucro: ${win_amount} | Saldo: ${self.bankroll:.2f}")
                elif win_amount < 0:
                    self.bankroll -= amount
                    if self.martingale > 0 and not is_mg:
                        self.execute_trade_pro(asset, action, strategy, amount * 2.2, is_mg=True)
                    else:
                        self.stats["losses"] += 1
                        self.strategy_performance[strategy]["losses"] += 1
                        self.save_result(asset, action, strategy, "LOSS", -amount)
                        post_log(f"❌ LOSS em {asset}! Saldo: ${self.bankroll:.2f}")
                
                if asset in self.active_trades: del self.active_trades[asset]
            except Exception as e:
                post_log(f"Erro ao gerenciar trade: {str(e)}")
                if asset in self.active_trades: del self.active_trades[asset]

    def save_result(self, asset, action, strategy, result, profit):
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%H:%M:%S"), asset, "SPOT", action, strategy, result, profit, self.bankroll])
        try:
            requests.post(API_URL, json={
                "asset": asset, 
                "action": action, 
                "strategy": strategy, 
                "confidence": 100, 
                "result": result, 
                "price": str(profit)
            }, timeout=5)
        except: pass

    def start_engine(self):
        tf_desc = f"{self.timeframe // 60}M"
        post_log(f"Motor iniciado em {tf_desc} para: {', '.join(self.assets)}")
        while self.running:
            try:
                server_time = self.get_precision_time()
                now = datetime.fromtimestamp(server_time)
                
                # Sincroniza com o fechamento do candle do timeframe selecionado
                if now.second == 58 and (now.minute + 1) % (self.timeframe // 60) == 0:
                    for asset in self.assets:
                        if asset in self.active_trades: continue
                        if asset in self.cooldowns and time.time() < self.cooldowns[asset]: continue
                        
                        candles = self.iq.get_candles(asset, self.timeframe, 60, server_time)
                        if candles and len(candles) >= 50:
                            df = pd.DataFrame(candles)
                            df['close'] = df['close'].astype(float)
                            df['open'] = df['open'].astype(float)
                            df['volume'] = df['volume'].astype(float)
                            
                            strategies = self.analyze_strategies(asset, df)
                            if strategies:
                                best = max(strategies, key=lambda x: x['conf'])
                                if best['action'] != "WAIT" and best['conf'] >= self.min_confidence:
                                    self.execute_trade_pro(asset, best['action'], best['name'], self.trade_amount)
                    time.sleep(2)
                time.sleep(0.5)
            except Exception as e:
                post_log(f"Erro no loop: {str(e)}")
                time.sleep(1)

    def menu(self):
        while True:
            winrate = (self.stats['wins'] / (self.stats['wins'] + self.stats['losses']) * 100) if (self.stats['wins'] + self.stats['losses']) > 0 else 0
            tf_desc = f"{self.timeframe // 60}M"
            print(f"\nPLACAR: {self.stats['wins']}W - {self.stats['losses']}L (WR: {winrate:.1f}%)")
            print(f"BANKROLL: ${self.bankroll:.2f} | TIMEFRAME: {tf_desc}")
            print("1. Iniciar Operações Automáticas")
            print("2. Selecionar Tempo Gráfico (M1, M5, M15)")
            print("3. Ajustar Saldo Inicial")
            print("0. Sair")
            c = input("\n> ")
            if c == "1": self.start_engine()
            elif c == "2":
                print("\n1. M1 | 2. M5 | 3. M15")
                t_choice = input("Opção: ")
                if t_choice == "1": self.timeframe = 60
                elif t_choice == "2": self.timeframe = 300
                elif t_choice == "3": self.timeframe = 900
            elif c == "3": self.bankroll = float(input("Novo bankroll: "))
            elif c == "0": break

if __name__ == "__main__":
    print_banner()
    bot = TradingBot()
    if bot.connect(): bot.menu()
