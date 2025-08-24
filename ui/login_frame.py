# ui/login_frame.py
import customtkinter as ctk
import os
import json
from .dashboard_frame import ModernDashboardFrame

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.criar_widgets()
        self.carregar_login_salvo()
    def fazer_login(self):
        email = self.entry_email.get()
        senha = self.entry_senha.get()
        tipo_conta_selecionado = self.seg_button_conta.get()
        if email and senha and tipo_conta_selecionado:
            if self.checkbox_salvar_login.get() == 1:
                with open("saved_login.json", "w") as f: json.dump({"email": email, "senha": senha}, f)
            elif os.path.exists("saved_login.json"): os.remove("saved_login.json")
            conta_api = 'PRACTICE' if tipo_conta_selecionado == 'DEMO' else 'REAL'
            credentials = {"email": email, "senha": senha, "conta": conta_api}
            self.master.switch_frame(ModernDashboardFrame, credentials=credentials)
        else:
            self.label_erro.configure(text="Por favor, preencha todos os campos.")
    def carregar_login_salvo(self):
        if os.path.exists("saved_login.json"):
            with open("saved_login.json", "r") as f:
                data = json.load(f)
                self.entry_email.insert(0, data.get("email", ""))
                self.entry_senha.insert(0, data.get("senha", ""))
                self.checkbox_salvar_login.select()
    def criar_widgets(self):
        frame_esquerdo = ctk.CTkFrame(self, width=300, fg_color="#2B0B3F", corner_radius=0)
        frame_esquerdo.pack(side="left", fill="y")
        ctk.CTkLabel(frame_esquerdo, text="SYNC", font=ctk.CTkFont(size=50, weight="bold")).pack(pady=(180, 0), padx=30)
        ctk.CTkLabel(frame_esquerdo, text="MT4  →  PYTHON", font=ctk.CTkFont(size=20)).pack(pady=(0, 180), padx=30)
        frame_direito = ctk.CTkFrame(self, fg_color="#242424")
        frame_direito.pack(side="right", fill="both", expand=True)
        form_frame = ctk.CTkFrame(frame_direito, fg_color="transparent")
        form_frame.pack(pady=20, padx=40, fill="both", expand=True)
        ctk.CTkLabel(form_frame, text="BEM-VINDO", font=ctk.CTkFont(size=32, weight="bold")).pack(pady=(0, 10))
        ctk.CTkLabel(form_frame, text="Insira suas credenciais", font=ctk.CTkFont(size=16), text_color="gray60").pack(pady=(0, 20))
        ctk.CTkLabel(form_frame, text="Email").pack(anchor="w")
        self.entry_email = ctk.CTkEntry(form_frame, placeholder_text="seuemail@exemplo.com", height=35)
        self.entry_email.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(form_frame, text="Senha").pack(anchor="w")
        self.entry_senha = ctk.CTkEntry(form_frame, placeholder_text="Digite sua senha", show="*", height=35)
        self.entry_senha.pack(fill="x", pady=(0, 10))
        self.checkbox_salvar_login = ctk.CTkCheckBox(form_frame, text="Salvar login")
        self.checkbox_salvar_login.pack(anchor="w", pady=10)
        ctk.CTkLabel(form_frame, text="Tipo de Conta").pack(anchor="w")
        self.seg_button_conta = ctk.CTkSegmentedButton(form_frame, values=["DEMO", "REAL"], height=35)
        self.seg_button_conta.set("DEMO")
        self.seg_button_conta.pack(fill="x", pady=(0, 10))
        self.label_erro = ctk.CTkLabel(form_frame, text="", text_color="red")
        self.label_erro.pack()
        ctk.CTkButton(form_frame, text="LOGIN", height=40, fg_color="#4B0082", hover_color="#6A0DAD", command=self.fazer_login).pack(fill="x", pady=10)