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

    def check_filters(self):
        # 2. Filtros de horário (08:00-17:00 GMT)
        now_gmt = datetime.utcnow()
        if not (8 <= now_gmt.hour < 17):
            return False, "Fora do horário operacional (08:00-17:00 GMT)"
            
        # Notícias high-impact (manual)
        news_times = ["13:30"] # Exemplo: NFP
        current_time_str = now_gmt.strftime("%H:%M")
        for nt in news_times:
            # Simplificação: evita 30min antes/depois se for o mesmo horário HH:MM
            if current_time_str == nt:
                return False, "Notícia de alto impacto agora"
        
        return True, ""

    def get_ai_opinion(self, asset, df):
        try:
            # 5. Melhoria na análise: detectando padrões básicos para o prompt
            last_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]
            
            # Padrões simples
            is_hammer = (min(last_candle['open'], last_candle['close']) - last_candle['low']) > (abs(last_candle['open'] - last_candle['close']) * 2)
            is_engulfing_bull = (last_candle['close'] > prev_candle['open']) and (last_candle['open'] < prev_candle['close']) and (prev_candle['close'] < prev_candle['open'])
            
            patterns_info = f"Patterns: Hammer={is_hammer}, BullishEngulfing={is_engulfing_bull}"
            
            last_candles = df.tail(5).to_dict('records')
            prompt = f"Analise estes últimos 5 candles de 1min para {asset}: {json.dumps(last_candles)}. " \
                     f"Indicadores Atuais: RSI={last_candle['rsi']:.2f}, EMA20={last_candle['ema20']:.5f}, EMA50={last_candle['ema50']:.5f}. " \
                     f"{patterns_info}. " \
                     f"Explique seu raciocínio detalhadamente considerando Price Action + Volume + Indicadores e finalize com um objeto JSON contendo 'action' (CALL, PUT ou WAIT) e 'confidence' (0-100). " \
                     f"Formato esperado: 'Pensamento: <seu raciocínio> JSON: {{\"action\": \"...\", \"confidence\": ...}}'"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Você é um analista expert em Price Action e Confluência Técnica."},
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
            
            # 1. Regras de Confluência
            price = last_candle['close']
            rsi = last_candle['rsi']
            ema20 = last_candle['ema20']
            
            if result['action'] == 'CALL':
                if not (price > ema20 and rsi < 70):
                    result['confidence'] -= 20
                    post_log("⚠️ Confiança reduzida: CALL sem confluência EMA20/RSI")
            elif result['action'] == 'PUT':
                if not (price < ema20 and rsi > 30):
                    result['confidence'] -= 20
                    post_log("⚠️ Confiança reduzida: PUT sem confluência EMA20/RSI")
            
            post_log(f"🧠 IA Analisando {asset}: {thought}")
            post_log(f"🎯 Decisão Final: {result['action']} ({result['confidence']}%)")
            
            return result
        except Exception as e:
            post_log(f"Erro na análise de IA: {str(e)}")
            return {"action": "WAIT", "confidence": 0}

    def analyze_strategies(self, asset, df):
        # 2. Filtro de horário
        allowed, reason = self.check_filters()
        if not allowed:
            post_log(f"🚫 {asset}: {reason}")
            return [{"name": "AI Opinion", "action": "WAIT", "conf": 0}]

        df = self.calculate_indicators(df)
        ai_res = self.get_ai_opinion(asset, df)
        
        return [{
            "name": "AI Opinion", 
            "action": ai_res['action'], 
            "conf": ai_res['confidence']
        }]

    def execute_trade_pro(self, asset, action, strategy, amount, is_mg=False):
        # 3. Gerenciamento de Risco: Stake 1% do bankroll
        self.trade_amount = max(2.0, self.bankroll * 0.01)
        amount = self.trade_amount if not is_mg else amount
        
        self.active_trades[asset] = True
        post_log(f"🚀 Ordem: {asset} | {action} | ${amount:.2f} (Stake 1%)")
        
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
                    self.bankroll += win_amount
                    self.strategy_performance[strategy]["wins"] += 1
                    self.save_result(asset, action, strategy, "WIN", win_amount)
                    self.cooldowns[asset] = time.time() + 120
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
        post_log(f"Motor de análise iniciado para: {', '.join(self.assets)}")
        while self.running:
            try:
                server_time = self.get_precision_time()
                now = datetime.fromtimestamp(server_time)
                if now.second == 58:
                    for asset in self.assets:
                        if asset in self.active_trades: continue
                        if asset in self.cooldowns and time.time() < self.cooldowns[asset]: continue
                        
                        candles = self.iq.get_candles(asset, 60, 60, server_time) # Pegar 60 para EMAs
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
            print(f"\nPLACAR: {self.stats['wins']}W - {self.stats['losses']}L (WR: {winrate:.1f}%)")
            print(f"BANKROLL: ${self.bankroll:.2f} | MODO: {self.balance_type}")
            print("1. Iniciar Operações Automáticas (EMA + RSI + TimeFilter)")
            print("2. Ajustar Saldo Inicial (Simulado)")
            print("0. Sair")
            c = input("\n> ")
            if c == "1": self.start_engine()
            elif c == "2": self.bankroll = float(input("Novo bankroll: "))
            elif c == "0": break

if __name__ == "__main__":
    print_banner()
    bot = TradingBot()
    if bot.connect(): bot.menu()
