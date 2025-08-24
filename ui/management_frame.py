# ui/management_frame.py

import customtkinter as ctk
from .styles.theme import ModernTheme
from .styles.fonts import AppFonts
import logging

class ManagementFrame(ctk.CTkFrame):
    def __init__(self, master, config_manager):
        super().__init__(master, fg_color="transparent")
        self.config_manager = config_manager
        self.fonts = AppFonts()
        self.entries = {}
        self.segmented_buttons = {}

        self._create_widgets()
        self._load_settings()

    def _create_widgets(self):
        ctk.CTkLabel(self, text="💰 Gerenciamento de Capital", font=self.fonts.PAGE_TITLE).pack(anchor="w", pady=(0, 20))

        # --- Criação do TabView ---
        tab_view = ctk.CTkTabview(self, fg_color=ModernTheme.BG_CARD, segmented_button_fg_color=ModernTheme.BG_SECONDARY,
                                  segmented_button_selected_color=ModernTheme.ACCENT_BLUE,
                                  segmented_button_selected_hover_color=ModernTheme.ACCENT_BLUE_HOVER,
                                  segmented_button_unselected_color=ModernTheme.BG_SECONDARY)
        tab_view.pack(fill="both", expand=True)

        tab_simples = tab_view.add("Gerenciamento Simples")
        tab_ciclos = tab_view.add("Ciclos (Recuperação)")
        tab_masaniello = tab_view.add("Masaniello")
        
        # --- Conteúdo da Aba "Gerenciamento Simples" ---
        self._create_simple_management_tab(tab_simples)
        
        # --- Conteúdo da Aba "Ciclos" ---
        self._create_cycles_tab(tab_ciclos)

        # --- Conteúdo da Aba "Masaniello" ---
        self._create_masaniello_tab(tab_masaniello)

        # --- Botão de Salvar ---
        save_button = ctk.CTkButton(self, text="Salvar Configurações de Gerenciamento", command=self._save_settings, height=40)
        save_button.pack(fill="x", pady=(20, 0))
        self.status_label = ctk.CTkLabel(self, text="", text_color=ModernTheme.ACCENT_GREEN)
        self.status_label.pack(pady=10)

    def _create_simple_management_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(tab, text="Defina seus alvos e limites diários.", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(10, 15))
        
        fields = {"valor_entrada": "Valor da Entrada ($)", "stop_win": "Meta de Lucro (Stop Win)", "stop_loss": "Limite de Perda (Stop Loss)"}
        row = 1
        for key, label in fields.items():
            ctk.CTkLabel(tab, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=20, pady=10)
            entry = ctk.CTkEntry(tab, width=200)
            entry.grid(row=row, column=1, sticky="w", padx=20, pady=10)
            self.entries[key] = entry
            row += 1

    def _create_cycles_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab, text="Configure a recuperação após um ciclo de Martingale perdido.", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(10, 15))
        
        self.segmented_buttons['usar_ciclos'] = self._create_row(tab, 1, "Ativar Gerenciamento de Ciclos", "usar_ciclos", is_segmented=True)
        self.entries['ciclos_valor_recuperacao'] = self._create_row(tab, 2, "Valor de Entrada Pós-Loss ($)", "ciclos_valor_recuperacao")
        self.entries['ciclos_payout_recuperacao'] = self._create_row(tab, 3, "Payout Esperado na Recuperação (%)", "ciclos_payout_recuperacao")
    
    def _create_masaniello_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab, text="Use a progressão Masaniello para gerenciar seu capital.", font=self.fonts.BODY_NORMAL).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(10, 15))

        self.segmented_buttons['usar_masaniello'] = self._create_row(tab, 1, "Ativar Masaniello", "usar_masaniello", is_segmented=True)
        self.entries['masaniello_capital'] = self._create_row(tab, 2, "Capital Inicial do Ciclo ($)", "masaniello_capital")
        self.entries['masaniello_num_trades'] = self._create_row(tab, 3, "Nº Total de Operações no Ciclo", "masaniello_num_trades")
        self.entries['masaniello_wins_esperados'] = self._create_row(tab, 4, "Nº de Wins Esperados no Ciclo", "masaniello_wins_esperados")
        self.entries['masaniello_payout'] = self._create_row(tab, 5, "Payout Médio Esperado (%)", "masaniello_payout")

    def _create_row(self, parent, row, label_text, key, is_segmented=False):
        ctk.CTkLabel(parent, text=label_text, anchor="w").grid(row=row, column=0, sticky="w", padx=20, pady=10)
        if is_segmented:
            widget = ctk.CTkSegmentedButton(parent, values=["ATIVADO", "DESATIVADO"])
            widget.grid(row=row, column=1, sticky="w", padx=20, pady=10)
            return widget
        else:
            widget = ctk.CTkEntry(parent, width=200)
            widget.grid(row=row, column=1, sticky="w", padx=20, pady=10)
            return widget

    def _load_settings(self):
        current_config = self.config_manager.get_all_settings()
        for key, entry_widget in self.entries.items():
            entry_widget.insert(0, current_config.get(key, ""))
        for key, button_widget in self.segmented_buttons.items():
            value = "ATIVADO" if current_config.get(key, "N").upper() == 'S' else "DESATIVADO"
            button_widget.set(value)
        logging.info("Configurações de gerenciamento carregadas na interface.")

    def _save_settings(self):
        new_config = {}
        for key, entry_widget in self.entries.items():
            new_config[key] = entry_widget.get()
        for key, button_widget in self.segmented_buttons.items():
            value = 'S' if button_widget.get() == "ATIVADO" else 'N'
            new_config[key] = value
            
        self.config_manager.save_settings(new_config)
        self.status_label.configure(text="✔ Configurações de gerenciamento salvas!")
        self.after(3000, lambda: self.status_label.configure(text=""))