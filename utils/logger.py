# utils/logger.py

import logging
from logging.handlers import RotatingFileHandler
import os
from .path_resolver import resource_path

def setup_loggers():
    """
    Configura o logger principal da aplicação.
    Saída: console e 'logs/bot_log.txt'.
    """
    # --- Formatação e Criação da Pasta de Log ---
    log_formatter = logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(message)s', datefmt='%H:%M:%S')
    
    log_dir = resource_path('logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # --- Handlers --- 
    # Handler para o arquivo de atividade geral (bot_log.txt)
    general_log_file = os.path.join(log_dir, 'bot_log.txt')
    general_handler = RotatingFileHandler(general_log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    general_handler.setFormatter(log_formatter)
    general_handler.setLevel(logging.DEBUG) # Definir nível DEBUG para o arquivo de log

    # Handler para o arquivo de trades (trade_log.txt)
    trade_log_file = os.path.join(log_dir, 'trade_log.txt')
    trade_handler = RotatingFileHandler(trade_log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    trade_handler.setFormatter(log_formatter)
    trade_handler.setLevel(logging.INFO) # Definir nível INFO para o arquivo de trades

    # Handler para o console (será usado pelo logger raiz)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO) # Manter INFO para o console para evitar poluição visual

    # --- Configuração do Logger Raiz ---
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Definir nível de log para o módulo iqoptionapi para evitar logs excessivos
    logging.getLogger('iqoptionapi').setLevel(logging.INFO)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(general_handler)
    root_logger.addHandler(console_handler)

    # --- Configuração do Logger de Trades ---
    trade_logger = logging.getLogger('trade_logger')
    trade_logger.setLevel(logging.INFO)
    trade_logger.addHandler(trade_handler)
    trade_logger.propagate = False # Evitar que os logs de trade sejam enviados para o logger raiz

    root_logger.info("="*50)
    root_logger.info("Loggers configurados. A aplicação está começando.")
    root_logger.info("="*50)

    return root_logger, trade_logger
