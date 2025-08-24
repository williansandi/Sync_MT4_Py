import customtkinter as ctk
from ..styles.theme import ModernTheme
from ..styles.fonts import AppFonts

class SuperMetricCard(ctk.CTkFrame):
    def __init__(self, master, font_family="Arial"):
        super().__init__(master, fg_color=ModernTheme.BG_CARD, corner_radius=10)
        self.fonts = AppFonts(font_family)
        
        self.grid_columnconfigure(0, weight=1)

        # Título
        ctk.CTkLabel(self, text="📊 MÉTRICAS DA SESSÃO", font=self.fonts.CARD_TITLE, text_color=ModernTheme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        # Saldo Atual (P/L)
        self.balance_label = ctk.CTkLabel(self, text="P/L: R$ +0.00", font=self.fonts.CARD_VALUE, text_color=ModernTheme.ACCENT_GREEN)
        self.balance_label.grid(row=1, column=0, sticky="w", padx=15)

        # Separador
        ctk.CTkFrame(self, height=1, fg_color=ModernTheme.BG_SECONDARY).grid(row=2, column=0, sticky="ew", padx=15, pady=10)

        # Linha de Stops
        stops_frame = ctk.CTkFrame(self, fg_color="transparent")
        stops_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 10))
        stops_frame.grid_columnconfigure((0, 1), weight=1)

        self.stop_win_label = ctk.CTkLabel(stops_frame, text="Stop Win: R$ 100.00", font=self.fonts.CARD_SUBTITLE)
        self.stop_win_label.grid(row=0, column=0, sticky="w")
        self.stop_loss_label = ctk.CTkLabel(stops_frame, text="Stop Loss: R$ -100.00", font=self.fonts.CARD_SUBTITLE)
        self.stop_loss_label.grid(row=0, column=1, sticky="w")

    def update_metrics(self, profit_loss, stop_win, stop_loss, cifrao="$"):
        # Atualiza o P/L
        pl_text = f"P/L: {cifrao} {profit_loss:+.2f}"
        pl_color = ModernTheme.ACCENT_GREEN if profit_loss >= 0 else ModernTheme.ACCENT_RED
        self.balance_label.configure(text=pl_text, text_color=pl_color)
        
        # Atualiza os Stops
        self.stop_win_label.configure(text=f"Stop Win: {cifrao} {stop_win:.2f}")
        self.stop_loss_label.configure(text=f"Stop Loss: {cifrao} {-stop_loss:.2f}")