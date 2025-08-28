# bot/strategies/mt4_strategy.py
import zmq
import threading
import time

class MT4Strategy:
    def __init__(self, bot_core, context, status_callback):
        self.bot_core = bot_core
        self.context = context
        self.status_callback = status_callback
        self.stop_event = threading.Event()
        self.strategy_thread = None

        # (NOVO) Atributos para guardar a informação do último trade
        self.last_traded_asset = None
        self.last_trade_direction = None
        self.last_trade_value = 0

    def start(self):
        # ... (código sem alterações)
        self.stop_event.clear()
        self.strategy_thread = threading.Thread(target=self._listen_for_signals)
        self.strategy_thread.daemon = True
        self.strategy_thread.start()
        self.bot_core.log_callback("Estratégia MT4 iniciada. Aguardando sinais...", "STRATEGY")

    def stop(self):
        # ... (código sem alterações)
        self.stop_event.set()
        if self.strategy_thread: self.strategy_thread.join(timeout=2)
        self.bot_core.log_callback("Estratégia MT4 parada.", "STRATEGY")

    def _listen_for_signals(self):
        # ... (código sem alterações)
        socket = self.context.socket(zmq.SUB)
        socket.connect("tcp://127.0.0.1:5557")
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        last_heartbeat_time = time.time()
        self.status_callback("MT4", "CONECTADO", "Aguardando")
        while not self.stop_event.is_set():
            try:
                if socket.poll(1000):
                    message = socket.recv_string().strip()
                    if message == "MT4_HEARTBEAT": last_heartbeat_time = time.time()
                    elif "TESTE DE CONEXAO MANUAL" in message: self.bot_core.log_callback("Sinal de teste do MT4 recebido com sucesso!", "STATUS")
                    elif "Conexão com o Expert Advisor" in message or "EA Desconectado" in message: self.bot_core.log_callback(message, "STATUS")
                    elif message: self._process_trade_signal(message)
                if time.time() - last_heartbeat_time > 15: self.status_callback("MT4", "DESCONECTADO", "Sem sinal do EA!")
                else: self.status_callback("MT4", "CONECTADO", "Monitorando...")
            except Exception as e:
                self.bot_core.log_callback(f"Erro no listener MT4: {e}", "ERRO")
                self.status_callback("MT4", "ERRO", "Erro no socket")
                time.sleep(5)
        socket.close()
        self.status_callback("MT4", "PARADO", "Desconectado")

    def _process_trade_signal(self, signal_string):
        """Processa um sinal de trade, aplicando filtros rígidos e extraindo timeframe se possível."""
        try:
            self.bot_core.log_callback(f"Sinal recebido do MT4: '{signal_string}'", "INFO")
            sinal_upper = signal_string.upper()
            if "POSSÍVEL" in sinal_upper:
                self.bot_core.log_callback(f"Sinal ignorado (contém 'POSSÍVEL'): '{signal_string}'", "AVISO")
                return
            if "SUPER" not in sinal_upper:
                self.bot_core.log_callback(f"Sinal ignorado (não é um alerta 'SUPER'): '{signal_string}'", "AVISO")
                return

            palavras = sinal_upper.split()
            if len(palavras) < 3:
                self.bot_core.log_callback(f"Sinal ignorado (formato inválido): '{signal_string}'", "AVISO")
                return

            ativo = palavras[0]
            # Detecta timeframe (ex: M1, M5, M15)
            timeframe = 1  # padrão
            for p in palavras:
                if p.startswith('M') and p[1:].isdigit():
                    timeframe = int(p[1:])
                    break

            direcao = "put" if "VENDA" in palavras else "call" if "COMPRA" in palavras else None

            if ativo and direcao:
                self.bot_core.log_callback(f"Sinal VÁLIDO detectado! Ativo: {ativo}, Direção: {direcao}, Timeframe: {timeframe}", "STRATEGY")
                # --- (CORREÇÃO PARA O BUG "N/A") ---
                self.last_traded_asset = ativo
                self.last_trade_direction = direcao
                self.last_trade_value = self.bot_core.valor_entrada_inicial
                # ------------------------------------
                self.bot_core.executar_trade(ativo, direcao, timeframe)
            else:
                self.bot_core.log_callback(f"Não foi possível interpretar o sinal: '{signal_string}'", "AVISO")
        except Exception as e:
            self.bot_core.log_callback(f"Falha crítica ao processar sinal '{signal_string}': {e}", "ERRO")