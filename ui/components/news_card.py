# ui/components/news_card.py

import customtkinter as ctk
from ..styles.theme import ModernTheme
from ..styles.fonts import AppFonts

class NewsCard(ctk.CTkFrame):
    def __init__(self, master, font_family="Arial"):
        super().__init__(master, fg_color="transparent")
        self.fonts = AppFonts(font_family)

        # --- Configuração das Colunas ---
        self.column_config = {
            "impact":   {"col": 0, "weight": 0, "minsize": 60},
            "time":     {"col": 1, "weight": 0, "minsize": 50},
            "currency": {"col": 2, "weight": 0, "minsize": 50},
            "event":    {"col": 3, "weight": 1, "minsize": 300}
        }
        self.header_texts = ["IMPACTO", "HORA", "MOEDA", "EVENTO"]
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Frame de Rolagem Principal ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color=ModernTheme.BG_CARD, corner_radius=10)
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")

        # Aplica a configuração de colunas ao grid do frame de rolagem
        for config in self.column_config.values():
            self.scrollable_frame.grid_columnconfigure(config["col"], weight=config["weight"], minsize=config["minsize"])

        self._create_headers()

    def _create_headers(self):
        """Cria os cabeçalhos das colunas diretamente no grid principal."""
        header_font = (self.fonts.FAMILY, 12, "bold") # Corrected font
        text_color = ModernTheme.TEXT_MUTED
        
        for config, text in zip(self.column_config.values(), self.header_texts):
            header_label = ctk.CTkLabel(self.scrollable_frame, text=text, font=header_font, text_color=text_color, anchor="w")
            header_label.grid(row=0, column=config["col"], sticky="nsew", padx=10, pady=5)

    def _create_news_row(self, row_index, news_item):
        """Cria os widgets para uma única linha de notícia no grid principal."""
        
        # --- Impacto ---
        impact_text = "★" * news_item['impact']
        impact_color = ModernTheme.ACCENT_GOLD if news_item['impact'] == 2 else ModernTheme.ACCENT_RED
        impact_label = ctk.CTkLabel(self.scrollable_frame, text=impact_text, font=self.fonts.BODY_SMALL, text_color=impact_color, anchor="w")
        impact_label.grid(row=row_index, column=self.column_config["impact"]["col"], sticky="nsew", padx=10, pady=2)

        # --- Hora ---
        time_label = ctk.CTkLabel(self.scrollable_frame, text=news_item['time'], font=self.fonts.BODY_SMALL, anchor="w")
        time_label.grid(row=row_index, column=self.column_config["time"]["col"], sticky="nsew", padx=10, pady=2)

        # --- Moeda ---
        currency_label = ctk.CTkLabel(self.scrollable_frame, text=news_item['currency'], font=self.fonts.BODY_SMALL, anchor="w")
        currency_label.grid(row=row_index, column=self.column_config["currency"]["col"], sticky="nsew", padx=10, pady=2)

        # --- Evento (com quebra de linha) ---
        # Define um wraplength fixo. A coluna de evento tem um minsize de 300.
        event_label = ctk.CTkLabel(self.scrollable_frame, text=news_item['event'], font=self.fonts.BODY_SMALL, anchor="w", justify="left", wraplength=300)
        event_label.grid(row=row_index, column=self.column_config["event"]["col"], sticky="nsew", padx=10, pady=2)

    def populate_news(self, news_data):
        # Limpa apenas as linhas de notícias antigas, preservando o cabeçalho
        for widget in self.scrollable_frame.winfo_children():
            if widget.grid_info().get("row", 0) > 0:
                widget.destroy()

        if not news_data:
            no_news_label = ctk.CTkLabel(self.scrollable_frame, text="Nenhuma notícia de impacto encontrada.")
            no_news_label.grid(row=1, column=0, columnspan=len(self.column_config), pady=20)
            return

        for i, news_item in enumerate(news_data, start=1):
            self._create_news_row(i, news_item)
