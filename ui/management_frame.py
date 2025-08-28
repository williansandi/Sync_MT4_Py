# ui/management_frame.py

import customtkinter as ctk
from .styles.theme import ModernTheme
from .styles.fonts import AppFonts
import logging

class ManagementFrame(ctk.CTkFrame):
    def __init__(self, master, config_manager, save_callback):
        super().__init__(master, fg_color="transparent")
        self.config_manager = config_manager
        self.save_callback = save_callback
        self.fonts = AppFonts()
        self.colors = ModernTheme
        
        # Dicionários separados para os widgets de cada aba
        self.simple_widgets = {"entries": {}, "buttons": {}}
        self.cycles_widgets = {"entries": {}, "buttons": {}}
        self.masaniello_widgets = {"entries": {}, "buttons": {}}
        self.general_widgets = {"entries": {}, "buttons": {}}
        self.all_widgets = [self.simple_widgets, self.cycles_widgets, self.masaniello_widgets, self.general_widgets]

        self.masaniello_status_labels = {}
        self.tab_view = None
        
        self._create_widgets()
        self._load_settings()

    def _create_widgets(self):
        ctk.CTkLabel(self, text="💰 Gerenciamento e Configurações", font=self.fonts.PAGE_TITLE).pack(anchor="w", pady=(0, 20))

        self.tab_view = ctk.CTkTabview(self, fg_color=self.colors.BG_CARD, segmented_button_fg_color=self.colors.BG_SECONDARY,
                                     segmented_button_selected_color=self.colors.ACCENT_BLUE, segmented_button_selected_hover_color=self.colors.ACCENT_BLUE_HOVER,
                                     segmented_button_unselected_color=self.colors.BG_SECONDARY)
        self.tab_view.pack(fill="both", expand=True)

        self._create_simple_management_tab(self.tab_view.add("Gerenciamento Simples"))
        self._create_cycles_tab(self.tab_view.add("Ciclos (Recuperação)"))
        self._create_masaniello_tab(self.tab_view.add("Masaniello"))
        self._create_general_settings_tab(self.tab_view.add("⚙️ Configs. Gerais"))

        save_button = ctk.CTkButton(self, text="Salvar e Aplicar Todas as Configurações", command=self._save_settings, height=40)
        save_button.pack(fill="x", pady=(20, 0))
        self.status_label = ctk.CTkLabel(self, text="", text_color=self.colors.ACCENT_GREEN)
        self.status_label.pack(pady=10)

    def _create_row(self, parent, row, label_text, is_segmented=False, options=None):
        ctk.CTkLabel(parent, text=label_text, anchor="w").grid(row=row, column=0, sticky="w", padx=20, pady=10)
        if is_segmented:
            widget = ctk.CTkSegmentedButton(parent, values=[opt.upper() for opt in (options or ["ATIVADO", "DESATIVADO"])] )
            widget.grid(row=row, column=1, sticky="w", padx=20, pady=10)
            return widget
        else:
            widget = ctk.CTkEntry(parent, width=200)
            widget.grid(row=row, column=1, sticky="w", padx=20, pady=10)
            return widget

    def _create_simple_management_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab, text="Defina seus alvos e limites diários.", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(10, 15))
        fields = {"valor_entrada": "Valor da Entrada ($)", "stop_win": "Meta de Lucro (Stop Win)", "stop_loss": "Limite de Perda (Stop Loss)"}
        for i, (key, label) in enumerate(fields.items(), start=1):
            self.simple_widgets["entries"][key] = self._create_row(tab, i, label)

    def _create_cycles_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab, text="Configure o sistema de recuperação com múltiplos ciclos e níveis.", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(10, 15))
        self.cycles_widgets["buttons"]["usar_ciclos"] = self._create_row(tab, 1, "Ativar Gerenciamento de Ciclos", is_segmented=True)
        self.cycles_widgets["buttons"]["management_type"] = self._create_row(tab, 2, "Tipo de Gerenciamento", is_segmented=True, options=["agressivo", "conservador"])
        
        cycle_entries = [("fator_martingale", "Fator de Multiplicação (Gale)"), ("niveis_martingale", "Níveis de Martingale por Ciclo"), 
                         ("max_ciclos", "Número Máximo de Ciclos"), ("payout_recuperacao", "Payout Esperado na Recuperação (%)"),
                         ("conservative_recovery_percentage", "% de Recuperação Conservadora")]
        for i, (key, label) in enumerate(cycle_entries, start=3):
            self.cycles_widgets["entries"][key] = self._create_row(tab, i, label)

    def _create_masaniello_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab, text="Use a progressão Masaniello para gerenciar seu capital.", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(10, 15))
        self.masaniello_widgets["buttons"]["usar_masaniello"] = self._create_row(tab, 1, "Ativar Masaniello", is_segmented=True)

        masaniello_entries = [("masaniello_capital", "Capital Inicial do Ciclo ($)"), ("masaniello_num_trades", "Nº Total de Operações"),
                              ("masaniello_wins_esperados", "Nº de Wins Esperados"), ("masaniello_payout", "Payout Médio Esperado (%)")]
        for i, (key, label) in enumerate(masaniello_entries, start=2):
            self.masaniello_widgets["entries"][key] = self._create_row(tab, i, label)
        # ... (código de status do masaniello permanece o mesmo)

    def _create_general_settings_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab, text="Ajustes gerais de automação e filtros.", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(10, 15))
        self.general_widgets["buttons"]["usar_martingale"] = self._create_row(tab, 1, "Usar Martingale", is_segmented=True)
        self.general_widgets["entries"]["fator_martingale"] = self._create_row(tab, 2, "Fator de Multiplicação (Gale)")
        self.general_widgets["entries"]["niveis_martingale"] = self._create_row(tab, 3, "Níveis de Martingale")
        
        ctk.CTkLabel(tab, text="FILTRO DE NOTÍCIAS", font=self.fonts.CARD_TITLE).grid(row=4, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 5))
        self.general_widgets["buttons"]["usar_filtro_noticias"] = self._create_row(tab, 5, "Filtro de Notícias", is_segmented=True)
        self.general_widgets["entries"]["minutos_antes_noticia"] = self._create_row(tab, 6, "Pausar Antes de Notícia (min)")
        self.general_widgets["entries"]["minutos_depois_noticia"] = self._create_row(tab, 7, "Pausar Depois de Notícia (min)")

        ctk.CTkLabel(tab, text="OPERAÇÕES DIGITAIS", font=self.fonts.CARD_TITLE).grid(row=8, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 5))
        self.general_widgets["buttons"]["usar_maior_payout_digital"] = self._create_row(tab, 9, "Operar com Maior Payout (Digital)", is_segmented=True)

    def _load_settings(self):
        current_config = self.config_manager.get_all_settings()
        for widget_group in self.all_widgets:
            for key, entry in widget_group["entries"].items():
                entry.delete(0, 'end')
                entry.insert(0, current_config.get(key, ""))
            for key, button in widget_group["buttons"].items():
                value = current_config.get(key, "N").upper()
                if key.startswith('usar_'):
                    button.set("ATIVADO" if value == 'S' else "DESATIVADO")
                else:
                    button.set(value)
        logging.info("Todas as configurações foram carregadas na interface.")

    def _save_settings(self):
        new_config = {}
        for widget_group in self.all_widgets:
            for key, entry in widget_group["entries"].items():
                new_config[key] = entry.get()
            for key, button in widget_group["buttons"].items():
                value = button.get().lower()
                if key.startswith('usar_'):
                    new_config[key] = 'S' if value == 'ativado' else 'N'
                else:
                    new_config[key] = value
        
        self.config_manager.save_settings(new_config)
        self.status_label.configure(text="✔ Configurações salvas e aplicadas ao robô!", text_color=self.colors.ACCENT_GREEN)
        self.after(3000, lambda: self.status_label.configure(text=""))
        
        # Notifica o dashboard que as configurações foram salvas
        if self.save_callback:
            self.save_callback()