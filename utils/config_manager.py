# utils/config_manager.py

import sqlite3
import logging

class ConfigManager:
    def __init__(self, db_path='config.db'):
        self.db_path = db_path
        self._setup_database()

    def _setup_database(self):
        """Cria a tabela de configurações e a popula com valores padrão se estiver vazia."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        cursor.execute("SELECT COUNT(*) FROM settings")
        if cursor.fetchone()[0] == 0:
            logging.info("Banco de dados de configuração vazio. Populando com valores padrão.")
            default_settings = {
                # Seção AJUSTES
                'tipo': 'binary', 'valor_entrada': '5', 'stop_win': '100', 'stop_loss': '100',
                # Seção MARTINGALE
                'usar_ciclos': 'S',
                'management_type': 'agressivo',
                'niveis_martingale': '1', 
                'fator_martingale': '2.1',
                'conservative_recovery_percentage': '50',
                # Seção SOROS
                'usar_soros': 'S', 'niveis_soros': '3',
                # --- (NOVO) Seção Filtro de Notícias ---
                'usar_filtro_noticias': 'S',
                'minutos_antes_noticia': '15',
                'minutos_depois_noticia': '15'
            }
            cursor.executemany("INSERT INTO settings (key, value) VALUES (?, ?)", default_settings.items())
        
        # --- (NOVO) Adiciona as chaves de notícias se elas não existirem (para atualizações) ---
        new_keys = {
            'usar_filtro_noticias': 'S', 
            'minutos_antes_noticia': '15', 
            'minutos_depois_noticia': '15',
            'management_type': 'agressivo',
            'usar_ciclos': 'S',
            'conservative_recovery_percentage': '50'
        }
        for key, value in new_keys.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

        conn.commit()
        conn.close()

    def get_all_settings(self):
        """Retorna todas as configurações como um dicionário."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        settings_dict = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        logging.info("Configurações carregadas do banco de dados.")
        return settings_dict

    def save_setting(self, key, value):
        """Salva ou atualiza uma configuração específica."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
        logging.info(f"Configuração salva: {key} = {value}")

    def save_settings(self, settings_dict):
        """Salva um dicionário de configurações no banco de dados."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for key, value in settings_dict.items():
            cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            logging.info(f"Configuração salva: {key} = {value}")
            
        conn.commit()
        conn.close()