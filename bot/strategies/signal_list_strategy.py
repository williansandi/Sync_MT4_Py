# bot/strategies/signal_list_strategy.py

import threading
import time
from datetime import datetime
import logging

class SignalListStrategy:
    def __init__(self, bot_core, signals, status_callback):
        self.bot_core = bot_core
        self.signals = signals # Recebe a lista de sinais
        self.status_callback = status_callback
        self.stop_event = threading.Event()
        self.strategy_thread = None
        self.is_running = False

    def is_alive(self):
        return self.is_running

    def start(self):
        self.is_running = True
        self.stop_event.clear()
        self.strategy_thread = threading.Thread(target=self._run_loop)
        self.strategy_thread.daemon = True
        self.strategy_thread.start()
        self.bot_core.log_callback(f"Estratégia de Lista de Sinais iniciada com {len(self.signals)} sinais.", "STRATEGY")

    def stop(self):
        self.is_running = False
        self.stop_event.set()
        self.bot_core.log_callback("Estratégia de Lista de Sinais parada.", "STRATEGY")

    def _run_loop(self):
        logging.info("Loop da lista de sinais iniciado.")
        
        while not self.stop_event.is_set():
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")

            for signal in self.signals:
                if signal['status'] == 'pending' and signal['time'] == current_time_str:
                    
                    # Evita re-entrar no mesmo minuto se a vela já virou
                    if now.second > 3: 
                        signal['status'] = 'expired'
                        self.bot_core.log_callback(f"Sinal {signal['asset']} às {signal['time']} expirou (vela virou).", "AVISO")
                        continue

                    logging.info(f"Executando sinal: {signal}")
                    signal['status'] = 'executing'
                    
                    # Passa o ID do sinal para o bot_core
                    context = {"signal_id": signal['id']}
                    self.bot_core.executar_trade(signal['asset'], signal['action'], 1, context)
            
            time.sleep(1) # Verifica a cada segundo
        
        logging.info("Loop da lista de sinais finalizado.")