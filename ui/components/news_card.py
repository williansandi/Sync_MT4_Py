# ui/components/news_card.py

import customtkinter as ctk
from ..styles.theme import ModernTheme
from ..styles.fonts import AppFonts

class NewsCard(ctk.CTkFrame):
    def __init__(self, master, font_family="Arial"):
        super().__init__(master, fg_color="transparent")
        self.fonts = AppFonts(font_family)
        
        # Configuração centralizada das colunas para garantir alinhamento perfeito
        self.column_config = {
            "impact":   {"weight": 0, "minsize": 80, "stretch": False, "text": "IMPACTO"},
            "time":     {"weight": 1, "minsize": 60, "stretch": True,  "text": "HORA"},
            "currency": {"weight": 1, "minsize": 60, "stretch": True,  "text": "MOEDA"},
            "event":    {"weight": 5, "minsize": 250, "stretch": True, "text": "EVENTO"}
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # A área de rolagem é que expande

        # Cria o frame do cabeçalho
        header_frame = ctk.CTkFrame(self, fg_color=ModernTheme.BG_CARD, corner_radius=10, height=30)
        header_frame.grid(row=0, column=0, sticky="ew")
        self._create_headers(header_frame)

        # Cria a área de rolagem para os cards de notícia
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        
    def _apply_column_config(self, parent_frame):
        """Aplica a configuração de colunas a um frame (header ou row)."""
        for i, config in enumerate(self.column_config.values()):
            parent_frame.grid_columnconfigure(i, weight=config["weight"], minsize=config.get("minsize", 0))

    def _create_headers(self, parent):
        """Cria os títulos das colunas usando a configuração centralizada."""
        self._apply_column_config(parent)
        
        header_font = (self.fonts.FAMILY, 10, "bold")
        text_color = ModernTheme.TEXT_MUTED
        
        for i, config in enumerate(self.column_config.values()):
            ctk.CTkLabel(parent, text=config["text"], font=header_font, text_color=text_color).grid(row=0, column=i, sticky="ew", padx=10)

    def _create_news_row(self, parent, news_item):
        """Cria um card individual para uma notícia."""
        # (ALTERADO) Altura definida para 30 e pady reduzido
        card = ctk.CTkFrame(parent, fg_color=ModernTheme.BG_CARD, corner_radius=10, height=30)
        card.pack(fill="x", padx=5, pady=2)
        card.pack_propagate(False) 
        
        self._apply_column_config(card)

        impact_text = "★" * news_item['impact']
        impact_color = ModernTheme.ACCENT_GOLD if news_item['impact'] == 2 else ModernTheme.ACCENT_RED
        
        # --- Todos os widgets com fonte e pady padronizados ---
        ctk.CTkLabel(card, text=impact_text, font=self.fonts.BODY_SMALL, text_color=impact_color).grid(row=0, column=0, sticky="ew", pady=0)
        ctk.CTkLabel(card, text=news_item['time'], font=self.fonts.BODY_SMALL).grid(row=0, column=1, sticky="ew", pady=0)
        ctk.CTkLabel(card, text=news_item['currency'], font=self.fonts.BODY_SMALL).grid(row=0, column=2, sticky="ew", pady=0)
        
        event_label = ctk.CTkLabel(card, text=news_item['event'], font=self.fonts.BODY_SMALL, wraplength=300, anchor="w", justify="left")
        event_label.grid(row=0, column=3, sticky="w", pady=0, padx=10)

    def populate_news(self, news_data):
        # Check if the NewsCard itself exists before proceeding
        if not self.winfo_exists(): # Check the parent NewsCard
            return

        # Destroy the old scrollable_frame and recreate it
        if hasattr(self, 'scrollable_frame') and self.scrollable_frame.winfo_exists():
            self.scrollable_frame.destroy()
        
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        
        # No need for update_idletasks here as the frame is new

        if not news_data:
            ctk.CTkLabel(self.scrollable_frame, text="Nenhuma notícia de impacto encontrada.").pack(pady=20)
            return

        for news_item in news_data:
            self._create_news_row(self.scrollable_frame, news_item)