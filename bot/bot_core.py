# bot/bot_core.py

import time
import threading
import logging
from datetime import datetime, timedelta
from iqoptionapi.stable_api import IQ_Option
from websocket._exceptions import WebSocketConnectionClosedException
from ui.components.news_scraper import fetch_structured_news
from .management.masaniello_manager import MasanielloManager

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
        self.heartbeat_thread = None
        self.stop_heartbeat_event = threading.Event()
        
        self.operacoes_em_andamento = {}
        self.news_events = []
        
        # Gerenciamento de Capital
        self.management_mode = 'normal'
        self.masaniello_manager = None
        self.ciclo_recuperacao = {'ativo': False, 'perda_acumulada': 0.0, 'nivel_atual': 0}
        
        self._carregar_config()

    def reset_state(self):
        """Reseta as variáveis de estado do robô para um novo ciclo de operações."""
        logging.info("Estado do bot_core resetado para nova sessão.")
        self.lucro_total = 0.0
        self.stop = True
        self.em_modo_recuperacao = False # Mantido por compatibilidade, mas a lógica usa ciclo_recuperacao
        self.prejuizo_a_recuperar = 0.0 # Mantido por compatibilidade
        self.ciclo_recuperacao = {'ativo': False, 'perda_acumulada': 0.0, 'nivel_atual': 0}
        
        if self.usar_masaniello:
            self._carregar_config()

    def reload_config(self, new_config):
        """Atualiza as configurações internas com novos valores do banco de dados."""
        self.config = new_config
        self._carregar_config()
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

        self.valor_entrada_inicial = safe_float('valor_entrada', 5.0)
        self.stop_win = safe_float('stop_win', 100.0)
        self.stop_loss = safe_float('stop_loss', 100.0)
        
        self.usar_martingale = self.config.get('usar_martingale', 'S').upper() == 'S'
        self.niveis_martingale = safe_int('niveis_martingale', 1)
        self.fator_martingale = safe_float('fator_martingale', 2.1)

        self.usar_ciclos = self.config.get('gerenciamento_ciclos', 'S').upper() == 'S'
        self.ciclos_niveis = int(self.config.get('ciclos_niveis', '2'))
        self.ciclos_payout_recuperacao = safe_float('ciclos_payout_recuperacao', 87.0) / 100.0

        self.usar_masaniello = self.config.get('usar_masaniello', 'N').upper() == 'S'
        if self.usar_masaniello:
            try:
                capital = safe_float('masaniello_capital', 100.0)
                num_trades = safe_int('masaniello_num_trades', 10)
                expected_wins = safe_int('masaniello_wins_esperados', 7)
                payout = safe_float('masaniello_payout', 87.0)
                
                if not all([capital > 0, num_trades > 0, expected_wins > 0, payout > 0, expected_wins <= num_trades]):
                    raise ValueError("Parâmetros do Masaniello inválidos.")
                
                self.masaniello_manager = MasanielloManager(capital=capital, num_trades=num_trades, expected_wins=expected_wins, payout=payout)
            except Exception as e:
                logging.error(f"Erro ao inicializar Masaniello: {e}")
                self.log_callback("Erro nos parâmetros do Masaniello. Verifique e salve novamente.", "ERRO")
                self.usar_masaniello = False
                self.masaniello_manager = None
        else:
            self.masaniello_manager = None

        self.usar_filtro_noticias = self.config.get('usar_filtro_noticias', 'S').upper() == 'S'
        self.minutos_antes_noticia = safe_int('minutos_antes_noticia', 15)
        self.minutos_depois_noticia = safe_int('minutos_depois_noticia', 15)
    
    def set_pause_status(self, is_paused: bool):
        self.is_paused = is_paused
        status = "PAUSADO" if is_paused else "REATIVADO"
        self.log_callback(f"Robô {status}", "STATUS")
        logging.info(f"Status do robô alterado para: {status}")

    def get_entry_value(self):
        if self.usar_masaniello and self.masaniello_manager:
            return self.masaniello_manager.get_next_entry_value()

        if self.ciclo_recuperacao['ativo'] and self.usar_ciclos:
            if self.ciclos_payout_recuperacao <= 0:
                self.log_callback("Payout de recuperação zerado. Usando entrada inicial.", "ERRO")
                return self.valor_entrada_inicial

            entrada_necessaria = self.ciclo_recuperacao['perda_acumulada'] / self.ciclos_payout_recuperacao
            valor_final = entrada_necessaria + (self.valor_entrada_inicial * self.ciclos_payout_recuperacao) # Recupera e busca o lucro de uma mão
            
            self.log_callback(f"Modo Recuperação: Entrada de {self.cifrao}{valor_final:.2f} para recuperar {self.cifrao}{self.ciclo_recuperacao['perda_acumulada']:.2f}", "INFO")
            return valor_final

        return self.valor_entrada_inicial

    def executar_trade(self, ativo, direcao, timeframe, context=None):
        try:
            if not self.stop or self.is_paused: return
            if not self._is_safe_to_trade(ativo): return
            if self.operacoes_em_andamento.get(ativo, False):
                self.log_callback(f"Operação para {ativo} ignorada (simultânea).", "AVISO"); return

            self.operacoes_em_andamento[ativo] = True
            
            entrada_base = self.get_entry_value()
            if entrada_base <= 0:
                self.log_callback(f"Valor de entrada inválido ({entrada_base:.2f}). Operação cancelada.", "AVISO")
                if self.usar_masaniello and self.masaniello_manager and self.masaniello_manager.is_finished:
                    self.log_callback(f"Masaniello: {self.masaniello_manager.result_message}. Robô parado.", "STOP")
                    self.stop = False
                return

            lucro_ciclo_atual = 0.0
            prejuizo_acumulado_ciclo = 0.0
            valor_final_da_entrada = 0.0
            entrada_atual = entrada_base
            ciclo_abortado = False
            
            niveis_gale = self.niveis_martingale if self.usar_martingale and not self.usar_masaniello and not self.ciclo_recuperacao['ativo'] else 0

            for i in range(niveis_gale + 1):
                if not self.stop: break
                
                valor_final_da_entrada = entrada_atual
                msg_gale = f' (Gale {i})' if i > 0 else ''
                check, trade_id = self.api.buy(valor_final_da_entrada, ativo, direcao, timeframe)
                
                if not check:
                    self.log_callback(f"Ordem rejeitada{msg_gale} para {ativo}: {trade_id}", "ERRO")
                    lucro_ciclo_atual = 0.0; ciclo_abortado = True; break

                self.log_callback(f'Ordem aberta{msg_gale}: {ativo} {direcao.upper()} | {self.cifrao}{valor_final_da_entrada:.2f}', "TRADE")
                lucro_operacao = self._aguardar_e_processar_resultado(trade_id, 'binary', msg_gale)

                if lucro_operacao is None:
                    lucro_ciclo_atual = 0.0; ciclo_abortado = True; break
                
                lucro_ciclo_atual += lucro_operacao
                if lucro_operacao < 0:
                    prejuizo_acumulado_ciclo += valor_final_da_entrada

                if lucro_operacao > 0: break
                else:
                    if i < niveis_gale: entrada_atual *= self.fator_martingale
                self.check_stop()

            if not ciclo_abortado:
                if self.usar_masaniello and self.masaniello_manager:
                    self.masaniello_manager.update_cycle(lucro_ciclo_atual > 0, valor_final_da_entrada)
                elif self.usar_ciclos:
                    if lucro_ciclo_atual < 0:
                        self.ciclo_recuperacao['ativo'] = True
                        self.ciclo_recuperacao['perda_acumulada'] += prejuizo_acumulado_ciclo
                        self.ciclo_recuperacao['nivel_atual'] += 1
                        self.log_callback(f"Ciclo perdido. Perda acumulada para recuperação: {self.cifrao}{self.ciclo_recuperacao['perda_acumulada']:.2f}", "AVISO")
                        if self.ciclo_recuperacao['nivel_atual'] >= self.ciclos_niveis:
                            self.log_callback(f"Limite de {self.ciclos_niveis} ciclos atingido. Zerando perdas.", "STOP")
                            self.ciclo_recuperacao = {'ativo': False, 'perda_acumulada': 0.0, 'nivel_atual': 0}
                    elif lucro_ciclo_atual > 0 and self.ciclo_recuperacao['ativo']:
                        self.log_callback("Perda anterior recuperada com sucesso!", "WIN")
                        self.ciclo_recuperacao = {'ativo': False, 'perda_acumulada': 0.0, 'nivel_atual': 0}

            resultado_final = {"profit": lucro_ciclo_atual, "entry_value": valor_final_da_entrada, "context": context, "foi_executado": not ciclo_abortado}
            self.trade_result_callback(resultado_final)
        except Exception as e:
            self.log_callback(f"ERRO CRÍTICO EM EXECUTAR_TRADE: {e}", "ERRO")
            logging.critical(f"ERRO CRÍTICO em executar_trade para o ativo {ativo}", exc_info=True)
        finally:
            self.operacoes_em_andamento[ativo] = False
    
    def connect(self, *args, **kwargs):
        self.log_callback("Conectando à IQ Option...", "INFO")
        logging.info("Iniciando conexão com a API IQ Option...")
        self.api = IQ_Option(self.credentials['email'], self.credentials['senha'])
        check, reason = self.api.connect()
        if not check:
            self.log_callback(f'Falha na conexão: {reason}', "ERRO")
            logging.error(f"Falha ao conectar na IQ Option. Razão: {reason}")
            self.status_callback("IQ", "ERRO", "Falha na Conexão")
            return False
            
        self.log_callback('Conectado com sucesso!', "INFO")
        logging.info("Conexão com a IQ Option estabelecida com sucesso.")
        self.api.change_balance(self.credentials['conta'])
        self.cifrao = self.api.get_profile_ansyc()['currency_char']
        self._fetch_and_send_open_pairs()
        self._carregar_noticias_do_dia()
        self.start_heartbeat()
        return True

    def disconnect(self):
        self.stop_heartbeat()
        self.log_callback("Conexão com a IQ Option encerrada.", "INFO")
        logging.info("Conexão com a IQ Option finalizada.")

    def start_heartbeat(self):
        self.stop_heartbeat_event.clear()
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def stop_heartbeat(self):
        self.stop_heartbeat_event.set()
        if self.heartbeat_thread: self.heartbeat_thread.join(timeout=2)
        
    def _heartbeat_loop(self):
        while not self.stop_heartbeat_event.is_set():
            if self.api and self.api.check_connect():
                self.status_callback("IQ", "CONECTADO", "Online")
            else:
                self.status_callback("IQ", "RECONECTANDO", "Conexão perdida...")
                self.log_callback("Conexão com IQ Option perdida! Tentando reconectar...", "AVISO")
                logging.warning("Conexão com IQ Option perdida. Tentando reconectar...")
                check, _ = self.api.connect()
                if check: 
                    self.log_callback("Reconectado com sucesso!", "INFO")
                    logging.info("Reconectado com sucesso à IQ Option.")
                else: 
                    self.log_callback("Falha ao reconectar. Nova tentativa em 10s.", "ERRO")
                    logging.error("Falha ao reconectar na IQ Option.")
            time.sleep(10)
        self.status_callback("IQ", "PARADO", "Desconectado")

    def _carregar_noticias_do_dia(self):
        def run():
            logging.info("Iniciando busca por notícias econômicas do dia...")
            self.news_events = fetch_structured_news()
            if self.news_events:
                self.log_callback(f"{len(self.news_events)} notícias de impacto encontradas para hoje.", "INFO")
                logging.info(f"{len(self.news_events)} notícias de impacto encontradas.")
            else:
                self.log_callback("Nenhuma notícia de impacto encontrada ou falha na busca.", "AVISO")
                logging.warning("Nenhuma notícia de impacto encontrada.")
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

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
            
    def _aguardar_e_processar_resultado(self, trade_id, tipo_final, msg_gale):
        resultado = None
        while True:
            if self.stop_heartbeat_event.is_set(): break
            try:
                if tipo_final == 'digital':
                    status, res = self.api.check_win_digital_v2(trade_id)
                else:
                    status, res = self.api.check_win_v4(trade_id)
                
                if status:
                    resultado = res
                    break
                
                time.sleep(1.0)
                
            except WebSocketConnectionClosedException: 
                self.log_callback("Conexão perdida ao verificar resultado...", "AVISO")
                logging.warning("Conexão perdida durante a verificação de resultado.")
                time.sleep(5)
        
        if resultado is None:
            self.log_callback(f"Não foi possível obter resultado para o trade ID {trade_id}", "ERRO")
            logging.error(f"Resultado NULO para trade ID {trade_id}")
            return None

        lucro = round(resultado, 2)
        self.lucro_total += lucro

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