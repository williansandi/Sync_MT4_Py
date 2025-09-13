# ui/dashboard_frame.py

import customtkinter as ctk
import datetime
import logging

# --- Imports da Aplicação ---
from utils.config_manager import ConfigManager
from .styles.theme import ModernTheme
from .styles.fonts import AppFonts
from .components.news_scraper import fetch_structured_news
from utils.path_resolver import resource_path

# --- Imports dos Componentes de UI ---
from .components.financial_summary_card import FinancialSummaryCard
from .components.trade_history import TradeHistoryCard
from .components.news_card import NewsCard
from .signal_list_frame import SignalListFrame
from .management_frame import ManagementFrame

class ModernDashboardFrame(ctk.CTkFrame):
    def __init__(self, master, controller, font_family="Arial"):
        super().__init__(master)
        self.controller = controller
        self.font_family = font_family
        self.colors = ModernTheme
        self.fonts = AppFonts(font_family=self.font_family)
        
        self.sub_frames = {} # Renamed from self.frames
        self.log_history = []
        self.all_pairs = []
        self.normal_pairs = []
        self.otc_pairs = []

        self._setup_ui_layout() # This will now also create and stack sub-frames
        self._register_callbacks()
        self._show_frame("dashboard")

    def _register_callbacks(self):
        """Informa ao controller quais métodos da UI ele deve chamar para atualizações."""
        self.controller.set_ui_callbacks({
            'log_message': self.add_log_message,
            'on_trade_result': self.on_trade_result,
            'on_pair_list_update': self.on_pair_list_update,
            'update_connection_status': self.update_connection_status,
            'update_robot_status': self.update_robot_status,
            'update_metric_cards': self.update_metric_cards,
            'get_masaniello_configs': self.get_masaniello_configs,
            'show_popup': self._show_popup,
            'clear_trade_history': lambda: self.history_card.clear_list() if hasattr(self, 'history_card') else None,
            'clear_signal_list': lambda: self.sub_frames["lista"]._clear_signal_list() if "lista" in self.sub_frames else None,
            'update_strategy_status_bar': self._update_strategy_status_bar
        })

    # --- Métodos de Ação (Chamados pelos botões da UI) ---

    def _start_bot_clicked(self):
        strategy_name = self.strategy_option_menu.get()
        selected_pair = self.pair_option_menu.get()
        signals = []
        if strategy_name == "Lista de Sinais":
            signal_list_frame = self.sub_frames.get("lista")
            signals = signal_list_frame.get_signals() if signal_list_frame else []
        
        self.controller.start_bot(strategy_name, selected_pair, signals)

    def _pause_bot_clicked(self):
        self.controller.pause_bot()

    def _stop_bot_clicked(self):
        self.controller.stop_bot()

    def _restart_bot_clicked(self):
        self.controller.restart_bot()

    def _export_pairs_for_mt4(self):
        selected_filter = self.export_pair_filter.get()
        if selected_filter == "Normal": pairs_to_export = self.normal_pairs
        elif selected_filter == "OTC": pairs_to_export = self.otc_pairs
        else: pairs_to_export = self.all_pairs
        
        if not pairs_to_export:
            self._show_popup("Erro", "Nenhuma lista de pares carregada ou selecionada.")
            return
        self.controller.export_pairs_for_mt4(pairs_to_export, selected_filter)

    # --- Métodos de Callback (Chamados pelo Controller para atualizar a UI) ---

    def on_trade_result(self, trade_details):
        if hasattr(self, 'history_card'):
            self.history_card.add_trade(trade_details)
        
        if "signal_id" in trade_details.get("context", {}):
            signal_list_frame = self.sub_frames.get("lista")
            if signal_list_frame:
                signal_list_frame.update_signal_status(trade_details["context"]["signal_id"], trade_details)

        if "masaniello_status" in trade_details:
            management_frame = self.sub_frames.get("management")
            if management_frame and hasattr(management_frame, 'update_masaniello_status'):
                self.after(0, management_frame.update_masaniello_status, trade_details["masaniello_status"])

    def on_pair_list_update(self, pairs):
        self.all_pairs, self.normal_pairs, self.otc_pairs = pairs
        self.after(0, self._update_pair_menu)

    def update_robot_status(self, is_active, is_paused):
        if is_active:
            if is_paused:
                self.status_label.configure(text="🟡 PAUSADO", text_color=self.colors.ACCENT_GOLD)
                self.pause_button.configure(text="Continuar", fg_color=self.colors.ACCENT_GOLD)
            else:
                self.status_label.configure(text="🟢 ATIVO", text_color=self.colors.ACCENT_GREEN)
                self.pause_button.configure(text="Pausar", fg_color=self.colors.ACCENT_BLUE)
            
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.pause_button.configure(state="normal")
            if hasattr(self, 'strategy_option_menu') and self.strategy_option_menu.winfo_exists():
                self.strategy_option_menu.configure(state="disabled")
            if hasattr(self, 'pair_option_menu') and self.pair_option_menu.winfo_exists():
                self.pair_option_menu.configure(state="disabled")
        else:
            self.status_label.configure(text="🔴 INATIVO", text_color=self.colors.ACCENT_RED)
            self.start_button.configure(state="normal", text="▶️ Iniciar")
            self.stop_button.configure(state="disabled")
            self.pause_button.configure(state="disabled", text="Pausar")
            if hasattr(self, 'strategy_option_menu') and self.strategy_option_menu.winfo_exists():
                self.strategy_option_menu.configure(state="normal")
            self._update_pair_menu()

    def update_connection_status(self, component, status, message):
        colors = {"CONECTADO": self.colors.ACCENT_GREEN, "RECONECTANDO": self.colors.ACCENT_GOLD, "DESCONECTADO": self.colors.ACCENT_RED, "ERRO": self.colors.ACCENT_RED, "PARADO": "gray"}
        color = colors.get(status, "gray")
        
        status_map = {
            "IQ": (self.iq_status_indicator, self.iq_status_label, "IQ Option: "),
            "MT4": (self.mt4_status_indicator, self.mt4_status_label, "MT4: "),
            "MANUAL": (self.manual_status_indicator, self.manual_status_label, "Estratégia Manual: "),
            "SIGNALLIST": (self.signallist_status_indicator, self.signallist_status_label, "Lista de Sinais: ")
        }
        
        if component in status_map:
            indicator, label, prefix = status_map[component]
            indicator.configure(text_color=color)
            label.configure(text=f"{prefix}{message}")

    def update_metric_cards(self, summary_data):
        if hasattr(self, 'summary_card') and self.summary_card.winfo_exists():
            self.summary_card.update_summary(summary_data)

    def add_log_message(self, message, tag=None):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        tag_text = f"[{tag}]" if tag else "[*]"
        formatted_message = f"[{timestamp}] {tag_text.ljust(12)} {message}\n"
        self.log_history.append(formatted_message)
        if hasattr(self, 'dashboard_console') and self.dashboard_console.winfo_exists():
            self.after(0, self._update_console, formatted_message)

    def _update_console(self, message):
        if hasattr(self, 'dashboard_console') and self.dashboard_console.winfo_exists():
            self.dashboard_console.configure(state="normal")
            self.dashboard_console.insert("end", message)
            self.dashboard_console.see("end")
            self.dashboard_console.configure(state="disabled")

    def get_masaniello_configs(self):
        management_frame = self.sub_frames.get("management")
        if management_frame and management_frame.tab_view.get() == "Masaniello":
            try:
                return {
                    'capital': management_frame.masaniello_widgets['entries']['masaniello_capital'].get(),
                    'num_trades': management_frame.masaniello_widgets['entries']['masaniello_num_trades'].get(),
                    'expected_wins': management_frame.masaniello_widgets['entries']['masaniello_wins_esperados'].get(),
                    'payout': management_frame.masaniello_widgets['entries']['masaniello_payout'].get()
                }
            except Exception as e:
                self._show_popup("Erro de Configuração", f"Verifique os valores de Masaniello: {e}")
        return None

    # --- Métodos de Construção da UI (Restaurados da versão antiga) ---

    def _setup_ui_layout(self):
        self.configure(fg_color=self.colors.BG_PRIMARY)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_sidebar()
        self._create_header()
        
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 10))
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)

        # Pre-instantiate all sub-frames and stack them
        self.sub_frames["dashboard"] = self._create_dashboard_frame()
        self.sub_frames["strategy"] = self._create_strategy_frame()
        self.sub_frames["lista"] = SignalListFrame(self.main_content_frame)
        self.sub_frames["management"] = ManagementFrame(self.main_content_frame, self.controller.config_manager, save_callback=self.controller.on_settings_saved)
        self.sub_frames["catalog"] = self._create_catalog_frame()
        self.sub_frames["news"] = self._create_news_frame()

        for frame_name, frame_instance in self.sub_frames.items():
            frame_instance.grid(row=0, column=0, sticky="nsew") # Stack all frames

        self._create_status_bar()

    def _create_sidebar(self):
        sidebar_frame = ctk.CTkFrame(self, width=200, fg_color=self.colors.BG_CARD, corner_radius=0)
        sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsew")
        ctk.CTkLabel(sidebar_frame, text="🚀 QUANTUM", font=self.fonts.SIDEBAR_LOGO, text_color=self.colors.ACCENT_BLUE).pack(pady=20, padx=20)
        
        # self.frame_creators is no longer needed as frames are pre-instantiated

        buttons_info = {"dashboard": "Dashboard", "strategy": "Estratégias", "lista": "Lista de Sinais", "management": "Gerenciamento", "catalog": "Catalogador", "news": "Notícias"}
        for name, text in buttons_info.items():
            command = lambda n=name: self._show_frame(n)
            ctk.CTkButton(sidebar_frame, text=text, image=None, command=command, anchor="w", font=self.fonts.SIDEBAR_BUTTON, fg_color="transparent", hover_color=self.colors.BG_SECONDARY, height=40).pack(fill="x", padx=10, pady=5)

    def _create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color=self.colors.BG_CARD, height=70, corner_radius=10)
        header_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        header_frame.pack_propagate(False)
        ctk.CTkLabel(header_frame, text="Trading Robot Dashboard", font=self.fonts.HEADER_TITLE).pack(side="left", padx=20)
        
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=10)
        self.status_label = ctk.CTkLabel(right_frame, text="⚪ CONECTANDO...", font=(self.font_family, 16, "bold"), text_color="gray")
        self.status_label.pack(side="left", padx=(0, 10))
        
        self.restart_button = ctk.CTkButton(right_frame, text="🔄 Reiniciar", command=self._restart_bot_clicked, width=100)
        self.restart_button.pack(side="left", padx=5)
        self.start_button = ctk.CTkButton(right_frame, text="Conectando...", command=self._start_bot_clicked, width=100, state="disabled")
        self.start_button.pack(side="left", padx=5)
        self.pause_button = ctk.CTkButton(right_frame, text="Pausar", command=self._pause_bot_clicked, width=100, state="disabled")
        self.pause_button.pack(side="left", padx=5)
        self.stop_button = ctk.CTkButton(right_frame, text="⏹️ Parar", command=self._stop_bot_clicked, width=100, state="disabled")
        self.stop_button.pack(side="left", padx=5)

    def _create_status_bar(self):
        status_bar_frame = ctk.CTkFrame(self, fg_color=self.colors.BG_CARD, height=30, corner_radius=10)
        status_bar_frame.grid(row=2, column=1, sticky="ew", padx=10, pady=(0,10))
        status_bar_frame.pack_propagate(False)
        
        self.iq_status_indicator = ctk.CTkLabel(status_bar_frame, text="●", text_color="gray", font=("Arial", 16))
        self.iq_status_indicator.pack(side="left", padx=(15, 2), pady=5)
        self.iq_status_label = ctk.CTkLabel(status_bar_frame, text="IQ Option: Aguardando", font=self.fonts.BODY_SMALL, text_color=self.colors.TEXT_MUTED)
        self.iq_status_label.pack(side="left", pady=5)
        
        self.mt4_status_indicator = ctk.CTkLabel(status_bar_frame, text="●", text_color="gray", font=("Arial", 16))
        self.mt4_status_indicator.pack(side="left", padx=(20, 2), pady=5)
        self.mt4_status_label = ctk.CTkLabel(status_bar_frame, text="MT4: Aguardando", font=self.fonts.BODY_SMALL, text_color=self.colors.TEXT_MUTED)
        self.mt4_status_label.pack(side="left", pady=5)

        self.manual_status_indicator = ctk.CTkLabel(status_bar_frame, text="●", text_color="gray", font=("Arial", 16))
        self.manual_status_indicator.pack(side="left", padx=(20, 2), pady=5)
        self.manual_status_label = ctk.CTkLabel(status_bar_frame, text="Estratégia Manual: Inativa", font=self.fonts.BODY_SMALL, text_color=self.colors.TEXT_MUTED)
        self.manual_status_label.pack(side="left", pady=5)

        self.signallist_status_indicator = ctk.CTkLabel(status_bar_frame, text="●", text_color="gray", font=("Arial", 16))
        self.signallist_status_indicator.pack(side="left", padx=(20, 2), pady=5)
        self.signallist_status_label = ctk.CTkLabel(status_bar_frame, text="Lista de Sinais: Inativa", font=self.fonts.BODY_SMALL, text_color=self.colors.TEXT_MUTED)
        self.signallist_status_label.pack(side="left", pady=5)

    def _update_strategy_status_bar(self, active_strategy_info):
        manual_active = active_strategy_info.get('manual', False)
        signallist_active = active_strategy_info.get('signallist', False)
        self.update_connection_status("MANUAL", "CONECTADO" if manual_active else "PARADO", "Ativa" if manual_active else "Inativa")
        self.update_connection_status("SIGNALLIST", "CONECTADO" if signallist_active else "PARADO", "Ativa" if signallist_active else "Inativa")

    def _show_frame(self, frame_name_to_show):
        # Hide all sub-frames
        for frame_instance in self.sub_frames.values():
            frame_instance.grid_forget()

        frame_to_show = self.sub_frames.get(frame_name_to_show)
        if frame_to_show:
            frame_to_show.tkraise()
            frame_to_show.grid(row=0, column=0, sticky="nsew", in_=self.main_content_frame)

    

    def _create_dashboard_frame(self):
        frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=2)
        frame.grid_rowconfigure(1, weight=1)
        self.summary_card = FinancialSummaryCard(frame, font_family=self.font_family)
        self.summary_card.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="nsew")
        self.history_card = TradeHistoryCard(frame, font_family=self.font_family)
        self.history_card.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="nsew")
        activity_frame = ctk.CTkFrame(frame, fg_color=self.colors.BG_CARD, corner_radius=10)
        activity_frame.grid(row=1, column=0, columnspan=2, padx=0, pady=10, sticky="nsew")
        ctk.CTkLabel(activity_frame, text="🔔 Atividade Recente (Terminal)", font=(self.font_family, 16, "bold")).pack(pady=10, anchor="w", padx=15)
        self.dashboard_console = ctk.CTkTextbox(activity_frame, font=self.fonts.CONSOLE, fg_color=self.colors.BG_SECONDARY, state="disabled", corner_radius=8, border_width=0)
        self.dashboard_console.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.controller.request_initial_dashboard_data() # Request initial data from the controller
        
        return frame

    def _create_strategy_frame(self):
        frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self._create_page_header(frame, "📊 Gerenciador de Estratégias")
        content_area = ctk.CTkFrame(frame, fg_color="transparent")
        content_area.pack(fill="both", expand=True, pady=10)
        content_area.grid_columnconfigure((0, 1, 2), weight=1)
        config_frame = ctk.CTkFrame(content_area, fg_color=self.colors.BG_CARD, corner_radius=10)
        config_frame.grid(row=0, column=0, columnspan=3, padx=0, pady=0, sticky="ew")
        ctk.CTkLabel(config_frame, text="Estratégia Principal:", font=self.fonts.CARD_TITLE).grid(row=0, column=0, padx=10, pady=(10,5), sticky="w")
        self.strategy_option_menu = ctk.CTkOptionMenu(config_frame, values=["Sinal MT4", "MHI (Minoria)", "Lista de Sinais"])
        self.strategy_option_menu.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
        ctk.CTkLabel(config_frame, text="Tipo de Ativo:", font=self.fonts.CARD_TITLE).grid(row=0, column=1, padx=10, pady=(10,5), sticky="w")
        self.pair_filter_button = ctk.CTkSegmentedButton(config_frame, values=["Normal", "OTC"], command=self._update_pair_menu)
        self.pair_filter_button.set("Normal")
        self.pair_filter_button.grid(row=1, column=1, padx=10, pady=(0,10), sticky="ew")
        ctk.CTkLabel(config_frame, text="Par de Moedas (para MHI):", font=self.fonts.CARD_TITLE).grid(row=0, column=2, padx=10, pady=(10,5), sticky="w")
        self.pair_option_menu = ctk.CTkOptionMenu(config_frame, values=["Aguardando conexão..."], state="disabled")
        self.pair_option_menu.grid(row=1, column=2, padx=10, pady=(0,10), sticky="ew")
        return frame

    def _create_catalog_frame(self):
        frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self._create_page_header(frame, "📈 Catalogador e Ferramentas")
        content_area = ctk.CTkFrame(frame, fg_color="transparent")
        content_area.pack(fill="both", expand=True, pady=10)
        content_area.grid_columnconfigure(0, weight=1)
        content_area.grid_rowconfigure(1, weight=1)
        tools_frame = ctk.CTkFrame(content_area, fg_color=self.colors.BG_CARD, corner_radius=10)
        tools_frame.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        ctk.CTkLabel(tools_frame, text="Ferramentas de Integração MT4", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, padx=10, pady=(10,5))
        self.export_pair_filter = ctk.CTkSegmentedButton(tools_frame, values=["Normal", "OTC", "Ambos"])
        self.export_pair_filter.set("Normal")
        self.export_pair_filter.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        export_button = ctk.CTkButton(tools_frame, text="✔️ Exportar Pares para MT4", command=self._export_pairs_for_mt4, height=35)
        export_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        results_frame = ctk.CTkFrame(content_area, fg_color=self.colors.BG_CARD, corner_radius=10)
        results_frame.grid(row=1, column=0, pady=10, sticky="nsew")
        ctk.CTkLabel(results_frame, text="Resultados da Catalogação aparecerão aqui...", font=self.fonts.BODY_NORMAL).pack(expand=True, padx=20, pady=20)
        return frame

    def _create_news_frame(self):
        frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        header = self._create_page_header(frame, "📰 Central de Notícias")
        ctk.CTkButton(header, text="🔄 Atualizar", command=self._fetch_news_data, fg_color=self.colors.ACCENT_BLUE, width=140, height=30, corner_radius=8, font=self.fonts.BUTTON).pack(side="right", padx=20, pady=15)
        self.news_card = NewsCard(frame, font_family=self.font_family)
        self.news_card.pack(fill="both", expand=True, pady=10)
        self._fetch_news_data() # Fetch initial news
        return frame

    def _fetch_news_data(self):
        if hasattr(self, 'news_card') and self.news_card.winfo_exists():
            self.after(100, lambda: self.controller.fetch_news(callback=self.news_card.populate_news))

    def _update_pair_menu(self, *args):
        if hasattr(self, 'pair_filter_button') and self.pair_filter_button.winfo_exists():
            selected_filter = self.pair_filter_button.get()
            pair_list = self.normal_pairs if selected_filter == "Normal" else self.otc_pairs
            if pair_list and self.start_button.cget("state") == "normal":
                if hasattr(self, 'pair_option_menu') and self.pair_option_menu.winfo_exists():
                    self.pair_option_menu.configure(values=pair_list, state="normal")
                    self.pair_option_menu.set(pair_list[0])
            elif self.start_button.cget("state") == "disabled":
                pass
            else:
                if hasattr(self, 'pair_option_menu') and self.pair_option_menu.winfo_exists():
                    self.pair_option_menu.configure(values=["Nenhum par aberto"], state="disabled")
                    self.pair_option_menu.set("Nenhum par aberto")

    def _show_popup(self, title, message):
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.geometry("300x150")
        x, y = self.winfo_x() + (self.winfo_width() / 2) - 150, self.winfo_y() + (self.winfo_height() / 2) - 75
        popup.geometry(f"+{int(x)}+{int(y)}")
        ctk.CTkLabel(popup, text=message, wraplength=280).pack(expand=True, padx=20, pady=20)
        ctk.CTkButton(popup, text="OK", command=popup.destroy).pack(pady=(0,10))
        popup.transient(self)
        popup.grab_set()
        popup.wait_window()

    def _create_page_header(self, parent, title):
        header = ctk.CTkFrame(parent, fg_color=self.colors.BG_CARD, corner_radius=10, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text=title, font=self.fonts.PAGE_TITLE).pack(side="left", padx=20, pady=15)
        return header
