import customtkinter as ctk
import os
import logging
import threading
from utils.path_resolver import resource_path
from utils.config_manager import ConfigManager
from bot.app_controller import AppController
from .login_frame import LoginFrame
from .dashboard_frame import ModernDashboardFrame

class App(ctk.CTk):
    def __init__(self, trade_logger):
        super().__init__()
        
        self.controller = None
        self.config_manager = ConfigManager()
        self.trade_logger = trade_logger

        # Configuração de fontes
        font_path = resource_path(os.path.join("assets", "fonts", "Poppins-Regular.ttf"))
        if os.path.exists(font_path):
            ctk.FontManager.load_font(font_path)
            ctk.FontManager.load_font(resource_path(os.path.join("assets", "fonts", "Poppins-Bold.ttf")))
            self.font_family = "Poppins"
        else:
            self.font_family = "Arial"

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.title("Quantum Booster")
        self.geometry("700x500")
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Create a container frame for stacking frames
        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        # Instantiate LoginFrame and add it to frames dictionary
        login_frame = LoginFrame(self.container, self)
        self.frames[LoginFrame] = login_frame
        login_frame.grid(row=0, column=0, sticky="nsew")
        
        self.switch_frame(LoginFrame)

    def log_message(self, message, level="INFO"):
        """Encaminha mensagens para o sistema de log central."""
        log_map = {
            "INFO": logging.info,
            "WARNING": logging.warning,
            "ERROR": logging.error,
            "CRITICAL": logging.critical
        }
        log_function = log_map.get(level.upper(), logging.info)
        log_function(message)

    def _on_closing(self):
        """Função chamada ao fechar a janela para um desligamento seguro."""
        self.log_message("Fechando a aplicação...")
        if self.controller:
            # Executa o desligamento em uma thread para não travar a UI
            shutdown_thread = threading.Thread(target=self.controller.shutdown, daemon=True)
            shutdown_thread.start()
        self.destroy()

    def switch_frame(self, frame_class, credentials=None):
        # Hide all frames
        for frame in self.frames.values():
            frame.grid_forget()

        frame_to_show = self.frames.get(frame_class)

        if frame_class == ModernDashboardFrame:
            if not frame_to_show and credentials:
                self.geometry("1200x720")
                self.resizable(True, True)
                self.title("Quantum Booster | Dashboard")
                
                # Cria o controller e o passa para o Dashboard
                self.controller = AppController(credentials, self.config_manager, trade_logger=self.trade_logger)
                frame_to_show = ModernDashboardFrame(self.container, controller=self.controller, font_family=self.font_family)
                self.frames[ModernDashboardFrame] = frame_to_show
                frame_to_show.grid(row=0, column=0, sticky="nsew")
                
                # Inicia a conexão do bot em uma thread separada para não travar a UI
                threading.Thread(target=self.controller.connect, daemon=True).start()
            elif frame_to_show:
                self.geometry("1200x720")
                self.resizable(True, True)
                self.title("Quantum Booster | Dashboard")
            else:
                # If ModernDashboardFrame is requested without credentials and not already loaded,
                # it means an attempt to switch to it without proper login.
                # In this case, we might want to revert to LoginFrame or show an error.
                # For now, we'll just not switch and log a warning.
                self.log_message("Attempted to switch to Dashboard without credentials or existing instance.", level="WARNING")
                return # Do not proceed with tkraise if not properly set up

        elif frame_class == LoginFrame:
            self.geometry("700x500")
            self.resizable(False, False)
            self.title("Quantum Booster | Login")
            # LoginFrame is already pre-instantiated in __init__

        if frame_to_show:
            frame_to_show.tkraise()
            frame_to_show.grid(row=0, column=0, sticky="nsew") # Ensure it's gridded if it was hidden