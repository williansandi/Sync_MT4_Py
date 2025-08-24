# ui/components/financial_summary_card.py

import customtkinter as ctk
from ..styles.theme import ModernTheme
from ..styles.fonts import AppFonts

class FinancialSummaryCard(ctk.CTkFrame):
    def __init__(self, master, font_family="Arial"):
        super().__init__(master, fg_color=ModernTheme.BG_CARD, corner_radius=10)
        self.fonts = AppFonts(font_family)
        
        # --- (ALTERADO) Configuração de um grid único com 5 colunas ---
        # Col 0: Dado 1 | Col 1: Separador | Col 2: Dado 2 | Col 3: Separador | Col 4: Dado 3
        self.grid_columnconfigure((0, 2, 4), weight=1) # Colunas de dados expandem
        self.grid_columnconfigure((1, 3), weight=0)   # Colunas de separador não expandem

        # 1. Título Principal (centralizado)
        title_label = ctk.CTkLabel(self, text="RESUMO FINANCEIRO", font=self.fonts.CARD_TITLE, text_color=ModernTheme.TEXT_SECONDARY)
        title_label.grid(row=0, column=0, columnspan=5, sticky="ew", padx=15, pady=(10, 5))

        # 2. Primeira linha de dados (Saldo e P/L)
        self.balance_label = ctk.CTkLabel(self, text="Saldo: -", font=self.fonts.BODY_NORMAL)
        self.balance_label.grid(row=1, column=0, sticky="w", padx=15, pady=2)
        
        separator1 = ctk.CTkLabel(self, text="|", font=self.fonts.BODY_SMALL, text_color=ModernTheme.TEXT_MUTED)
        separator1.grid(row=1, column=1, sticky="ew")

        self.pl_label = ctk.CTkLabel(self, text="P/L Hoje: -", font=self.fonts.BODY_NORMAL)
        self.pl_label.grid(row=1, column=2, columnspan=3, sticky="w", padx=15, pady=2)

        # 3. Segunda linha de dados (Wins, Loss, Winrate)
        self.wins_label = ctk.CTkLabel(self, text="Wins: 0", font=self.fonts.BODY_NORMAL)
        self.wins_label.grid(row=2, column=0, sticky="w", padx=15, pady=(2, 15))

        separator2 = ctk.CTkLabel(self, text="|", font=self.fonts.BODY_SMALL, text_color=ModernTheme.TEXT_MUTED)
        separator2.grid(row=2, column=1, sticky="ew", pady=(0, 15))

        self.loss_label = ctk.CTkLabel(self, text="Loss: 0", font=self.fonts.BODY_NORMAL)
        self.loss_label.grid(row=2, column=2, sticky="w", padx=15, pady=(2, 15))

        separator3 = ctk.CTkLabel(self, text="|", font=self.fonts.BODY_SMALL, text_color=ModernTheme.TEXT_MUTED)
        separator3.grid(row=2, column=3, sticky="ew", pady=(0, 15))

        self.winrate_label = ctk.CTkLabel(self, text="Winrate: -", font=self.fonts.BODY_NORMAL)
        self.winrate_label.grid(row=2, column=4, sticky="w", padx=15, pady=(2, 15))

    def update_summary(self, data):
        """Atualiza todos os valores do card com um dicionário de dados."""
        # data = {'balance': 1000, 'pl_today': 50, 'wins': 5, 'losses': 2, 'winrate': 71.4, 'cifrao': '$'}
        
        cifrao = data.get('cifrao', '$')
        
        # Atualiza Saldo e P/L
        self.balance_label.configure(text=f"Saldo: {cifrao} {data.get('balance', 0):.2f}")
        pl_today = data.get('pl_today', 0)
        pl_color = ModernTheme.ACCENT_GREEN if pl_today >= 0 else ModernTheme.ACCENT_RED
        self.pl_label.configure(text=f"P/L Hoje: {cifrao} {pl_today:+.2f}", text_color=pl_color)

        # Atualiza Wins, Loss e Winrate
        self.wins_label.configure(text=f"Wins: {data.get('wins', 0)}")
        self.loss_label.configure(text=f"Loss: {data.get('losses', 0)}")
        self.winrate_label.configure(text=f"Winrate: {data.get('winrate', 0):.2f}%")