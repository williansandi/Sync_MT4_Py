# ui/app.py

import customtkinter as ctk
from .login_frame import LoginFrame
from .dashboard_frame import ModernDashboardFrame
import os

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # ... (seu código de inicialização de fonte, etc.)
        font_path = os.path.join("assets", "fonts", "Poppins-Regular.ttf")
        if os.path.exists(font_path):
            ctk.FontManager.load_font(font_path)
            ctk.FontManager.load_font(os.path.join("assets", "fonts", "Poppins-Bold.ttf"))
            self.font_family = "Poppins"
        else:
            self.font_family = "Arial"

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.title("Quantum Booster")
        self.geometry("700x500")
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self._frame = None
        self.switch_frame(LoginFrame)

    def _on_closing(self):
        """Função chamada ao fechar a janela para um desligamento seguro."""
        # (ALTERADO) Chama o método de desligamento completo do dashboard
        if hasattr(self._frame, 'shutdown_completo'):
            self._frame.shutdown_completo()
        self.destroy()

    def switch_frame(self, frame_class, credentials=None):
        if self._frame is not None: self._frame.destroy()
        if frame_class == ModernDashboardFrame:
            self.geometry("1200x720")
            self.resizable(True, True)
            self.title("Quantum Booster | Dashboard")
            self._frame = frame_class(self, credentials=credentials, font_family=self.font_family)
        else:
            self.geometry("700x500")
            self.resizable(False, False)
            self.title("Quantum Booster | Login")
            self._frame = frame_class(self)
        self._frame.pack(fill="both", expand=True)