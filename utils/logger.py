# utils/logger.py

import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger():
    """Configura o logger principal para salvar em um arquivo com rotação."""
    
    # Garante que a pasta de logs exista
    if not os.path.exists('logs'):
        os.makedirs('logs')

    log_file = 'logs/bot_activity.log'

    # Configura o formato da mensagem de log
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Configura o handler para rotacionar o arquivo de log quando ele atingir 5MB
    # Mantém até 5 arquivos de backup.
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    handler.setFormatter(log_formatter)

    # Pega o logger raiz e adiciona o handler
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Evita adicionar handlers duplicados se a função for chamada mais de uma vez
    if not logger.handlers:
        logger.addHandler(handler)
        
    logging.info("="*50)
    logging.info("Logger profissional iniciado. A aplicação está começando.")
    logging.info("="*50)