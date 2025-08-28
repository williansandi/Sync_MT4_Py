# bot/connection_manager.py

import time
import threading
import logging
from iqoptionapi.stable_api import IQ_Option

class ConnectionManager:
    def __init__(self, api_instance, log_callback, status_callback):
        self.api = api_instance
        self.log_callback = log_callback
        self.status_callback = status_callback
        
        self.is_connected = False
        self.reconnect_in_progress = threading.Lock()
        self.health_check_thread = None
        self.stop_event = threading.Event()
        
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delays = [5, 15, 30, 60, 120]  # Exponential backoff delays

    def start(self):
        """Inicia o monitoramento da conexão."""
        if self.health_check_thread and self.health_check_thread.is_alive():
            logging.info("ConnectionManager já está em execução.")
            return
            
        self.stop_event.clear()
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        self.log_callback("Gerenciador de Conexão iniciado.", "INFO")
        logging.info("ConnectionManager started.")

    def stop(self):
        """Para o monitoramento da conexão."""
        self.stop_event.set()
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        self.log_callback("Gerenciador de Conexão parado.", "INFO")
        logging.info("ConnectionManager stopped.")

    def _health_check_loop(self):
        """Loop principal que verifica a saúde da conexão periodicamente."""
        while not self.stop_event.is_set():
            if self.api and self.api.check_connect():
                try:
                    # get_server_timestamp é uma chamada leve para verificar a conexão real.
                    self.api.get_server_timestamp()
                    if not self.is_connected:
                        self.is_connected = True
                        self.reconnect_attempts = 0  # Reseta tentativas após sucesso
                        self.status_callback("IQ", "CONECTADO", "Online")
                        self.log_callback("Conexão com a IQ Option está saudável.", "INFO")
                except Exception as e:
                    self.is_connected = False
                    self.log_callback(f"Health Check falhou, mesmo com check_connect() True. Erro: {e}", "AVISO")
                    self._trigger_reconnection()
            else:
                if self.is_connected:
                    self.is_connected = False
                    self.log_callback("Conexão com a IQ Option perdida.", "AVISO")
                self._trigger_reconnection()
            
            # Verifica a cada 10 segundos
            self.stop_event.wait(10)

    def _trigger_reconnection(self):
        """Aciona o processo de reconexão em uma nova thread para não bloquear."""
        if self.reconnect_in_progress.locked():
            # Já existe uma tentativa de reconexão em andamento.
            return

        reconnect_thread = threading.Thread(target=self._reconnect_with_backoff)
        reconnect_thread.daemon = True
        reconnect_thread.start()

    def _reconnect_with_backoff(self):
        """Tenta reconectar usando uma estratégia de exponential backoff."""
        with self.reconnect_in_progress:
            if self.is_connected:
                return

            if self.reconnect_attempts >= self.max_reconnect_attempts:
                self.log_callback("FALHA CRÍTICA DE CONEXÃO. VERIFIQUE SUA INTERNET E REINICIE O ROBÔ.", "ERRO")
                self.status_callback("IQ", "ERRO", "Falha Crítica")
                self.stop() # Para de tentar
                return

            delay = self.reconnect_delays[min(self.reconnect_attempts, len(self.reconnect_delays) - 1)]
            
            self.log_callback(f"Tentando reconectar em {delay} segundos... (Tentativa {self.reconnect_attempts + 1}/{self.max_reconnect_attempts})", "AVISO")
            self.status_callback("IQ", "RECONECTANDO", f"Tentando em {delay}s")
            
            self.stop_event.wait(delay)
            if self.stop_event.is_set(): return # Se o bot foi parado, cancela a reconexão

            self.reconnect_attempts += 1
            
            try:
                logging.info(f"Attempting to reconnect... (Attempt {self.reconnect_attempts})")
                check, reason = self.api.connect()
                if check:
                    self.is_connected = True
                    self.reconnect_attempts = 0
                    self.log_callback("Reconectado com sucesso à IQ Option!", "INFO")
                    logging.info("Successfully reconnected to IQ Option.")
                    self.status_callback("IQ", "CONECTADO", "Online")
                else:
                    self.log_callback(f"Falha ao reconectar: {reason}. Agendando nova tentativa.", "ERRO")
                    logging.error(f"Failed to reconnect: {reason}")
                    # A proxima tentativa será acionada pelo health check loop
            except Exception as e:
                self.log_callback(f"Exceção durante a tentativa de reconexão: {e}", "ERRO")
                logging.error(f"Exception during reconnection attempt: {e}", exc_info=True)
                # A proxima tentativa será acionada pelo health check loop
