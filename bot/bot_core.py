# bot/bot_core.py

import time
import threading
import logging
import queue
from datetime import datetime, timedelta
from iqoptionapi.stable_api import IQ_Option
from websocket._exceptions import WebSocketConnectionClosedException
from ui.components.news_scraper import fetch_structured_news
from .management.masaniello_manager import MasanielloManager
from .management.cycle_manager import CycleManager

class IQBotCore:
    def __init__(self, credentials, config, log_callback, trade_result_callback, pair_list_callback, status_callback):
        self.api = None
        self.credentials = credentials
        self.config = config
        self.log_callback = log_callback
        self.trade_result_callback = trade_result_callback
        self.pair_list_callback = pair_list_callback
        self.status_callback = status_callback
        
        self.lucro_total = 0.0
        self.is_running = False
        self.is_paused = False
        self.cifrao = "$"

        # --- Workers em Segundo Plano, Cache e Fila de Trades ---
        self.open_assets_cache = {}
        self.cache_last_updated = None
        self.cache_lock = threading.Lock()
        self.worker_thread = None
        self.stop_worker_event = threading.Event()
        self.trade_queue = queue.Queue()
        self.trade_executor_thread = None
        # ------------------------------------------------------
        
        # --- Lógica de Conexão e Reconexão (Internalizada) ---
        self.is_connected = False
        self.reconnect_in_progress = threading.Lock()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delays = [5, 15, 30, 60, 120]
        self.connection_restored_event = threading.Event()
        # ------------------------------------

        self.operacoes_em_andamento = {}
        self.news_events = []
        
        # --- Gerenciadores de Risco ---
        self.masaniello_manager = None
        self.cycle_manager = CycleManager(self.config, self.log_callback)
        self.active_manager = 'cycle'
        # ------------------------------------------------

        self._carregar_config()

    # --- Métodos de controle e configuração ---
    def reset_state(self):
        logging.info("Estado do bot_core resetado para nova sessão.")
        self.lucro_total = 0.0
        self.is_running = True
        if self.cycle_manager:
            self.cycle_manager.reset()

    def reload_config(self, new_config):
        self.config = new_config
        self._carregar_config()
        if self.cycle_manager:
            self.cycle_manager.reload_config(new_config)
        logging.info("Configurações do bot_core recarregadas.")

    def _carregar_config(self):
        def safe_float(key, default): 
            try: return float(self.config.get(key))
            except (ValueError, TypeError): return default
        def safe_int(key, default): 
            try: return int(float(self.config.get(key)))
            except (ValueError, TypeError): return default

        self.stop_win = safe_float('stop_win', 100.0)
        self.stop_loss = safe_float('stop_loss', 100.0)
        self.valor_entrada_inicial = safe_float('valor_entrada', 1.0)
        self.usar_filtro_noticias = self.config.get('usar_filtro_noticias', 'S').upper() == 'S'
        self.minutos_antes_noticia = safe_int('minutos_antes_noticia', 15)
        self.minutos_depois_noticia = safe_int('minutos_depois_noticia', 15)
        self.buy_timeout = safe_int('buy_timeout', 15)

    def set_active_manager(self, mode, manager_instance=None):
        self.active_manager = mode
        if mode == 'masaniello' and manager_instance:
            self.masaniello_manager = manager_instance
            self.log_callback(f"Modo de gerenciamento definido para: Masaniello", "CONFIG")
        else:
            self.masaniello_manager = None
            self.log_callback(f"Modo de gerenciamento definido para: Ciclos", "CONFIG")

    def set_pause_status(self, is_paused: bool):
        self.is_paused = is_paused
        status_text = "Pausado" if is_paused else "Continuado"
        self.log_callback(f"Robô {status_text}.", "STATUS")
        logging.info(f"Status do robô alterado para: {status_text}")

    # --- Arquitetura de Execução de Trades com Fila ---
    def executar_trade(self, ativo_sinal, direcao, timeframe, context={}):
        """Adiciona uma solicitação de trade à fila para execução sequencial."""
        if not self.is_running:
            self.log_callback(f"Trade para {ativo_sinal} ignorado: Robô não está em execução.", "AVISO")
            return
        
        trade_request = (ativo_sinal, direcao, timeframe, context)
        self.trade_queue.put(trade_request)
        self.log_callback(f"Sinal para {ativo_sinal} ({direcao.upper()}) adicionado à fila de execução.", "INFO")

    def _trade_executor_loop(self):
        """Loop do worker que consome a fila de trades e os executa um por um."""
        self.log_callback("Executor de Trades iniciado.", "DEBUG")
        while not self.stop_worker_event.is_set():
            try:
                if self.is_paused:
                    time.sleep(1)
                    continue

                trade_request = self.trade_queue.get_nowait()
                self._process_single_trade(trade_request)
                self.trade_queue.task_done()
            except queue.Empty:
                time.sleep(0.1) # Pequena pausa para evitar busy-waiting
                continue
            except Exception as e:
                self.log_callback(f"Erro no executor de trades: {e}", "ERRO")
                time.sleep(1) # Pausa em caso de erro inesperado
        self.log_callback("Executor de Trades finalizado.", "DEBUG")

    def _process_single_trade(self, trade_request):
        """Processa um único trade. Contém a lógica de validação e execução."""
        ativo_sinal, direcao, timeframe, context = trade_request
        
        if not self.is_connected:
            self.log_callback(f"Trade para {ativo_sinal} abortado: Sem conexão.", "ERRO")
            return

        ativo_real = self._resolver_ativo_correto(ativo_sinal)
        if not ativo_real:
            self.log_callback(f"Operação para {ativo_sinal} abortada: ativo não encontrado ou fechado.", "AVISO")
            return

        if self.operacoes_em_andamento.get(ativo_real, False):
            self.log_callback(f"Trade ignorado: Já existe uma operação em andamento para {ativo_real}.", "AVISO")
            return

        self._run_trade_cycle(ativo_real, direcao, timeframe, context)

    def _run_trade_cycle(self, ativo_real, direcao, timeframe, context):
        try:
            self.operacoes_em_andamento[ativo_real] = True
            
            while self.is_running and not self.stop_worker_event.is_set():
                entry_value, manager_name, should_record = self._get_entry_value()

                if entry_value <= 0:
                    self.log_callback(f"Gerenciador ({manager_name}) finalizou ou retornou valor inválido.", "INFO")
                    self.is_running = False
                    break

                if not self._validar_timeframe(ativo_real, timeframe):
                    break

                check, trade_id = self._enviar_ordem(entry_value, ativo_real, direcao, timeframe, manager_name)
                if not check:
                    break

                lucro = self._aguardar_e_processar_resultado(trade_id, timeframe)
                if lucro is None: # Erro crítico ou timeout
                    break

                if should_record:
                    self._registrar_resultado_gerenciador(lucro, entry_value)

                self.trade_result_callback({"profit": lucro, "entry_value": entry_value, "context": context, "foi_executado": True, "ativo": ativo_real})
                self.check_stop()

                if not self._deve_continuar_martingale(lucro):
                    break # Sai do ciclo de martingale (WIN ou fim dos níveis)
                
                self.log_callback(f"Iniciando Martingale para {ativo_real}...", "INFO")
                # O loop continuará para a próxima iteração (martingale)

        except WebSocketConnectionClosedException:
            self.log_callback(f"ERRO CRÍTICO: Conexão perdida durante trade em {ativo_real}.", "ERRO")
            self._trigger_reconnection()
        except Exception as e:
            logging.critical(f"ERRO CRÍTICO em _run_trade_cycle para {ativo_real}", exc_info=True)
            self.log_callback(f"ERRO CRÍTICO NO CICLO DE TRADE: {e}", "ERRO")
        finally:
            self.operacoes_em_andamento[ativo_real] = False

    # --- Métodos auxiliares do ciclo de trade ---
    def _resolver_ativo_correto(self, ativo_sinal):
        if not self.cache_last_updated:
            self.log_callback("Cache de ativos ainda não populado.", "ERRO")
            return None
        with self.cache_lock:
            # Usa o tipo de opção da configuração, com 'binary' como padrão.
            option_type = self.config.get('tipo', 'binary')
            lista_ativos_abertos = list(self.open_assets_cache.get(option_type, {}).keys())
        
        ativo_base = ativo_sinal.upper().replace('-OTC', '').replace('-OP', '')
        candidatos = []
        if "-OTC" in ativo_sinal.upper():
            candidatos.append(f"{ativo_base}-OTC")
        else:
            candidatos.append(f"{ativo_base}-op")
            candidatos.append(f"{ativo_base}-OP")
            candidatos.append(ativo_base)

        for candidato in candidatos:
            if candidato in lista_ativos_abertos:
                return candidato

        for ativo_aberto in lista_ativos_abertos:
            if ativo_aberto.upper().startswith(ativo_base):
                return ativo_aberto
        return None

    def _get_entry_value(self):
        if self.active_manager == 'cycle':
            if self.config.get('usar_ciclos', 'S') == 'S':
                return self.cycle_manager.get_next_entry_value(), "Ciclos", True
            else:
                return float(self.config.get('valor_entrada', 1.0)), "Fixo", False
        elif self.active_manager == 'masaniello' and self.masaniello_manager:
            return self.masaniello_manager.get_next_entry_value(), "Masaniello", True
        return 0, "N/A", False

    def _validar_timeframe(self, ativo, timeframe):
        timeframe_do_sinal = int(timeframe)
        tipo_opcao = 'turbo' if timeframe_do_sinal < 5 else 'binary'
        timeframes_disponiveis = self.api.get_available_expirations(ativo, tipo_opcao)
        if timeframes_disponiveis and timeframe_do_sinal not in timeframes_disponiveis:
            self.log_callback(f"Operação para {ativo} abortada. Timeframe M{timeframe_do_sinal} não disponível.", "AVISO")
            return False
        return True

    def _enviar_ordem(self, entry_value, ativo, direcao, timeframe, manager_name):
        self.log_callback(f'Ordem enviada: {ativo} {direcao.upper()} | {self.cifrao}{entry_value:.2f} | {manager_name}', "TRADE")
        try:
            check, trade_id = self.api.buy(entry_value, ativo, direcao, timeframe)
            if not (check and isinstance(trade_id, int)):
                self.log_callback(f"Ordem para {ativo} foi rejeitada ou falhou. Resposta: {trade_id}", "ERRO")
                return False, None
            return True, trade_id
        except Exception as e:
            self.log_callback(f"API Error on buy for {ativo}: {e}", "ERRO")
            return False, None

    def _registrar_resultado_gerenciador(self, lucro, entry_value):
        if self.active_manager == 'cycle':
            self.cycle_manager.record_trade(lucro, entry_value)
        elif self.active_manager == 'masaniello' and self.masaniello_manager:
            self.masaniello_manager.record_trade(entry_value, lucro)

    def _deve_continuar_martingale(self, lucro):
        return self.active_manager == 'cycle' and lucro <= 0 and self.cycle_manager.is_active and self.cycle_manager.current_martingale_level > 0 and self.cycle_manager.current_martingale_level <= self.cycle_manager.martingale_levels

    # --- Conexão e Workers ---
    def connect(self, *args, **kwargs):
        self.log_callback("Conectando à IQ Option...", "INFO")
        try:
            self.api = IQ_Option(self.credentials['email'], self.credentials['senha'])
            check, reason = self.api.connect()
            if not check:
                self.log_callback(f'Falha na conexão: {reason}', "ERRO")
                self.status_callback("IQ", "ERRO", "Falha na Conexão")
                self.connection_restored_event.clear()
                return False

            self.log_callback('Conectado com sucesso!', "INFO")
            self.api.change_balance(self.credentials['conta'])
            self.cifrao = self.api.get_profile_ansyc()['currency_char']
            all_assets = self.api.get_all_open_time()
            open_pairs = {asset for asset_type in ['turbo', 'binary'] if asset_type in all_assets for asset, details in all_assets[asset_type].items() if details.get('open', False)}
            self.pair_list_callback(sorted(list(open_pairs)))
            self.is_connected = True
            self.status_callback("IQ", "CONECTADO", "Online")
            self.connection_restored_event.set()
            return True
        except Exception as e:
            self.log_callback(f'Exceção ao conectar: {e}', "ERRO")
            self.status_callback("IQ", "ERRO", "Exceção na conexão")
            self.connection_restored_event.clear()
            return False

    def disconnect(self):
        self.stop_background_worker()
        if self.api and hasattr(self.api, 'ws') and hasattr(self.api.ws, 'wss') and self.api.ws.wss:
            try:
                self.api.ws.wss.close()
                self.log_callback("Conexão da IQ Option encerrada via websocket.", "INFO")
            except Exception as e:
                self.log_callback(f"Erro ao fechar conexão IQ Option: {e}", "ERRO")
        else:
            self.log_callback("IQ Option API não está conectada ou objeto websocket não encontrado.", "AVISO")
        self.log_callback("Conexão com a IQ Option encerrada.", "INFO")
        self.connection_restored_event.clear()

    def start_background_worker(self):
        if not (self.worker_thread and self.worker_thread.is_alive()):
            self.stop_worker_event.clear()
            self.worker_thread = threading.Thread(target=self._background_worker_loop, daemon=True)
            self.worker_thread.start()
            self.log_callback("Worker de Manutenção iniciado.", "DEBUG")

        if not (self.trade_executor_thread and self.trade_executor_thread.is_alive()):
            self.trade_executor_thread = threading.Thread(target=self._trade_executor_loop, daemon=True)
            self.trade_executor_thread.start()

    def stop_background_worker(self):
        self.stop_worker_event.set()
        if self.worker_thread: self.worker_thread.join(timeout=5)
        if self.trade_executor_thread: self.trade_executor_thread.join(timeout=5)

    def _background_worker_loop(self):
        self.log_callback("Worker de Manutenção iniciado. Executando primeira carga de dados...", "INFO")
        self._carregar_noticias_do_dia()
        self._update_open_assets_cache()

        WORKER_INTERVAL = 5
        NEWS_INTERVAL = 14400
        last_news_update = time.time()

        while not self.stop_worker_event.is_set():
            if self.stop_worker_event.wait(WORKER_INTERVAL): break
            
            if self._health_check_and_reconnect():
                now = time.time()
                if (now - last_news_update) >= NEWS_INTERVAL:
                    self._carregar_noticias_do_dia()
                    last_news_update = now

    def _health_check_and_reconnect(self):
        is_currently_ok = False
        try:
            if self.api and self.api.check_connect():
                self.api.get_server_timestamp()
                is_currently_ok = True
        except Exception:
            is_currently_ok = False

        if is_currently_ok:
            if not self.is_connected:
                self.is_connected = True
                self.reconnect_attempts = 0
                self.status_callback("IQ", "CONECTADO", "Online")
                self.log_callback("Conexão restabelecida.", "INFO")
                self.connection_restored_event.set()
        else:
            if self.is_connected:
                self.is_connected = False
                self.connection_restored_event.clear()
                self.log_callback("Conexão perdida. Acionando reconexão.", "AVISO")
                self._trigger_reconnection()
        return self.is_connected

    def _trigger_reconnection(self):
        if self.reconnect_in_progress.locked(): return
        reconnect_thread = threading.Thread(target=self._reconnect_with_backoff, daemon=True)
        reconnect_thread.start()

    def _reconnect_with_backoff(self):
        with self.reconnect_in_progress:
            if self.is_connected: return
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                self.log_callback("FALHA CRÍTICA DE CONEXÃO. REINICIE O ROBÔ.", "ERRO")
                self.status_callback("IQ", "ERRO", "Falha Crítica")
                self.stop_background_worker()
                return

            delay = self.reconnect_delays[min(self.reconnect_attempts, len(self.reconnect_delays) - 1)]
            self.log_callback(f"Tentando reconectar em {delay}s...", "AVISO")
            self.status_callback("IQ", "RECONECTANDO", f"Tentando em {delay}s")
            if self.stop_worker_event.wait(delay): return

            self.reconnect_attempts += 1
            try:
                check, reason = self.api.connect()
                if check:
                    self.is_connected = True
                    self.status_callback("IQ", "CONECTADO", "Online")
                    self.log_callback("Conexão reestabelecida com sucesso!", "INFO")
                    self.connection_restored_event.set()
                else:
                    self.log_callback(f"Falha ao reconectar: {reason}.", "ERRO")
            except Exception as e:
                self.log_callback(f"Exceção na tentativa de reconexão: {e}", "ERRO")

    def _aguardar_e_processar_resultado(self, trade_id, timeframe=1):
        resultado = None
        tempo_max_espera = (int(timeframe) * 60) + 35
        start_time = time.time()

        while time.time() - start_time < tempo_max_espera:
            if self.stop_worker_event.is_set(): break
            try:
                status, res = self.api.check_win_v4(trade_id)
                if status:
                    resultado = res
                    break
                time.sleep(1.0)
            except WebSocketConnectionClosedException:
                self.log_callback("Conexão perdida ao verificar resultado. Aguardando...", "AVISO")
                self._trigger_reconnection()
                restored = self.connection_restored_event.wait(timeout=60)
                if not restored:
                    self.log_callback("Não foi possível reestabelecer a conexão a tempo.", "ERRO")

        if resultado is None:
            self.log_callback(f"Timeout ou parada: Não foi possível obter resultado para o trade ID {trade_id}.", "ERRO")
            return -1

        lucro = round(resultado, 2)
        self.lucro_total += lucro

        if lucro > 0:
            self.log_callback(f'WIN | Lucro: {self.cifrao}{lucro:+.2f} | Saldo: {self.cifrao}{self.lucro_total:+.2f}', "WIN")
        else:
            msg = 'EMPATE' if lucro == 0 else 'LOSS'
            self.log_callback(f'{msg} | Prejuízo: {self.cifrao}{lucro:.2f} | Saldo: {self.cifrao}{self.lucro_total:+.2f}', "LOSS" if msg == 'LOSS' else "INFO")
        return lucro

    def _carregar_noticias_do_dia(self):
        logging.info("Iniciando busca por notícias econômicas do dia...")
        self.news_events = fetch_structured_news()
        if self.news_events:
            self.log_callback(f"{len(self.news_events)} notícias de impacto encontradas para hoje.", "INFO")
        else:
            self.log_callback("Nenhuma notícia de impacto encontrada ou falha na busca.", "AVISO")

    def _update_open_assets_cache(self):
        try:
            if self.api and self.is_connected:
                with self.cache_lock:
                    self.open_assets_cache = self.api.get_all_open_time()
                    self.cache_last_updated = datetime.now()
        except Exception as e:
            logging.error(f"Erro ao atualizar o cache de ativos abertos: {e}")

    def check_stop(self):
        if self.lucro_total <= -abs(self.stop_loss):
            self.is_running = False
            self.log_callback(f'STOP LOSS ATINGIDO: {self.cifrao}{self.lucro_total:.2f}', "STOP")
        if self.lucro_total >= abs(self.stop_win):
            self.is_running = False
            self.log_callback(f'STOP WIN ATINGIDO: {self.cifrao}{self.lucro_total:.2f}', "STOP")