import sqlite3
import logging
from .path_resolver import resource_path

class ConfigManager:
    def __init__(self, db_path='config.db'):
        self.db_path = resource_path(db_path)
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

        # Remove old keys to avoid conflicts
        old_keys_to_remove = ['management_type', 'niveis_martingale', 'max_ciclos', 'payout_recuperacao', 'conservative_recovery_percentage']
        for old_key in old_keys_to_remove:
            cursor.execute("DELETE FROM settings WHERE key=?", (old_key,))

        # Add new keys
        new_keys = {
            'perfil_de_risco': 'MODERADO',
            'conservador_recuperacao': '50', 'conservador_max_gales': '1', 'conservador_max_ciclos': '3',
            'moderado_recuperacao': '75', 'moderado_max_gales': '2', 'moderado_max_ciclos': '2',
            'agressivo_recuperacao': '110', 'agressivo_max_gales': '2', 'agressivo_max_ciclos': '2',
            'usar_filtro_noticias': 'S', 
            'minutos_antes_noticia': '15', 
            'minutos_depois_noticia': '15',
            'usar_ciclos': 'S',
            'fator_martingale': '2.1',
            'usar_soros': 'N',
            'niveis_soros': '3',
            'tipo': 'binary', 
            'valor_entrada': '5', 
            'stop_win': '100', 
            'stop_loss': '100'
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
