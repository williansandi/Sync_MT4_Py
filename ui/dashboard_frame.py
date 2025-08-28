# ui/dashboard_frame.py

import customtkinter as ctk
import threading, datetime
from PIL import Image
import zmq
import logging

# --- Imports da Aplicação ---
from utils.config_manager import ConfigManager
from .styles.theme import ModernTheme
from .styles.fonts import AppFonts
from bot.bot_core import IQBotCore
from bot.strategies.mt4_strategy import MT4Strategy
from bot.strategies.mhi_strategy import MHIStrategy
from bot.strategies.signal_list_strategy import SignalListStrategy
from .components.news_scraper import get_formatted_news, fetch_structured_news

# --- Imports dos Componentes de UI e Lógica ---
from .components.financial_summary_card import FinancialSummaryCard
from .components.trade_history import TradeHistoryCard
from .components.news_card import NewsCard
from .signal_list_frame import SignalListFrame
from .management_frame import ManagementFrame
from bot.management.masaniello_manager import MasanielloManager

class ModernDashboardFrame(ctk.CTkFrame):
    def _update_robot_status(self):
        """
        Atualiza o status do robô na interface, incluindo o rodapé de Estratégia Manual e Lista de Sinais.
        """
        if self.robot_stats['is_active']:
            if self.robot_stats['is_paused']:
                self.status_label.configure(text="🟡 PAUSADO", text_color=self.colors.ACCENT_GOLD)
            else:
                self.status_label.configure(text="🟢 ATIVO", text_color=self.colors.ACCENT_GREEN)
        else:
            self.status_label.configure(text="🔴 INATIVO", text_color=self.colors.ACCENT_RED)

        self._update_strategy_status_bar()
    def __init__(self, master, credentials, log_callback, font_family="Arial"):
        super().__init__(master)

        self.log_callback = log_callback

        self.font_family = font_family
        self.colors = ModernTheme
        self.fonts = AppFonts(font_family=self.font_family)
        self.credentials = credentials
        self.config_manager = ConfigManager()
        self.strategy = None
        self.masaniello_manager = None
        self.frames = {}
        self.log_history = []
        self.zmq_context = zmq.Context()
        self.robot_stats = { 'is_active': False, 'is_paused': False, 'balance': 0.0, 'today_profit': 0.0, 'wins': 0, 'losses': 0 }
        self.management_frame_instance = None 
        self.all_pairs = []
        self.normal_pairs = []
        self.otc_pairs = []
        self._setup_ui_layout()
        self.bot_core = self._criar_instancia_bot_core()
        self.after(200, self._conectar_iq_option_thread)
        self._create_all_frames()
        self._show_frame("dashboard")

    def _criar_instancia_bot_core(self):
        config_dict = self.config_manager.get_all_settings()
        return IQBotCore(credentials=self.credentials, config=config_dict, log_callback=self._log_to_gui, trade_result_callback=self._on_trade_result, pair_list_callback=self._on_pair_list_update, status_callback=self._update_connection_status)

    def _on_settings_saved(self):
        """Callback que é chamado quando as configurações são salvas no ManagementFrame."""
        self.log_callback("Configurações salvas. Recarregando lógica do robô...", "CONFIG")
        all_settings = self.config_manager.get_all_settings()
        if self.bot_core:
            self.bot_core.reload_config(all_settings)
        self.log_callback("Lógica do robô atualizada com as novas configurações.", "CONFIG")

    def _on_connection_complete(self, conectado):
        """
        Este método é chamado na thread principal da GUI após a tentativa de conexão.
        É o local seguro para atualizar a interface e registrar o log final.
        """
        if conectado:
            self.robot_stats['balance'] = self.bot_core.api.get_balance()
            self._update_metric_cards()
            self.start_button.configure(state="normal", text="▶️ Iniciar")
        else:
            self.start_button.configure(text="Erro de Conexão")

    def _conectar_iq_option_thread(self):
        self.start_button.configure(state="disabled", text="Conectando...")

        def run_connection():
            conectado = self.bot_core.connect()
            self.after(0, self._on_connection_complete, conectado)
        threading.Thread(target=run_connection, daemon=True).start()

    def _start_bot_clicked(self):
        self.log_callback("1. _start_bot_clicked called", "DEBUG")
        if self.strategy and self.strategy.is_alive(): return

        self.log_callback("2. preparando sinais", "DEBUG")
        strategy_name = self.strategy_option_menu.get()
        selected_pair = self.pair_option_menu.get()
        self.update_idletasks()

        # Capture os sinais SOMENTE SE a estratégia for "Lista de Sinais"
        signals = []
        if strategy_name == "Lista de Sinais":
            signal_list_frame = self.frames.get("lista")
            signals = signal_list_frame.get_signals() if signal_list_frame else []

        self.log_callback("3. restarting bot", "DEBUG")
        # NÃO limpe a lista de sinais ao reiniciar, nem depois de iniciar a estratégia!
        self._stop_bot_clicked()
        if self.bot_core:
            self.bot_core.reset_state()
            self.robot_stats['balance'] = self.bot_core.api.get_balance()
        self.robot_stats['today_profit'] = 0.0
        self.robot_stats['wins'] = 0
        self.robot_stats['losses'] = 0
        if hasattr(self, 'history_card'): self.history_card.clear_list()
        self._update_metric_cards()
        self.log_callback("4. bot restarted", "DEBUG")
        self.log_callback("Iniciando nova sessão de operações...", "SISTEMA")

        self.log_callback(f"Estratégia selecionada: {strategy_name}", "DEBUG")
        self.log_callback(f"Par selecionado: {selected_pair}", "DEBUG")

        management_frame = self.frames.get("management")
        if management_frame:
            self.log_callback("5. management frame found", "DEBUG")
            active_tab = management_frame.tab_view.get()
            if active_tab == "Masaniello":
                try:
                    capital = management_frame.masaniello_widgets['entries']['masaniello_capital'].get()
                    num_trades = management_frame.masaniello_widgets['entries']['masaniello_num_trades'].get()
                    expected_wins = management_frame.masaniello_widgets['entries']['masaniello_wins_esperados'].get()
                    payout = management_frame.masaniello_widgets['entries']['masaniello_payout'].get()
                    self.masaniello_manager = MasanielloManager(capital, num_trades, expected_wins, payout)
                    self.bot_core.set_active_manager('masaniello', self.masaniello_manager)
                    self.log_callback("Iniciando com Gerenciamento Masaniello!", "INFO")
                except Exception as e:
                    self._show_popup("Erro de Configuração", f"Verifique os valores de Masaniello: {e}"); return
            else:
                self.bot_core.set_active_manager('cycle')
                self.log_callback("Iniciando com Gerenciamento Normal/Ciclos!", "INFO")

        if strategy_name == "MHI (Minoria)" and ("Conecte" in selected_pair or "Nenhum" in selected_pair):
            self._show_popup("Aviso", "Para MHI, selecione um par válido."); return
        if strategy_name == "Lista de Sinais":
            if not signals:
                self._show_popup("Erro", "Nenhum arquivo de sinais foi carregado."); return
            self.strategy = SignalListStrategy(self.bot_core, signals, self._update_connection_status)
            # NÃO limpe a lista visual aqui! Deixe os sinais visíveis para status.
        elif strategy_name == "Sinal MT4":
            self.strategy = MT4Strategy(self.bot_core, self.zmq_context, self._update_connection_status)
        elif strategy_name == "MHI (Minoria)":
            self.strategy = MHIStrategy(self.bot_core, selected_pair)

        if self.strategy:
            self.log_callback("6. starting strategy", "DEBUG")
            self.strategy.start()
            self.log_callback("7. strategy started", "DEBUG")
            self.robot_stats['is_active'] = True
            self.robot_stats['is_paused'] = False
            self._update_robot_status()
            self.start_button.configure(state="disabled"); self.stop_button.configure(state="normal"); self.pause_button.configure(state="normal", text="Pausar")
            self.strategy_option_menu.configure(state="disabled"); self.pair_option_menu.configure(state="disabled")

    def _stop_bot_clicked(self):
        if self.strategy:
            self.strategy.stop(); self.strategy = None
        self.robot_stats['is_active'] = False
        self.robot_stats['is_paused'] = False
        if self.bot_core: self.bot_core.set_pause_status(False)
        self._update_robot_status()
        self.start_button.configure(state="normal"); self.stop_button.configure(state="disabled"); self.pause_button.configure(state="disabled", text="Pausar")
        self.strategy_option_menu.configure(state="normal"); self._update_pair_menu()

    def _pause_bot_clicked(self):
        if not self.robot_stats['is_active']: return
        new_pause_state = not self.robot_stats.get('is_paused', False)
        self.robot_stats['is_paused'] = new_pause_state
        if self.bot_core: self.bot_core.set_pause_status(new_pause_state)
        
        self._update_robot_status()

        if new_pause_state:
            self.pause_button.configure(text="Continuar", fg_color=self.colors.ACCENT_GOLD)
        else:
            self.pause_button.configure(text="Pausar", fg_color=self.colors.ACCENT_BLUE)

    def _restart_bot_clicked(self, is_silent=False):
        if not is_silent:
            self._log_to_gui("Reiniciando sessão...", "SISTEMA")
        self._stop_bot_clicked()
        if self.bot_core:
            self.bot_core.reset_state()
            self.robot_stats['balance'] = self.bot_core.api.get_balance()
        self.robot_stats['today_profit'] = 0.0
        self.robot_stats['wins'] = 0
        self.robot_stats['losses'] = 0
        if hasattr(self, 'history_card'): self.history_card.clear_list()
        if self.frames.get("lista"): self.frames["lista"]._clear_signal_list()
        self._update_metric_cards()
        if not is_silent:
            self._log_to_gui("Sessão reiniciada. Pronto para começar.", "SISTEMA")

    def shutdown_completo(self):
        logging.info("Comando de desligamento completo recebido.")
        if self.strategy: self.strategy.stop()
        if self.bot_core: self.bot_core.disconnect()

    def _setup_ui_layout(self):
        self.configure(fg_color=self.colors.BG_PRIMARY); self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(1, weight=1)
        sidebar_frame = ctk.CTkFrame(self, width=200, fg_color=self.colors.BG_CARD, corner_radius=0); sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsew")
        ctk.CTkLabel(sidebar_frame, text="🚀 QUANTUM", font=self.fonts.SIDEBAR_LOGO, text_color=self.colors.ACCENT_BLUE).pack(pady=20, padx=20)
        buttons_info = {"dashboard": "Dashboard", "strategy": "Estratégias", "lista": "Lista de Sinais", "management": "Gerenciamento", "catalog": "Catalogador", "news": "Notícias", "backtest": "Backtest"}
        for name, text in buttons_info.items():
            if name == "backtest":
                ctk.CTkButton(sidebar_frame, text=text, image=None, command=self._abrir_backtest_pyqt, anchor="w", font=self.fonts.SIDEBAR_BUTTON, fg_color="transparent", hover_color=self.colors.BG_SECONDARY, height=40).pack(fill="x", padx=10, pady=5)
            else:
                ctk.CTkButton(sidebar_frame, text=text, image=self._load_icon(name), command=lambda n=name: self._show_frame(n), anchor="w", font=self.fonts.SIDEBAR_BUTTON, fg_color="transparent", hover_color=self.colors.BG_SECONDARY, height=40).pack(fill="x", padx=10, pady=5)
        self._create_header()
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent"); self.main_content_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 10)); self.main_content_frame.grid_rowconfigure(0, weight=1); self.main_content_frame.grid_columnconfigure(0, weight=1)
        self._create_status_bar()

    def _abrir_backtest_pyqt(self):
        import subprocess
        import sys
        import os
        # Caminho absoluto para o script run_backtest.py
        script_path = os.path.join(os.path.dirname(__file__), 'run_backtest.py')
        python_exe = sys.executable
        subprocess.Popen([python_exe, script_path])

    def _create_all_frames(self):
        for frame_name in ["dashboard", "strategy", "lista", "management", "catalog", "news"]:
            frame = None
            if frame_name == "dashboard": frame = self._create_dashboard_frame()
            elif frame_name == "strategy": frame = self._create_strategy_frame()
            elif frame_name == "lista": frame = SignalListFrame(self.main_content_frame)
            elif frame_name == "management":
                frame = ManagementFrame(self.main_content_frame, self.config_manager, save_callback=self._on_settings_saved)
            elif frame_name == "catalog": frame = self._create_catalog_frame()
            elif frame_name == "news": frame = self._create_news_frame()
            self.frames[frame_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

    def _show_frame(self, frame_name_to_show):
        frame = self.frames[frame_name_to_show]; frame.tkraise()

    def _create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color=self.colors.BG_CARD, height=70, corner_radius=10); header_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=10); header_frame.pack_propagate(False)
        ctk.CTkLabel(header_frame, text="Trading Robot Dashboard", font=self.fonts.HEADER_TITLE).pack(side="left", padx=20)
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent"); right_frame.pack(side="right", padx=10)
        self.status_label = ctk.CTkLabel(right_frame, text="🔴 INATIVO", font=(self.font_family, 16, "bold"), text_color=self.colors.ACCENT_RED); self.status_label.pack(side="left", padx=(0, 10))
        self.restart_button = ctk.CTkButton(right_frame, text="🔄 Reiniciar", command=self._restart_bot_clicked, width=100); self.restart_button.pack(side="left", padx=5)
        self.start_button = ctk.CTkButton(right_frame, text="▶️ Iniciar", command=self._start_bot_clicked, width=100); self.start_button.pack(side="left", padx=5)
        self.pause_button = ctk.CTkButton(right_frame, text="Pausar", command=self._pause_bot_clicked, width=100, state="disabled"); self.pause_button.pack(side="left", padx=5)
        self.stop_button = ctk.CTkButton(right_frame, text="⏹️ Parar", command=self._stop_bot_clicked, width=100, state="disabled"); self.stop_button.pack(side="left", padx=5)

    def _on_trade_result(self, result_info):
        profit = result_info.get("profit", 0)
        final_entry_value = result_info.get("entry_value", 0)
        context = result_info.get("context")
        foi_executado = result_info.get("foi_executado", False)

        if context and "signal_id" in context:
            signal_id = context["signal_id"]
            result_info["cifrao"] = self.bot_core.cifrao if self.bot_core else "$"
            signal_list_frame = self.frames.get("lista")
            if signal_list_frame:
                signal_list_frame.update_signal_status(signal_id, result_info)
        
        if self.bot_core and getattr(self.bot_core, 'active_manager', None) == 'masaniello' and self.bot_core.masaniello_manager:
            status = self.bot_core.masaniello_manager.get_status()
            management_frame = self.frames.get("management")
            if management_frame and hasattr(management_frame, 'update_masaniello_status'):
                self.after(0, management_frame.update_masaniello_status, status)
        
        if foi_executado:
            self.robot_stats['today_profit'] += profit
            if profit > 0: self.robot_stats['wins'] += 1
            elif profit < 0: self.robot_stats['losses'] += 1
            
            try:
                if self.bot_core and self.strategy:
                    ativo = getattr(self.strategy, 'last_traded_asset', 'N/A')
                    direcao = getattr(self.strategy, 'last_trade_direction', 'N/A')
                    trade_details = {'ativo': ativo, 'direcao': direcao, 'valor': final_entry_value, 'resultado': 'WIN' if profit > 0 else 'LOSS' if profit < 0 else 'EMPATE', 'lucro': profit, 'cifrao': self.bot_core.cifrao}
                    if hasattr(self, 'history_card'): self.history_card.add_trade(trade_details)
            except Exception as e:
                logging.warning(f"Não foi possível adicionar trade ao histórico: {e}")
        
        self._update_strategy_status_bar()
        self.after(0, self._update_metric_cards)
    
    def _create_dashboard_frame(self):
        frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1); frame.grid_columnconfigure(1, weight=2); frame.grid_rowconfigure(1, weight=1)
        self.summary_card = FinancialSummaryCard(frame, font_family=self.font_family); self.summary_card.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="nsew")
        self.history_card = TradeHistoryCard(frame, font_family=self.font_family); self.history_card.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="nsew")
        activity_frame = ctk.CTkFrame(frame, fg_color=self.colors.BG_CARD, corner_radius=10); activity_frame.grid(row=1, column=0, columnspan=2, padx=0, pady=10, sticky="nsew")
        ctk.CTkLabel(activity_frame, text="🔔 Atividade Recente (Terminal)", font=(self.font_family, 16, "bold")).pack(pady=10, anchor="w", padx=15)
        self.dashboard_console = ctk.CTkTextbox(activity_frame, font=self.fonts.CONSOLE, fg_color=self.colors.BG_SECONDARY, state="disabled", corner_radius=8, border_width=0); self.dashboard_console.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.dashboard_console.configure(state="normal");
        for msg in self.log_history: self.dashboard_console.insert("end", msg)
        self.dashboard_console.see("end"); self.dashboard_console.configure(state="disabled")
        self.after(10, self._update_metric_cards)
        return frame

    def _create_strategy_frame(self):
        frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self._create_page_header(frame, "📊 Gerenciador de Estratégias")
        content_area = ctk.CTkFrame(frame, fg_color="transparent"); content_area.pack(fill="both", expand=True, pady=10); content_area.grid_columnconfigure((0, 1, 2), weight=1)
        config_frame = ctk.CTkFrame(content_area, fg_color=self.colors.BG_CARD, corner_radius=10); config_frame.grid(row=0, column=0, columnspan=3, padx=0, pady=0, sticky="ew")
        ctk.CTkLabel(config_frame, text="Estratégia Principal:", font=self.fonts.CARD_TITLE).grid(row=0, column=0, padx=10, pady=(10,5), sticky="w")
        self.strategy_option_menu = ctk.CTkOptionMenu(config_frame, values=["Sinal MT4", "MHI (Minoria)", "Lista de Sinais"]); self.strategy_option_menu.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
        ctk.CTkLabel(config_frame, text="Tipo de Ativo:", font=self.fonts.CARD_TITLE).grid(row=0, column=1, padx=10, pady=(10,5), sticky="w")
        self.pair_filter_button = ctk.CTkSegmentedButton(config_frame, values=["Normal", "OTC"], command=self._update_pair_menu); self.pair_filter_button.set("Normal"); self.pair_filter_button.grid(row=1, column=1, padx=10, pady=(0,10), sticky="ew")
        ctk.CTkLabel(config_frame, text="Par de Moedas (para MHI):", font=self.fonts.CARD_TITLE).grid(row=0, column=2, padx=10, pady=(10,5), sticky="w")
        self.pair_option_menu = ctk.CTkOptionMenu(config_frame, values=["Aguardando conexão..."], state="disabled"); self.pair_option_menu.grid(row=1, column=2, padx=10, pady=(0,10), sticky="ew")
        return frame
    
    def _create_catalog_frame(self):
        frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self._create_page_header(frame, "📈 Catalogador e Ferramentas")
        content_area = ctk.CTkFrame(frame, fg_color="transparent"); content_area.pack(fill="both", expand=True, pady=10); content_area.grid_columnconfigure(0, weight=1); content_area.grid_rowconfigure(1, weight=1)
        tools_frame = ctk.CTkFrame(content_area, fg_color=self.colors.BG_CARD, corner_radius=10); tools_frame.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        ctk.CTkLabel(tools_frame, text="Ferramentas de Integração MT4", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, padx=10, pady=(10,5))
        self.export_pair_filter = ctk.CTkSegmentedButton(tools_frame, values=["Normal", "OTC", "Ambos"]); self.export_pair_filter.set("Normal"); self.export_pair_filter.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        export_button = ctk.CTkButton(tools_frame, text="✔️ Exportar Pares para MT4", command=self._export_pairs_for_mt4, height=35); export_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        results_frame = ctk.CTkFrame(content_area, fg_color=self.colors.BG_CARD, corner_radius=10); results_frame.grid(row=1, column=0, pady=10, sticky="nsew")
        ctk.CTkLabel(results_frame, text="Resultados da Catalogação aparecerão aqui...", font=self.fonts.BODY_NORMAL).pack(expand=True, padx=20, pady=20)
        return frame

    def _create_news_frame(self):
        frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        header = self._create_page_header(frame, "📰 Central de Notícias"); 
        ctk.CTkButton(header, text="🔄 Atualizar", command=self._start_news_thread, fg_color=self.colors.ACCENT_BLUE, width=140, height=30, corner_radius=8, font=self.fonts.BUTTON).pack(side="right", padx=20, pady=15)
        self.news_card = NewsCard(frame, font_family=self.font_family); self.news_card.pack(fill="both", expand=True, pady=10)
        self._start_news_thread()
        return frame
    
    def _update_metric_cards(self):
        if not hasattr(self, 'summary_card') or not self.summary_card.winfo_exists(): return
        stats = self.robot_stats; total_ops = stats['wins'] + stats['losses']
        win_rate = (stats['wins'] / total_ops) * 100 if total_ops > 0 else 0
        summary_data = {'balance': stats.get('balance', 0), 'pl_today': stats.get('today_profit', 0), 'wins': stats.get('wins', 0), 'losses': stats.get('losses', 0), 'winrate': win_rate, 'cifrao': self.bot_core.cifrao if self.bot_core else "$"}
        self.summary_card.update_summary(summary_data)
        
    def _log_to_gui(self, message, tag=None):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S'); tag_text = f"[{tag}]" if tag else "[*]"
        formatted_message = f"[{timestamp}] {tag_text.ljust(12)} {message}\n"
        self.log_history.append(formatted_message)
        if hasattr(self, 'dashboard_console') and self.dashboard_console.winfo_exists():
            self.after(0, self._update_console, formatted_message)

    def _update_console(self, message):
        if hasattr(self, 'dashboard_console') and self.dashboard_console.winfo_exists():
            self.dashboard_console.configure(state="normal"); self.dashboard_console.insert("end", message); self.dashboard_console.see("end"); self.dashboard_console.configure(state="disabled")

    def _load_icon(self, name, size=(24, 24)):
        try:
            path = f"assets/icons/{name}.png"; return ctk.CTkImage(Image.open(path), size=size)
        except Exception as e:
            logging.warning(f"Ícone não encontrado: {path}. Erro: {e}"); return None
            
    def _create_status_bar(self):
        status_bar_frame = ctk.CTkFrame(self, fg_color=self.colors.BG_CARD, height=30, corner_radius=10); status_bar_frame.grid(row=2, column=1, sticky="ew", padx=10, pady=(0,10)); status_bar_frame.pack_propagate(False)
        self.iq_status_indicator = ctk.CTkLabel(status_bar_frame, text="●", text_color="gray", font=("Arial", 16)); self.iq_status_indicator.pack(side="left", padx=(15, 2), pady=5)
        self.iq_status_label = ctk.CTkLabel(status_bar_frame, text="IQ Option: Aguardando", font=self.fonts.BODY_SMALL, text_color=self.colors.TEXT_MUTED); self.iq_status_label.pack(side="left", pady=5)
        self.mt4_status_indicator = ctk.CTkLabel(status_bar_frame, text="●", text_color="gray", font=("Arial", 16)); self.mt4_status_indicator.pack(side="left", padx=(20, 2), pady=5)
        self.mt4_status_label = ctk.CTkLabel(status_bar_frame, text="MT4: Aguardando", font=self.fonts.BODY_SMALL, text_color=self.colors.TEXT_MUTED); self.mt4_status_label.pack(side="left", pady=5)
        # Novos status: Estratégia Manual e Lista de Sinais
        self.manual_status_indicator = ctk.CTkLabel(status_bar_frame, text="●", text_color="gray", font=("Arial", 16)); self.manual_status_indicator.pack(side="left", padx=(20, 2), pady=5)
        self.manual_status_label = ctk.CTkLabel(status_bar_frame, text="Estratégia Manual: Inativa", font=self.fonts.BODY_SMALL, text_color=self.colors.TEXT_MUTED); self.manual_status_label.pack(side="left", pady=5)
        self.signallist_status_indicator = ctk.CTkLabel(status_bar_frame, text="●", text_color="gray", font=("Arial", 16)); self.signallist_status_indicator.pack(side="left", padx=(20, 2), pady=5)
        self.signallist_status_label = ctk.CTkLabel(status_bar_frame, text="Lista de Sinais: Inativa", font=self.fonts.BODY_SMALL, text_color=self.colors.TEXT_MUTED); self.signallist_status_label.pack(side="left", pady=5)

    def _update_connection_status(self, component, status, message):
        colors = {"CONECTADO": self.colors.ACCENT_GREEN, "RECONECTANDO": self.colors.ACCENT_GOLD, "DESCONECTADO": self.colors.ACCENT_RED, "ERRO": self.colors.ACCENT_RED, "PARADO": "gray"}
        color = colors.get(status, "gray")
        if component == "IQ":
            indicator, label, prefix = self.iq_status_indicator, self.iq_status_label, "IQ Option: "
        elif component == "MT4":
            indicator, label, prefix = self.mt4_status_indicator, self.mt4_status_label, "MT4: "
        elif component == "MANUAL":
            indicator, label, prefix = self.manual_status_indicator, self.manual_status_label, "Estratégia Manual: "
        elif component == "SIGNALLIST":
            indicator, label, prefix = self.signallist_status_indicator, self.signallist_status_label, "Lista de Sinais: "
        else:
            return
        indicator.configure(text_color=color)
        label.configure(text=f"{prefix}{message}")

    def _update_strategy_status_bar(self):
        from bot.strategies.mhi_strategy import MHIStrategy
        from bot.strategies.signal_list_strategy import SignalListStrategy
        manual_active = isinstance(self.strategy, MHIStrategy)
        signallist_active = isinstance(self.strategy, SignalListStrategy)
        if manual_active:
            self._update_connection_status("MANUAL", "CONECTADO", "Ativa")
        else:
            self._update_connection_status("MANUAL", "PARADO", "Inativa")
        if signallist_active:
            self._update_connection_status("SIGNALLIST", "CONECTADO", "Ativa")
        else:
            self._update_connection_status("SIGNALLIST", "PARADO", "Inativa")

    def _create_page_header(self, parent, title):
        header = ctk.CTkFrame(parent, fg_color=self.colors.BG_CARD, corner_radius=10, height=60); header.pack(fill="x")
        header.pack_propagate(False); ctk.CTkLabel(header, text=title, font=self.fonts.PAGE_TITLE).pack(side="left", padx=20, pady=15)
        return header

    def _export_pairs_for_mt4(self):
        if not hasattr(self, 'all_pairs') or not self.all_pairs: self._show_popup("Erro", "Nenhuma lista de pares carregada."); return
        selected_filter = self.export_pair_filter.get()
        if selected_filter == "Normal": pairs_to_export = self.normal_pairs
        elif selected_filter == "OTC": pairs_to_export = self.otc_pairs
        else: pairs_to_export = self.all_pairs
        filename = "mt4_pares.txt"; 
        try:
            with open(filename, 'w') as f:
                for pair in pairs_to_export: f.write(f"{pair}\n")
            self._show_popup("Sucesso", f"'{filename}' exportado com {len(pairs_to_export)} pares.")
            self._log_to_gui(f"Lista de {len(pairs_to_export)} pares ({selected_filter}) exportada.", "INFO")
        except Exception as e: self._show_popup("Erro de Arquivo", f"Não foi possível salvar:\n{e}")

    def _show_popup(self, title, message):
        popup = ctk.CTkToplevel(self); popup.title(title); popup.geometry("300x150")
        x, y = self.winfo_x()+(self.winfo_width()/2)-150, self.winfo_y()+(self.winfo_height()/2)-75
        popup.geometry(f"+{int(x)}+{int(y)}"); ctk.CTkLabel(popup, text=message, wraplength=280).pack(expand=True, padx=20, pady=20)
        ctk.CTkButton(popup, text="OK", command=popup.destroy).pack(pady=(0,10)); popup.transient(self); popup.grab_set()

    def _on_pair_list_update(self, pairs):
        self.all_pairs, self.normal_pairs, self.otc_pairs = pairs, sorted([p for p in pairs if not p.endswith('-OTC')]), sorted([p for p in pairs if p.endswith('-OTC')])
        self.after(0, self._update_pair_menu)

    def _update_pair_menu(self, *args):
        if hasattr(self, 'pair_filter_button') and self.pair_filter_button.winfo_exists():
            selected_filter = self.pair_filter_button.get()
            pair_list = self.normal_pairs if selected_filter == "Normal" else self.otc_pairs
            if pair_list and not self.robot_stats['is_active']:
                self.pair_option_menu.configure(values=pair_list, state="normal"); self.pair_option_menu.set(pair_list[0])
            elif self.robot_stats['is_active']:
                pass
            else:
                self.pair_option_menu.configure(values=["Nenhum par aberto"], state="disabled"); self.pair_option_menu.set("Nenhum par aberto")
    
    def _start_news_thread(self):
        if hasattr(self, 'news_card'): self.news_card.populate_news([{"impact": 0, "time": "", "currency": "🔄", "event": "Buscando notícias..."}])
        thread = threading.Thread(target=self._fetch_and_display_news); thread.daemon = True; thread.start()
        
    def _fetch_and_display_news(self):
        structured_news = fetch_structured_news()
        self.after(0, self._update_news_card, structured_news)
        
    def _update_news_card(self, news_data):
        if hasattr(self, 'news_card') and self.news_card.winfo_exists():
            self.news_card.populate_news(news_data)
