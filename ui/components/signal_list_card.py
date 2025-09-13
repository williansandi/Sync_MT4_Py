# ui/components/signal_list_card.py

import customtkinter as ctk
from ..styles.theme import ModernTheme
from ..styles.fonts import AppFonts

class SignalListCard(ctk.CTkFrame):
    def __init__(self, master, font_family="Arial", on_delete_signal=None):
        super().__init__(master, fg_color="transparent")
        self.fonts = AppFonts(font_family)
        self.on_delete_signal = on_delete_signal # Callback para notificar a exclusão

        self.column_config = {
            "status":   {"weight": 0, "minsize": 30, "stretch": False, "text": "STATUS"},
            "time":     {"weight": 1, "minsize": 80, "stretch": True,  "text": "HORÁRIO"},
            "asset":    {"weight": 2, "minsize": 120, "stretch": True, "text": "ATIVO"},
            "action":   {"weight": 1, "minsize": 80, "stretch": True,  "text": "DIREÇÃO"},
            "result":   {"weight": 2, "minsize": 100, "stretch": True, "text": "RESULTADO"},
            "delete":   {"weight": 0, "minsize": 30, "stretch": False, "text": ""} # Coluna para o botão X
        }
        self.signal_rows = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color=ModernTheme.BG_CARD, corner_radius=10, height=30)
        header_frame.grid(row=0, column=0, sticky="ew")
        self._create_headers(header_frame)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color=ModernTheme.BG_CARD, corner_radius=10)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        
    def _apply_column_config(self, parent_frame):
        for i, config in enumerate(self.column_config.values()):
            parent_frame.grid_columnconfigure(i, weight=config["weight"], minsize=config.get("minsize", 0))

    def _create_headers(self, parent):
        self._apply_column_config(parent)
        header_font = (self.fonts.FAMILY, 10, "bold")
        text_color = ModernTheme.TEXT_MUTED
        for i, config in enumerate(self.column_config.values()):
            ctk.CTkLabel(parent, text=config["text"], font=header_font, text_color=text_color).grid(row=0, column=i, sticky="ew", padx=5)

    def populate_signals(self, signal_list):
        # Limpa a interface antes de popular
        self.clear_list()

        if not signal_list:
            ctk.CTkLabel(self.scrollable_frame, text="Nenhum sinal carregado.").pack(pady=20)
            return

        for signal in signal_list:
            self._create_signal_row(signal)

    def _create_signal_row(self, signal):
        """Cria uma única linha de sinal na interface."""
        row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=ModernTheme.BG_SECONDARY, height=30, corner_radius=8)
        row_frame.pack(fill="x", padx=5, pady=3)
        row_frame.pack_propagate(False)
        self._apply_column_config(row_frame)
        
        status_label = ctk.CTkLabel(row_frame, text="●", font=("Arial", 16), text_color="gray")
        status_label.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(row_frame, text=signal['time'], font=self.fonts.BODY_SMALL).grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(row_frame, text=signal['asset'], font=self.fonts.BODY_SMALL).grid(row=0, column=2, sticky="ew")
        ctk.CTkLabel(row_frame, text=f"M{signal.get('timeframe', 1)}", font=self.fonts.BODY_SMALL).grid(row=0, column=3, sticky="ew")
        direcao_text = "🔼 CALL" if signal['action'] == 'call' else "🔽 PUT"
        ctk.CTkLabel(row_frame, text=direcao_text, font=self.fonts.BODY_SMALL).grid(row=0, column=4, sticky="ew")
        result_label = ctk.CTkLabel(row_frame, text="-", font=self.fonts.BODY_SMALL, text_color=ModernTheme.TEXT_MUTED)
        result_label.grid(row=0, column=5, sticky="ew")
        
        # --- (NOVO) Botão de exclusão ---
        delete_button = ctk.CTkButton(row_frame, text="✕", font=("Arial", 14), width=20, height=20, 
                                      fg_color="transparent", text_color=ModernTheme.TEXT_MUTED, hover_color="#52525b",
                                      command=lambda sid=signal['id']: self._delete_signal_row(sid))
        delete_button.grid(row=0, column=6, padx=5)
        
        self.signal_rows[signal['id']] = {
            "frame": row_frame, 
            "status_widget": status_label, 
            "result_widget": result_label
        }

    def _delete_signal_row(self, signal_id):
        """Remove a linha da UI e notifica a tela principal."""
        if signal_id in self.signal_rows:
            self.signal_rows[signal_id]["frame"].destroy()
            del self.signal_rows[signal_id]
            if self.on_delete_signal:
                self.on_delete_signal(signal_id) # Chama o callback

    def update_signal_status(self, signal_id, result_info):
        if signal_id in self.signal_rows:
            # ... (código sem alterações)
            row_widgets = self.signal_rows[signal_id]
            profit = result_info.get("profit", 0)
            cifrao = result_info.get("cifrao", "$")
            if profit > 0:
                status_color = ModernTheme.ACCENT_GREEN
                result_text = f"WIN ({cifrao}{profit:+.2f})"
            else:
                status_color = ModernTheme.ACCENT_RED
                result_text = f"LOSS ({cifrao}{profit:+.2f})"
            row_widgets["status_widget"].configure(text_color=status_color)
            row_widgets["result_widget"].configure(text=result_text, text_color=status_color)
            
    def clear_list(self):
        """Remove todos os sinais da interface."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.signal_rows.clear()