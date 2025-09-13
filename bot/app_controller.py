# bot/app_controller.py

import logging
import threading
import zmq
from .bot_core import IQBotCore
from .strategies.mt4_strategy import MT4Strategy
from .strategies.mhi_strategy import MHIStrategy
from .strategies.signal_list_strategy import SignalListStrategy
from .management.masaniello_manager import MasanielloManager
from ui.components.news_scraper import fetch_structured_news
from utils.path_resolver import resource_path

class AppController:
    """A classe controladora que gerencia a lógica do aplicativo e a comunicação entre a UI e o BotCore."""
    def __init__(self, credentials, config_manager, trade_logger):
        self.credentials = credentials
        self.config_manager = config_manager
        self.trade_logger = trade_logger # Store trade_logger
        self.bot_core = None
        self.ui_callbacks = {}
        self.strategy = None

        # Adiciona um handler ao trade_logger para enviar mensagens para a UI
        class UILogHandler(logging.Handler):
            def __init__(self, ui_callback_method):
                super().__init__()
                self.ui_callback_method = ui_callback_method
            def emit(self, record):
                self.ui_callback_method(self.format(record), tag="TRADE")
        
        self.trade_logger.addHandler(UILogHandler(self._handle_log))
        self.trade_logger.propagate = False # Garante que não duplique logs se o root logger também tiver um handler de console
        self.masaniello_manager = None
        self.zmq_context = zmq.Context()
        self.robot_stats = { 'is_active': False, 'is_paused': False, 'balance': 0.0, 'today_profit': 0.0, 'wins': 0, 'losses': 0, 'cifrao': ''}

    def start_bot(self, strategy_name, selected_pair, signals):
        if self.strategy and self.strategy.is_alive(): return
        if not self.bot_core or not self.bot_core.is_connected:
            self._handle_log("Conexão com a IQ Option não está ativa.", "AVISO")
            return

        self.stop_bot(silent=True)
        self._reset_stats()
        self._handle_log("Iniciando nova sessão de operações...", "SISTEMA")

        # Configura o gerenciamento (Masaniello ou Ciclos)
        self._setup_management()

        self.bot_core.start_background_worker()

        # Cria e inicia a estratégia
        if strategy_name == "MHI (Minoria)" and ("Conecte" in selected_pair or "Nenhum" in selected_pair):
            self.ui_callbacks.get('show_popup', lambda x, y: None)("Aviso", "Para MHI, selecione um par válido.")
            return
        
        strategy_map = {
            "Lista de Sinais": (SignalListStrategy, (self.bot_core, signals, self._handle_status_update)),
            "Sinal MT4": (MT4Strategy, (self.bot_core, self.zmq_context, self._handle_status_update)),
            "MHI (Minoria)": (MHIStrategy, (self.bot_core, selected_pair))
        }

        if strategy_name in strategy_map:
            if strategy_name == "Lista de Sinais" and not signals:
                self.ui_callbacks.get('show_popup', lambda x, y: None)("Erro", "Nenhum arquivo de sinais foi carregado.")
                return
            
            strategy_class, args = strategy_map[strategy_name]
            self.strategy = strategy_class(*args)

        if self.strategy:
            self.strategy.start()
            self._handle_log("Robô Iniciado.", "STATUS")
            self.robot_stats['is_active'] = True
            self.robot_stats['is_paused'] = False
            self.ui_callbacks.get('update_robot_status', lambda x, y: None)(True, False)
            self._update_strategy_status_bar()

    def stop_bot(self, silent=False):
        if self.strategy: 
            self.strategy.stop()
            self.strategy = None
        if self.bot_core:
            self.bot_core.stop_background_worker()
        
        self.robot_stats['is_active'] = False
        self.robot_stats['is_paused'] = False
        if self.bot_core: self.bot_core.is_paused = False
        
        if not silent:
            self._handle_log("Robô Desativado.", "STATUS")
        
        self.ui_callbacks.get('update_robot_status', lambda x, y: None)(False, False)
        self._update_strategy_status_bar()

    def pause_bot(self):
        if not self.robot_stats['is_active']: return
        new_pause_state = not self.robot_stats.get('is_paused', False)
        self.robot_stats['is_paused'] = new_pause_state
        if self.bot_core: self.bot_core.set_pause_status(new_pause_state)
        self.ui_callbacks.get('update_robot_status', lambda x, y: None)(True, new_pause_state)

    def restart_bot(self):
        self._handle_log("Robô Resetado. Limpando sessão...", "STATUS")
        self.stop_bot(silent=True)
        self._reset_stats()
        self.ui_callbacks.get('clear_trade_history', lambda: None)()
        self.ui_callbacks.get('clear_signal_list', lambda: None)()
        self._handle_log("Sessão reiniciada. Pronto para começar.", "SISTEMA")

    def on_settings_saved(self):
        self._handle_log("Configurações salvas. Recarregando lógica do robô...", "CONFIG")
        all_settings = self.config_manager.get_all_settings()
        if self.bot_core:
            self.bot_core.reload_config(all_settings)
        self._handle_log("Lógica do robô atualizada com as novas configurações.", "CONFIG")

    def request_initial_dashboard_data(self):
        # Send current robot stats to update metric cards
        self.ui_callbacks.get('update_metric_cards', lambda x: None)(self._get_summary_data())
        
        # Send current robot status
        self.ui_callbacks.get('update_robot_status', lambda x, y: None)(self.robot_stats['is_active'], self.robot_stats['is_paused'])

    def fetch_news(self, callback):
        """Busca notícias em uma thread separada e as retorna via callback."""
        def task():
            # Informa à UI que a busca começou, usando o próprio callback
            if callback:
                callback([{"impact": 0, "time": "", "currency": "🔄", "event": "Buscando notícias..."}])
            
            news_data = fetch_structured_news()
            
            # Envia os dados (ou uma lista vazia) de volta para a UI
            if callback:
                callback(news_data or [])

        threading.Thread(target=task, daemon=True).start()

    def export_pairs_for_mt4(self, pairs_to_export, selected_filter):
        filename = resource_path("mt4_pares.txt")
        try:
            with open(filename, 'w') as f: 
                for pair in pairs_to_export: f.write(f"{pair}\n")
            self.ui_callbacks.get('show_popup', lambda x, y: None)("Sucesso", f"'mt4_pares.txt' exportado com {len(pairs_to_export)} pares.")
            self._handle_log(f"Lista de {len(pairs_to_export)} pares ({selected_filter}) exportada.", "INFO")
        except Exception as e:
            self.ui_callbacks.get('show_popup', lambda x, y: None)("Erro de Arquivo", f"Não foi possível salvar:\n{e}")

    def shutdown(self):
        self.stop_bot(silent=True)
        if self.bot_core:
            self.bot_core.disconnect()
        self.zmq_context.term()

    # --- Métodos Internos e Handlers de Callback ---

    def _handle_log(self, message, tag="INFO"):
        self.ui_callbacks.get('log_message', lambda x, y: None)(message, tag)

    def _handle_trade_result(self, result_info):
        if result_info.get("foi_executado", False):
            profit = result_info.get("profit", 0)
            self.robot_stats['today_profit'] += profit
            if profit > 0: self.robot_stats['wins'] += 1
            elif profit < 0: self.robot_stats['losses'] += 1

        trade_details = {
            'ativo': result_info.get('ativo', 'N/A'),
            'direcao': self.strategy.last_trade_direction if self.strategy else 'N/A',
            'valor': result_info.get('entry_value', 0),
            'resultado': 'WIN' if result_info.get("profit", 0) > 0 else 'LOSS' if result_info.get("profit", 0) < 0 else 'EMPATE',
            'lucro': result_info.get("profit", 0),
            'cifrao': self.robot_stats['cifrao'],
            'context': result_info.get('context', {})
        }

        if self.bot_core and self.bot_core.active_manager == 'masaniello' and self.bot_core.masaniello_manager:
            trade_details['masaniello_status'] = self.bot_core.masaniello_manager.get_status()

        self.ui_callbacks.get('on_trade_result', lambda x: None)(trade_details)
        self.ui_callbacks.get('update_metric_cards', lambda x: None)(self._get_summary_data())
        self._update_strategy_status_bar()

    def _handle_pair_list_update(self, pairs):
        all_pairs = sorted(list(pairs))
        normal_pairs = sorted([p for p in all_pairs if not p.endswith('-OTC')])
        otc_pairs = sorted([p for p in all_pairs if p.endswith('-OTC')])
        self.ui_callbacks.get('on_pair_list_update', lambda x: None)((all_pairs, normal_pairs, otc_pairs))

    def _handle_status_update(self, component, status, message):
        self.ui_callbacks.get('update_connection_status', lambda a, b, c: None)(component, status, message)

    def _update_strategy_status_bar(self):
        manual_active = isinstance(self.strategy, MHIStrategy)
        signallist_active = isinstance(self.strategy, SignalListStrategy)
        self._handle_status_update("MANUAL", "CONECTADO" if manual_active else "PARADO", "Ativa" if manual_active else "Inativa")
        self._handle_status_update("SIGNALLIST", "CONECTADO" if signallist_active else "PARADO", "Ativa" if signallist_active else "Inativa")

    def _reset_stats(self):
        if self.bot_core: self.bot_core.reset_state()
        self.robot_stats['today_profit'] = 0.0
        self.robot_stats['wins'] = 0
        self.robot_stats['losses'] = 0
        self.ui_callbacks.get('update_metric_cards', lambda x: None)(self._get_summary_data())

    def _get_summary_data(self):
        stats = self.robot_stats
        total_ops = stats['wins'] + stats['losses']
        win_rate = (stats['wins'] / total_ops) * 100 if total_ops > 0 else 0
        return {
            'balance': stats.get('balance', 0),
            'pl_today': stats.get('today_profit', 0),
            'wins': stats.get('wins', 0),
            'losses': stats.get('losses', 0),
            'winrate': win_rate,
            'cifrao': stats.get('cifrao', '$')
        }

    def _setup_management(self):
        get_configs = self.ui_callbacks.get('get_masaniello_configs', lambda: None)
        masaniello_configs = get_configs()
        if masaniello_configs:
            try:
                self.masaniello_manager = MasanielloManager(**masaniello_configs)
                self.bot_core.set_active_manager('masaniello', self.masaniello_manager)
                self._handle_log("Iniciando com Gerenciamento Masaniello!", "INFO")
            except Exception as e:
                self.ui_callbacks.get('show_popup', lambda x, y: None)("Erro de Configuração", f"Verifique os valores de Masaniello: {e}")
                return False
        else:
            self.bot_core.set_active_manager('cycle')
            self._handle_log("Iniciando com Gerenciamento Normal/Ciclos!", "INFO")
        return True

    def set_ui_callbacks(self, callbacks):
        self.ui_callbacks = callbacks

    def connect(self):
        if self.bot_core: return
        config_dict = self.config_manager.get_all_settings()
        self.bot_core = IQBotCore(
            credentials=self.credentials, config=config_dict,
            log_callback=self._handle_log, trade_logger=self.trade_logger, trade_result_callback=self._handle_trade_result,
            pair_list_callback=self._handle_pair_list_update, status_callback=self._handle_status_update
        )
        
        if self.bot_core.connect():
            self.robot_stats['balance'] = self.bot_core.api.get_balance()
            self.robot_stats['cifrao'] = self.bot_core.cifrao
            self.ui_callbacks.get('update_metric_cards', lambda x: None)(self._get_summary_data())
            self.ui_callbacks.get('update_robot_status', lambda x, y: None)(False, False)
 