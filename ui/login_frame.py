import customtkinter as ctk
import os
import logging
import json
import base64
from PIL import Image
from .dashboard_frame import ModernDashboardFrame
from utils.path_resolver import resource_path

logging.basicConfig(level=logging.INFO)


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.master = master
        self.app_instance = app_instance # Store the App instance
        self.saved_login_path = resource_path("saved_login.json")
        self.criar_widgets()
        self.carregar_login_salvo()

    def fazer_login(self):
        email = self.entry_email.get()
        senha = self.entry_senha.get()
        tipo_conta_selecionado = self.seg_button_conta.get()
        if email and senha and tipo_conta_selecionado:
            if self.checkbox_salvar_login.get() == 1:
                # Codifica a senha antes de salvar
                encoded_senha = base64.b64encode(senha.encode('utf-8')).decode('utf-8')
                with open(self.saved_login_path, "w") as f: 
                    json.dump({"email": email, "senha": encoded_senha}, f)
            elif os.path.exists(self.saved_login_path): 
                os.remove(self.saved_login_path)
            
            conta_api = 'PRACTICE' if tipo_conta_selecionado == 'DEMO' else 'REAL'
            credentials = {"email": email, "senha": senha, "conta": conta_api}
            self.app_instance.switch_frame(ModernDashboardFrame, credentials=credentials)
        else:
            self.label_erro.configure(text="Por favor, preencha todos os campos.")

    def carregar_login_salvo(self):
        if os.path.exists(self.saved_login_path):
            try:
                with open(self.saved_login_path, "r") as f:
                    data = json.load(f)
                    self.entry_email.insert(0, data.get("email", ""))
                    
                    encoded_senha = data.get("senha", "")
                    if encoded_senha:
                        # Decodifica a senha ao carregar
                        decoded_senha = base64.b64decode(encoded_senha.encode('utf-8')).decode('utf-8')
                        self.entry_senha.insert(0, decoded_senha)
                    
                    self.checkbox_salvar_login.select()
            except (json.JSONDecodeError, IOError, base64.binascii.Error, UnicodeDecodeError):
                # Se o arquivo estiver corrompido, ilegível ou com base64 inválido, remove-o.
                if os.path.exists(self.saved_login_path):
                    os.remove(self.saved_login_path)

    def criar_widgets(self):
        # --- Layout Principal ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        frame_esquerdo = ctk.CTkFrame(self, fg_color="#2B0B3F", corner_radius=0)
        frame_esquerdo.grid(row=0, column=0, sticky="nsew")
        
        frame_direito = ctk.CTkFrame(self, fg_color="#242424")
        frame_direito.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # --- Frame Esquerdo (Branding) ---
        frame_esquerdo.grid_rowconfigure(0, weight=1)
        frame_esquerdo.grid_rowconfigure(2, weight=1)
        frame_esquerdo.grid_columnconfigure(0, weight=1)
        branding_frame = ctk.CTkFrame(frame_esquerdo, fg_color="transparent")
        branding_frame.grid(row=1, column=0)
        ctk.CTkLabel(branding_frame, text="SYNC", font=ctk.CTkFont(size=50, weight="bold")).pack(pady=(0,0))
        ctk.CTkLabel(branding_frame, text="MT4  →  PYTHON", font=ctk.CTkFont(size=20)).pack(pady=(0,0))

        # --- Frame Direito (Formulário) ---
        form_frame = ctk.CTkFrame(frame_direito, fg_color="transparent")
        form_frame.pack(pady=20, padx=40, fill="both", expand=True)
        
        form_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form_frame, text="BEM-VINDO", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(form_frame, text="Insira suas credenciais", font=ctk.CTkFont(size=16), text_color="gray60").grid(row=1, column=0, pady=(0, 20), sticky="ew")

        # --- Campos com Ícones ---
        # Carregar imagens
        try:
            email_icon_path = resource_path(os.path.join("icons", "email_icon.png"))
            password_icon_path = resource_path(os.path.join("icons", "password_icon.png"))
            email_icon = ctk.CTkImage(Image.open(email_icon_path), size=(20, 20))
            password_icon = ctk.CTkImage(Image.open(password_icon_path), size=(20, 20))
        except FileNotFoundError as e:
            logging.warning(f"Ícone de login não encontrado: {e}")
            email_icon, password_icon = None, None # Define como None se não encontrar

        # Campo de Email
        email_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        email_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        email_frame.grid_columnconfigure(1, weight=1)
        if email_icon:
            ctk.CTkLabel(email_frame, image=email_icon, text="").grid(row=0, column=0, padx=(0, 10))
        self.entry_email = ctk.CTkEntry(email_frame, placeholder_text="seuemail@exemplo.com", height=35)
        self.entry_email.grid(row=0, column=1, sticky="ew")

        # Campo de Senha
        senha_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        senha_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        senha_frame.grid_columnconfigure(1, weight=1)
        if password_icon:
            ctk.CTkLabel(senha_frame, image=password_icon, text="").grid(row=0, column=0, padx=(0, 10))
        self.entry_senha = ctk.CTkEntry(senha_frame, placeholder_text="Digite sua senha", show="*", height=35)
        self.entry_senha.grid(row=0, column=1, sticky="ew")

        # --- Controles Restantes ---
        self.checkbox_salvar_login = ctk.CTkCheckBox(form_frame, text="Salvar login")
        self.checkbox_salvar_login.grid(row=4, column=0, sticky="w", pady=10)
        
        ctk.CTkLabel(form_frame, text="Tipo de Conta").grid(row=5, column=0, sticky="w")
        self.seg_button_conta = ctk.CTkSegmentedButton(form_frame, values=["DEMO", "REAL"], height=35)
        self.seg_button_conta.set("DEMO")
        self.seg_button_conta.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        
        self.label_erro = ctk.CTkLabel(form_frame, text="", text_color="red")
        self.label_erro.grid(row=7, column=0, sticky="ew", pady=(0,5))
        
        ctk.CTkButton(form_frame, text="LOGIN", height=40, fg_color="#4B0082", hover_color="#6A0DAD", command=self.fazer_login).grid(row=8, column=0, sticky="ew", pady=10)