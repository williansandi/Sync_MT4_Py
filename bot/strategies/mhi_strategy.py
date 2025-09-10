# bot/strategies/mhi_strategy.py
import threading
import time
from datetime import datetime

class MHIStrategy:
    def __init__(self, bot_core, ativo):
        self.bot_core = bot_core
        self.ativo = ativo
        self.stop_event = threading.Event()
        self.strategy_thread = None
        self.log = self.bot_core.log_callback
        self.last_traded_asset = None
        self.last_trade_direction = None

    def start(self):
        if self.strategy_thread is None or not self.strategy_thread.is_alive():
            self.stop_event.clear()
            self.strategy_thread = threading.Thread(target=self._run_strategy_loop)
            self.strategy_thread.daemon = True
            self.strategy_thread.start()
            self.log(f"Estratégia MHI iniciada para o ativo {self.ativo}.", "STRATEGY")

    def stop(self):
        self.stop_event.set()
        if self.strategy_thread: self.strategy_thread.join(timeout=2)
        self.log("Estratégia MHI parada.", "STRATEGY")

    def _run_strategy_loop(self):
        self.log("Aguardando horário de entrada para MHI (final de velas M5)...", "INFO")
        while not self.stop_event.is_set():
            minutos = float(datetime.fromtimestamp(self.bot_core.api.get_server_timestamp()).strftime('%M.%S'))
            entrar = (4.58 <= (minutos % 5) <= 5.0)
            if entrar:
                self.log("Horário de entrada MHI detectado, analisando...", "INFO")
                self._analisar_e_operar()
                time.sleep(60) 
            time.sleep(0.5)

    def _analisar_e_operar(self):
        try:
            velas_raw = self.bot_core.api.get_candles(self.ativo, 60, 3, time.time())
            if velas_raw is None or len(velas_raw) < 3:
                self.log(f"Não foi possível obter 3 velas para {self.ativo}.", "AVISO")
                return
            cores = ['Verde' if v['open'] < v['close'] else 'Vermelha' if v['open'] > v['close'] else 'Doji' for v in velas_raw]
            self.log(f"Análise MHI: {cores[0]}, {cores[1]}, {cores[2]}", "INFO")

            if 'Doji' in cores:
                self.log("Análise abortada: Doji encontrado.", "AVISO")
                return

            direcao = 'put' if cores.count('Verde') > cores.count('Vermelha') else 'call' if cores.count('Vermelha') > cores.count('Verde') else None
            if direcao:
                self.log(f"Sinal MHI: Entrada para {direcao.upper()}.", "STRATEGY")
                self.last_traded_asset = self.ativo
                self.last_trade_direction = direcao
                # A chamada agora é direta e não bloqueante, apenas enfileira o trade
                self.bot_core.executar_trade(self.ativo, direcao, 1)
            else:
                self.log("Análise abortada: Empate de cores.", "AVISO")
        except Exception as e:
            self.log(f"Erro na análise MHI: {e}", "ERRO")