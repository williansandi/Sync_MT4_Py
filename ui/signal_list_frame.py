# ui/signal_list_frame.py

import customtkinter as ctk
from tkinter import filedialog  # Importação corrigida para o filedialog
from .styles.theme import ModernTheme
from .components.signal_list_card import SignalListCard
import uuid
import logging

class SignalListFrame(ctk.CTkFrame):
    # --- MODIFICADO: Adicionado log_callback no construtor ---
    def __init__(self, master, log_callback=None):
        super().__init__(master, fg_color="transparent")
        self.signals = []
        # --- NOVO: Armazena a função de log ---
        self.log_callback = log_callback or (lambda msg, tag: logging.info(f"[{tag}] {msg}"))

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        control_frame = ctk.CTkFrame(self, fg_color=ModernTheme.BG_CARD, corner_radius=10)
        control_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 10))

        load_button = ctk.CTkButton(control_frame, text="📂 Carregar Arquivo (.txt)", command=self._load_signal_file)
        load_button.pack(side="left", padx=15, pady=10)
        
        clear_button = ctk.CTkButton(control_frame, text="🗑️ Limpar Lista", command=self._clear_signal_list,
                                     fg_color="#52525b", hover_color="#71717a")
        clear_button.pack(side="left", padx=0, pady=10)

        self.file_label = ctk.CTkLabel(control_frame, text="Nenhum arquivo carregado.", text_color=ModernTheme.TEXT_MUTED)
        self.file_label.pack(side="left", padx=15, pady=10)

        self.signal_card = SignalListCard(self, font_family="Arial", on_delete_signal=self._handle_signal_deletion)
        self.signal_card.grid(row=1, column=0, sticky="nsew", padx=5)

    def _load_signal_file(self):
        # Usando o filedialog do tkinter diretamente
        file_path = filedialog.askopenfilename(title="Selecione um arquivo de sinais", filetypes=(("Arquivos de Texto", "*.txt"), ("Todos os arquivos", "*.*")))
        if not file_path: return

        self.signals.clear()
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    
                    parts = line.split(';')
                    if len(parts) >= 3:
                        timeframe = 1 # Padrão de 1 minuto
                        if len(parts) == 4:
                            try:
                                timeframe = int(parts[3])
                            except (ValueError, IndexError):
                                self.log_callback(f"Timeframe inválido na linha '{line}', usando padrão M1.", "AVISO")
                        
                        action = parts[2].lower().replace("venda", "put").replace("compra", "call")
                        
                        self.signals.append({
                            "id": str(uuid.uuid4()), 
                            "time": parts[0], 
                            "asset": parts[1],
                            "action": action, 
                            "timeframe": timeframe,
                            "status": "pending"
                        })
                    else:
                        self.log_callback(f"Linha ignorada (formato inválido): '{line}'", "AVISO")
            
            self.file_label.configure(text=f"{len(self.signals)} sinais carregados de: ...{file_path[-30:]}")
            self.signal_card.populate_signals(self.signals)
            
            # --- ADICIONADO: Mensagem no terminal ---
            if self.log_callback:
                self.log_callback(f"{len(self.signals)} sinais carregados com sucesso.", "SINAIS")
                self.log_callback("Vá para a tela 'Estratégias' para iniciar as operações.", "INFO")

        except Exception as e:
            self.file_label.configure(text=f"Erro ao ler o arquivo: {e}", text_color="red")
            if self.log_callback:
                self.log_callback(f"Falha ao carregar lista de sinais: {e}", "ERRO")

    def _clear_signal_list(self):
        """Limpa a lista de dados e a interface."""
        self.signals.clear()
        self.signal_card.clear_list()
        self.file_label.configure(text="Lista de sinais limpa.")
        # Adiciona uma mensagem na lista vazia
        ctk.CTkLabel(self.signal_card.scrollable_frame, text="Carregue um novo arquivo de sinais.").pack(pady=20)
        if self.log_callback:
            self.log_callback("Lista de sinais foi limpa.", "INFO")

    def _handle_signal_deletion(self, signal_id):
        """Remove o sinal da lista de dados quando o 'X' é clicado."""
        self.signals = [s for s in self.signals if s['id'] != signal_id]
        self.file_label.configure(text=f"{len(self.signals)} sinais restantes na lista.")

    def get_signals(self):
        return self.signals

    def update_signal_status(self, signal_id, result_info):
        self.signal_card.update_signal_status(signal_id, result_info)