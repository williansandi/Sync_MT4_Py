# bot/bot_core.py

import time
import threading
import logging
from datetime import datetime, timedelta
from iqoptionapi.stable_api import IQ_Option
from websocket._exceptions import WebSocketConnectionClosedException
from ui.components.news_scraper import fetch_structured_news
from .management.masaniello_manager import MasanielloManager
from .management.cycle_manager import CycleManager
from .connection_manager import ConnectionManager

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
        self.stop = True
        self.is_paused = False
        self.cifrao = "$"
        self.connection_manager = None
        self.news_update_thread = None
        self.stop_news_update_event = threading.Event()
        
        self.operacoes_em_andamento = {}
        self.news_events = []
        
        # --- Gerenciadores de Risco ---
        self.masaniello_manager = None
        self.cycle_manager = CycleManager(self.config, self.log_callback)
        self.active_manager = 'cycle' # 'cycle' ou 'masaniello'
        # ------------------------------------------------

        self._carregar_config()

    def reset_state(self):
        """Reseta as variáveis de estado do robô para um novo ciclo de operações."""
        logging.info("Estado do bot_core resetado para nova sessão.")
        self.lucro_total = 0.0
        self.stop = True
        if self.cycle_manager:
            self.cycle_manager.reset()
        # O Masaniello é instanciado novamente a cada início, então não precisa de reset aqui.

    def reload_config(self, new_config):
        """Atualiza as configurações internas com novos valores do banco de dados."""
        self.config = new_config
        self._carregar_config()
        if self.cycle_manager:
            self.cycle_manager.reload_config(new_config)
        logging.info("Configurações do bot_core recarregadas a partir da UI.")

    def _carregar_config(self):
        logging.info("Carregando configurações do robô.")
        
        def safe_float(key, default):
            value = self.config.get(key)
            try: return float(value)
            except (ValueError, TypeError): return default

        def safe_int(key, default):
            value = self.config.get(key)
            try: return int(float(value))
            except (ValueError, TypeError): return default

        self.stop_win = safe_float('stop_win', 100.0)
        self.stop_loss = safe_float('stop_loss', 100.0)
        
        # --- Adicione esta linha para compatibilidade ---
        self.valor_entrada_inicial = safe_float('valor_entrada', 1.0)
        # -------------------------------------------------

        self.usar_filtro_noticias = self.config.get('usar_filtro_noticias', 'S').upper() == 'S'
        self.minutos_antes_noticia = safe_int('minutos_antes_noticia', 15)
        self.minutos_depois_noticia = safe_int('minutos_depois_noticia', 15)
    

    def set_active_manager(self, mode, manager_instance=None):
        """
        Define o modo de gerenciamento de capital a ser usado pelo robô.
        'cycle' ou 'masaniello'
        """
        self.active_manager = mode
        if mode == 'masaniello' and manager_instance:
            self.masaniello_manager = manager_instance
            self.log_callback(f"Modo de gerenciamento definido para: Masaniello", "CONFIG")
        else:
            self.masaniello_manager = None
            self.log_callback(f"Modo de gerenciamento definido para: Ciclos", "CONFIG")

    
    
    def set_pause_status(self, is_paused: bool):
        self.is_paused = is_paused
        status = "PAUSADO" if is_paused else "REATIVADO"
        self.log_callback(f"Robô {status}", "STATUS")
        logging.info(f"Status do robô alterado para: {status}")

    def resolver_ativo_correto(self, ativo_sinal, lista_de_ativos_abertos):
        """
        Recebe o nome do ativo do sinal e busca o nome negociável correto na lista de ativos abertos.
        Retorna o nome correto do ativo ou None se não encontrar.
        """
        
        # Prioridade 1: Busca por correspondência exata
        if ativo_sinal in lista_de_ativos_abertos:
            self.log_callback(f"Ativo '{ativo_sinal}' encontrado com nome exato.", "INFO")
            return ativo_sinal

        # Prioridade 2: Busca por variações que começam com o nome do sinal
        # Ex: Sinal "EURUSD-OTC" pode encontrar o ativo "EURUSD-OTC-L"
        for ativo_aberto in lista_de_ativos_abertos:
            if ativo_aberto.startswith(ativo_sinal):
                self.log_callback(f"Ativo para '{ativo_sinal}' resolvido como '{ativo_aberto}'.", "INFO")
                return ativo_aberto
        
        # Se o sinal for normal (sem -OTC), podemos adicionar uma busca por variações como "-op"
        if "-OTC" not in ativo_sinal:
            variacao_op = f"{ativo_sinal}-op"
            if variacao_op in lista_de_ativos_abertos:
                self.log_callback(f"Ativo para '{ativo_sinal}' resolvido como '{variacao_op}'.", "INFO")
                return variacao_op

        # Se nada foi encontrado
        self.log_callback(f"Nenhuma variação negociável encontrada para o ativo '{ativo_sinal}'.", "AVISO")
        return None

    def _get_best_digital_asset(self):
        try:
            all_assets = self.api.get_all_open_time()
            if 'digital' not in all_assets:
                self.log_callback("Nenhum ativo digital aberto no momento.", "AVISO")
                return None, 0

            open_digital_assets = {asset: details for asset, details in all_assets['digital'].items() if details.get('open', False)}
            
            best_asset = None
            highest_payout = 0

            for asset_name in open_digital_assets:
                payout = self.api.get_digital_payout(asset_name)
                if payout > highest_payout:
                    highest_payout = payout
                    best_asset = asset_name
            
            if best_asset:
                self.log_callback(f"Ativo digital com maior payout encontrado: {best_asset} ({highest_payout}%)", "INFO")
                return best_asset, highest_payout
            else:
                self.log_callback(f"Não foi possível encontrar um ativo digital aberto.", "AVISO")
                return None, 0

        except Exception as e:
            self.log_callback(f"Erro ao buscar o melhor ativo digital: {e}", "ERRO")
            return None, 0


    def executar_trade(self, ativo_sinal, direcao, timeframe, context=None):
        if self.stop is False or self.is_paused:
            self.log_callback("Trade ignorado: Robô pausado ou parado.", "AVISO")
            return

        if not self.api or not self.api.check_connect():
            self.log_callback("Trade ignorado: A conexão com a IQ Option não está ativa.", "ERRO")
            return

        ativo_real_para_operar = None
        
        # Checa se deve usar a lógica de maior payout para digitais
        if self.config.get('usar_maior_payout_digital', False):
            ativo_real_para_operar, payout = self._get_best_digital_asset()
            if ativo_real_para_operar:
                self.log_callback(f"Operando no ativo de maior payout: {ativo_real_para_operar} com {payout}% de payout.", "INFO")
        else:
            # Lógica existente para resolver o ativo
            try:
                # A lista de ativos abertos deve incluir tanto binárias quanto digitais
                all_open = self.api.get_all_open_time()
                lista_ativos_abertos = list(all_open.get('binary', {}).keys()) + list(all_open.get('digital', {}).keys())
                ativo_real_para_operar = self.resolver_ativo_correto(ativo_sinal, lista_ativos_abertos)
            except Exception as e:
                self.log_callback(f"Erro ao obter lista de ativos abertos da API: {e}", "ERRO")
                return

        if not ativo_real_para_operar:
            self.log_callback(f"Operação para {ativo_sinal} abortada: ativo não está aberto ou não foi encontrado.", "AVISO")
            return

        if self.operacoes_em_andamento.get(ativo_real_para_operar, False):
            self.log_callback(f"Trade ignorado: Já existe uma operação em andamento para {ativo_real_para_operar}.", "AVISO")
            return

        def executar_martingale():
            entry_value = 0
            manager_name = "N/A"
            should_record_trade = True
            while True:
                # 1. Obter valor da entrada do gerenciador ativo
                if self.active_manager == 'cycle':
                    if self.config.get('usar_ciclos', 'S') == 'S':
                        manager_name = "Ciclos"
                        entry_value = self.cycle_manager.get_next_entry_value()
                    else:
                        manager_name = "Fixo"
                        entry_value = float(self.config.get('valor_entrada', 1.0))
                        should_record_trade = False # Não registra no gerenciador de ciclo
                elif self.active_manager == 'masaniello' and self.masaniello_manager:
                    manager_name = "Masaniello"
                    entry_value = self.masaniello_manager.get_next_entry_value()

                if entry_value <= 0:
                    self.log_callback(f"Gerenciador ({manager_name}) finalizou o ciclo ou retornou valor de entrada inválido. Trade não executado.", "INFO")
                    self.stop = False # Se o gerenciador parou, paramos o bot
                    break

                self.operacoes_em_andamento[ativo_real_para_operar] = True

                # 2. Executar a ordem
                self.log_callback(f'Ordem enviada: {ativo_real_para_operar} {direcao.upper()} | {self.cifrao}{entry_value:.2f} | Gerenciador: {manager_name}', "TRADE")

                check, trade_id = False, None
                try:
                    check, trade_id = self.api.buy(entry_value, ativo_real_para_operar, direcao, timeframe, timeout=15)
                    if not check and trade_id == "Timeout":
                        self.log_callback(f"A ordem para {ativo_real_para_operar} não pôde ser confirmada a tempo (timeout de 15s).", "ERRO")
                        # Lógica para lidar com o timeout, talvez pular para o próximo sinal ou tentar novamente.
                        self.operacoes_em_andamento[ativo_real_para_operar] = False
                        break # Sai do loop de martingale para este sinal

                except Exception as api_buy_error:
                    self.log_callback(f"API Error on buy for {ativo_real_para_operar}: {api_buy_error}", "ERRO")
                    check = False

                if not check:
                    self.log_callback(f"Ordem foi rejeitada pela corretora para {ativo_real_para_operar}. Verifique se o ativo está aberto.", "ERRO")
                    self.operacoes_em_andamento[ativo_real_para_operar] = False
                    break

                # 3. Aguardar e processar resultado
                lucro = self._aguardar_e_processar_resultado(trade_id, 'binary', '', timeframe)

                if lucro is None: # Erro na API ao buscar resultado
                    self.operacoes_em_andamento[ativo_real_para_operar] = False
                    break

                # 4. Registrar resultado no gerenciador, se aplicável
                if should_record_trade:
                    if self.active_manager == 'cycle':
                        self.cycle_manager.record_trade(lucro, entry_value)
                    elif self.active_manager == 'masaniello' and self.masaniello_manager:
                        self.masaniello_manager.record_trade(entry_value, lucro)

                # 5. Enviar resultado para a UI
                resultado_final = {"profit": lucro, "entry_value": entry_value, "context": context, "foi_executado": True}
                self.trade_result_callback(resultado_final)

                # 6. Checar Stop Win/Loss global
                self.check_stop()

                # 7. Se for WIN ou ciclo/martingale acabou, parar. Se for LOSS e ainda há martingale, repetir.
                if self.active_manager == 'cycle' and lucro <= 0 and self.cycle_manager.is_active and self.cycle_manager.current_martingale_level > 0 and self.cycle_manager.current_martingale_level <= self.cycle_manager.martingale_levels:
                    continue
                break

            self.operacoes_em_andamento[ativo_real_para_operar] = False

        try:
            executar_martingale()
        except WebSocketConnectionClosedException:
            self.log_callback("ERRO CRÍTICO: Conexão perdida durante a execução do trade.", "ERRO")
            logging.critical(f"WebSocketConnectionClosedException em executar_trade para o ativo {ativo_sinal}", exc_info=True)
        except Exception as e:
            self.log_callback(f"ERRO CRÍTICO EM EXECUTAR_TRADE: {e}", "ERRO")
            logging.critical(f"ERRO CRÍTICO em executar_trade para o ativo {ativo_sinal}", exc_info=True)

    


    def connect(self, *args, **kwargs):
        self.log_callback("Conectando à IQ Option...", "INFO")
        logging.info("Iniciando conexão com a API IQ Option...")
        try:
            self.api = IQ_Option(self.credentials['email'], self.credentials['senha'])
            self.log_callback("Instância da API criada.", "DEBUG")
            check, reason = self.api.connect()
            self.log_callback(f"Resultado da conexão: {check}, Motivo: {reason}", "DEBUG")
        except Exception as e:
            self.log_callback(f'Exceção ao criar API ou conectar: {e}', "ERRO")
            logging.error(f"Exceção ao criar API ou conectar: {e}")
            self.status_callback("IQ", "ERRO", "Exceção na conexão")
            return False
        if not check:
            self.log_callback(f'Falha na conexão: {reason}', "ERRO")
            logging.error(f"Falha ao conectar na IQ Option. Razão: {reason}")
            self.status_callback("IQ", "ERRO", "Falha na Conexão")
            return False
        try:
            self.log_callback('Conectado com sucesso!', "INFO")
            logging.info("Conexão com a IQ Option estabelecida com sucesso.")
            self.api.change_balance(self.credentials['conta'])
            self.cifrao = self.api.get_profile_ansyc()['currency_char']
            self._fetch_and_send_open_pairs()
            
            # Inicia o ConnectionManager
            self.connection_manager = ConnectionManager(self.api, self.log_callback, self.status_callback)
            self.connection_manager.start()

            self.start_news_updater()
        except Exception as e:
            self.log_callback(f'Exceção após conectar: {e}', "ERRO")
            logging.error(f"Exceção após conectar: {e}")
            self.status_callback("IQ", "ERRO", "Exceção pós-conexão")
            return False
        return True

    def disconnect(self):
        if self.connection_manager:
            self.connection_manager.stop()
        self.stop_news_updater()
        self.log_callback("Conexão com a IQ Option encerrada.", "INFO")
        logging.info("Conexão com a IQ Option finalizada.")

    def start_news_updater(self):
        """Inicia a thread que atualiza as notícias periodicamente."""
        self.stop_news_update_event.clear()
        self.news_update_thread = threading.Thread(target=self._news_updater_loop)
        self.news_update_thread.daemon = True
        self.news_update_thread.start()

    def stop_news_updater(self):
        """Para a thread de atualização de notícias."""
        self.stop_news_update_event.set()
        if self.news_update_thread:
            self.news_update_thread.join(timeout=2)

    def _news_updater_loop(self):
        """Loop que chama a busca por notícias a cada 4 horas."""
        while not self.stop_news_update_event.is_set():
            self._carregar_noticias_do_dia()
            # Espera 4 horas (14400 segundos) para a próxima atualização
            self.stop_news_update_event.wait(timeout=14400) 

    def _carregar_noticias_do_dia(self):
        logging.info("Iniciando busca por notícias econômicas do dia...")
        self.news_events = fetch_structured_news()
        if self.news_events:
            self.log_callback(f"{len(self.news_events)} notícias de impacto encontradas para hoje.", "INFO")
            logging.info(f"{len(self.news_events)} notícias de impacto encontradas.")
        else:
            self.log_callback("Nenhuma notícia de impacto encontrada ou falha na busca.", "AVISO")
            logging.warning("Nenhuma notícia de impacto encontrada.")

    def _is_safe_to_trade(self, ativo):
        if not self.usar_filtro_noticias:
            return True
        try:
            moedas_do_par = [ativo[:3], ativo[3:6]] if len(ativo) >= 6 else [ativo]
            agora = datetime.now()
            for noticia in self.news_events:
                if noticia['currency'].upper() in [m.upper() for m in moedas_do_par]:
                    hora_noticia_str = noticia['time']
                    hora_noticia = datetime.strptime(hora_noticia_str, "%H:%M").replace(year=agora.year, month=agora.month, day=agora.day)
                    inicio_bloqueio = hora_noticia - timedelta(minutes=self.minutos_antes_noticia)
                    fim_bloqueio = hora_noticia + timedelta(minutes=self.minutos_depois_noticia)
                    if inicio_bloqueio <= agora <= fim_bloqueio:
                        msg = f"Trade em {ativo} bloqueado por notícia de {noticia['impact']} touros para {noticia['currency']} às {hora_noticia_str}."
                        self.log_callback(msg, "AVISO")
                        logging.warning(msg)
                        return False
        except Exception as e:
            logging.error(f"Erro no filtro de notícias: {e}")
            return True
        return True

    def _fetch_and_send_open_pairs(self):
        self.log_callback("Buscando lista de ativos abertos...", "INFO")
        logging.info("Buscando lista de ativos abertos na IQ Option.")
        try:
            all_assets = self.api.get_all_open_time()
            open_pairs = {asset for asset_type in ['turbo', 'binary'] if asset_type in all_assets for asset, details in all_assets[asset_type].items() if details.get('open', False)}
            sorted_pairs = sorted(list(open_pairs))
            self.pair_list_callback(sorted_pairs)
        except Exception as e:
            self.log_callback(f"Erro ao buscar lista de ativos: {e}", "ERRO")
            logging.error(f"Erro ao buscar lista de ativos: {e}", exc_info=True)
            self.pair_list_callback([])

    def check_stop(self):
        if self.lucro_total <= -abs(self.stop_loss):
            self.stop = False
            msg = f'STOP LOSS ATINGIDO: {self.cifrao}{self.lucro_total:.2f}'
            self.log_callback(msg, "STOP"); logging.warning(msg)
        if self.lucro_total >= abs(self.stop_win):
            self.stop = False
            msg = f'STOP WIN ATINGIDO: {self.cifrao}{self.lucro_total:.2f}'
            self.log_callback(msg, "STOP"); logging.info(msg)
            

    def _aguardar_e_processar_resultado(self, trade_id, tipo_final, msg_gale, timeframe=1):
        resultado = None
        tempo_max_espera = 40 + int(timeframe)
        tempo_esperado = 0
        while True:
            if self.connection_manager and self.connection_manager.stop_event.is_set():
                break
            try:
                if tipo_final == 'digital':
                    status, res = self.api.check_win_digital_v2(trade_id)
                else:
                    status, res = self.api.check_win_v4(trade_id)
                if status:
                    resultado = res
                    break
                time.sleep(1.0)
                tempo_esperado += 1
                if tempo_esperado >= tempo_max_espera:
                    self.log_callback(f"Timeout: Não foi possível obter resultado para o trade ID {trade_id} após {tempo_max_espera}s (timeframe {timeframe}).", "ERRO")
                    logging.error(f"Timeout: Resultado NULO para trade ID {trade_id}")
                    resultado = -1  # Considera como LOSS
                    msg_gale = msg_gale + " | Timeout"
                    break
            except WebSocketConnectionClosedException:
                self.log_callback("Conexão perdida ao verificar resultado. O gerenciador de conexão cuidará da reconexão.", "AVISO")
                logging.warning("Conexão perdida durante a verificação de resultado.")
                # O ConnectionManager vai lidar com a reconexão, então apenas esperamos.
                time.sleep(5) # Espera um pouco antes de tentar novamente

        lucro = round(resultado, 2) if resultado is not None else 0
        self.lucro_total += lucro
        if resultado is None:
            self.log_callback(f"Não foi possível obter resultado para o trade ID {trade_id}", "ERRO")
            logging.error(f"Resultado NULO para trade ID {trade_id}")
            return None
        if lucro > 0:
            msg_log = f'WIN{msg_gale} | Lucro: {self.cifrao}{lucro:+.2f} | Saldo: {self.cifrao}{self.lucro_total:+.2f}'
            self.log_callback(msg_log, "WIN")
            logging.info(f"RESULTADO: WIN, Lucro={self.cifrao}{lucro:+.2f}, Saldo Parcial={self.cifrao}{self.lucro_total:+.2f}")
        else:
            msg = 'EMPATE' if lucro == 0 else 'LOSS'
            msg_log = f'{msg}{msg_gale} | Prejuízo: {self.cifrao}{lucro:.2f} | Saldo: {self.cifrao}{self.lucro_total:+.2f}'
            self.log_callback(msg_log, "LOSS" if msg == 'LOSS' else "INFO")
            logging.warning(f"RESULTADO: {msg}, Prejuízo={self.cifrao}{lucro:.2f}, Saldo Parcial={self.cifrao}{self.lucro_total:+.2f}")
        return lucro


