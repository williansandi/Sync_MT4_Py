# ui/components/trade_history.py

import customtkinter as ctk
from ..styles.theme import ModernTheme
from ..styles.fonts import AppFonts
from datetime import datetime
import logging

class TradeHistoryCard(ctk.CTkFrame):
    def __init__(self, master, font_family="Arial"):
        super().__init__(master, fg_color=ModernTheme.BG_CARD, corner_radius=10)
        self.fonts = AppFonts(font_family)
        
        # Configuração Centralizada das Colunas
        self.column_config = {
            "status":   {"weight": 0, "minsize": 30, "stretch": False},
            "hora":     {"weight": 1, "minsize": 60, "stretch": True,  "text": "HORA"},
            "ativo":    {"weight": 2, "minsize": 80, "stretch": True,  "text": "ATIVO"},
            "direcao":  {"weight": 1, "minsize": 60, "stretch": True,  "text": "DIREÇÃO"},
            "valor":    {"weight": 2, "minsize": 80, "stretch": True,  "text": "ENTRADA"},
            "lucro":    {"weight": 2, "minsize": 80, "stretch": True,  "text": "LUCRO"}
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="🔔 HISTÓRICO DE OPERAÇÕES", font=self.fonts.CARD_TITLE, text_color=ModernTheme.TEXT_SECONDARY).grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))

        header_frame = ctk.CTkFrame(self, fg_color="transparent", height=25)
        header_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        self._create_headers(header_frame)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
        
        self.trade_rows = []

    def _apply_column_config(self, parent_frame):
        """Aplica a configuração de colunas a um frame (header ou row)."""
        for i, (key, config) in enumerate(self.column_config.items()):
            if config["stretch"]:
                parent_frame.grid_columnconfigure(i, weight=config["weight"], minsize=config.get("minsize", 0))
            else:
                 parent_frame.grid_columnconfigure(i, weight=0, minsize=config.get("minsize", 0))

    def _create_headers(self, parent):
        """Cria os títulos das colunas usando a configuração centralizada."""
        self._apply_column_config(parent)
        
        header_font = (self.fonts.FAMILY, 10, "bold")
        text_color = ModernTheme.TEXT_MUTED
        
        for i, (key, config) in enumerate(self.column_config.items()):
            if "text" in config:
                ctk.CTkLabel(parent, text=config["text"], font=header_font, text_color=text_color).grid(row=0, column=i, sticky="ew")

    def add_trade(self, trade_data):
        """Adiciona uma nova linha de trade ao histórico."""
        # Cria o frame da linha com altura fixa de 30px
        row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=ModernTheme.BG_SECONDARY, height=30, corner_radius=8)
        row_frame.pack_propagate(False) 
        row_frame.pack(fill="x", padx=5, pady=2)
        
        self._apply_column_config(row_frame)
        
        # --- ESTA É A PARTE QUE ESTAVA FALTANDO ---
        # Criação dos widgets com os dados do trade
        status_color = ModernTheme.ACCENT_GREEN if trade_data['resultado'] == 'WIN' else ModernTheme.ACCENT_RED
        ctk.CTkLabel(row_frame, text="●", font=("Arial", 16), text_color=status_color).grid(row=0, column=0, sticky="ew", pady=0)
        
        hora = datetime.now().strftime('%H:%M:%S')
        ctk.CTkLabel(row_frame, text=hora, font=self.fonts.BODY_SMALL).grid(row=0, column=1, sticky="ew", pady=0)

        ctk.CTkLabel(row_frame, text=trade_data['ativo'], font=self.fonts.BODY_SMALL).grid(row=0, column=2, sticky="ew", pady=0)

        direcao_img = "🔼 CALL" if trade_data['direcao'] == 'call' else "🔽 PUT"
        ctk.CTkLabel(row_frame, text=direcao_img, font=self.fonts.BODY_SMALL).grid(row=0, column=3, sticky="ew", pady=0)
        
        valor_text = f"{trade_data['cifrao']} {trade_data['valor']:.2f}"
        ctk.CTkLabel(row_frame, text=valor_text, font=self.fonts.BODY_SMALL, text_color=ModernTheme.TEXT_MUTED).grid(row=0, column=4, sticky="ew", pady=0)

        lucro_text = f"{trade_data['cifrao']} {trade_data['lucro']:+.2f}"
        ctk.CTkLabel(row_frame, text=lucro_text, font=self.fonts.BODY_SMALL).grid(row=0, column=5, sticky="ew", pady=0)
        # --- FIM DA PARTE QUE FALTAVA ---

        self.trade_rows.append(row_frame)
        self.scrollable_frame._parent_canvas.yview_moveto(1.0)

    def clear_list(self):
        """Remove todas as linhas de trade da interface."""
        # Este método deve estar no nível da classe, não dentro de outro método.
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.trade_rows.clear()
        logging.info("Histórico de trades da UI foi limpo.")