# ui/settings_frame.py

import customtkinter as ctk
from .styles.theme import ModernTheme
from .styles.fonts import AppFonts
import logging

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, config_manager):
        super().__init__(master, fg_color="transparent")
        self.config_manager = config_manager
        self.fonts = AppFonts()
        self.entries = {}
        self.segmented_buttons = {}

        self._create_widgets()
        self._load_settings()

    def _create_widgets(self):
        ctk.CTkLabel(self, text="⚙️ Configurações Gerais do Robô", font=self.fonts.PAGE_TITLE).pack(anchor="w", pady=(0, 20))
        settings_area = ctk.CTkScrollableFrame(self, fg_color=ModernTheme.BG_CARD, corner_radius=10)
        settings_area.pack(fill="both", expand=True)
        settings_area.grid_columnconfigure(1, weight=1)
        
        # --- CAMPOS DE CONFIGURAÇÃO ATUALIZADOS ---
        # A seção "AJUSTES" foi movida para ManagementFrame
        config_fields = {
            "MARTINGALE": {"usar_martingale": "Usar Martingale", "niveis_martingale": "Níveis de Martingale", "fator_martingale": "Fator de Multiplicação"},
            "FILTRO DE NOTÍCIAS": {"usar_filtro_noticias": "Filtro de Notícias", "minutos_antes_noticia": "Pausar Antes de Notícia (min)", "minutos_depois_noticia": "Pausar Depois de Notícia (min)"}
        }
        
        row_counter = 0
        for section, fields in config_fields.items():
            ctk.CTkLabel(settings_area, text=section, font=self.fonts.CARD_TITLE).grid(row=row_counter, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 5))
            row_counter += 1
            for key, label in fields.items():
                ctk.CTkLabel(settings_area, text=label, anchor="w").grid(row=row_counter, column=0, sticky="w", padx=20, pady=5)
                if key.startswith('usar_'):
                    seg_button = ctk.CTkSegmentedButton(settings_area, values=["ATIVADO", "DESATIVADO"])
                    seg_button.grid(row=row_counter, column=1, sticky="w", padx=20, pady=5)
                    self.segmented_buttons[key] = seg_button
                else:
                    entry = ctk.CTkEntry(settings_area, width=200)
                    entry.grid(row=row_counter, column=1, sticky="w", padx=20, pady=5)
                    self.entries[key] = entry
                row_counter += 1
        
        save_button = ctk.CTkButton(self, text="Salvar Configurações", command=self._save_settings, height=40)
        save_button.pack(fill="x", pady=(20, 0))
        self.status_label = ctk.CTkLabel(self, text="", text_color=ModernTheme.ACCENT_GREEN)
        self.status_label.pack(pady=10)

    def _load_settings(self):
        current_config = self.config_manager.get_all_settings()
        for key, entry_widget in self.entries.items():
            # Limpa o campo antes de inserir, caso já haja algo
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, current_config.get(key, ""))
        for key, button_widget in self.segmented_buttons.items():
            value = "ATIVADO" if current_config.get(key, "N").upper() == 'S' else "DESATIVADO"
            button_widget.set(value)
        logging.info("Configurações carregadas na interface.")

    def _save_settings(self):
        new_config = {}
        for key, entry_widget in self.entries.items():
            new_config[key] = entry_widget.get()
        for key, button_widget in self.segmented_buttons.items():
            value = 'S' if button_widget.get() == "ATIVADO" else 'N'
            new_config[key] = value
            
        self.config_manager.save_settings(new_config)
        self.status_label.configure(text="✔ Configurações salvas com sucesso!")
        self.after(3000, lambda: self.status_label.configure(text=""))