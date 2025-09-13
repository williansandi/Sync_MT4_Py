# main.py
import tkinter.font

from ui.app import App
from utils.logger import setup_loggers
import logging

if __name__ == "__main__":
    root_logger, trade_logger = setup_loggers()
    
    # <-- MENSAGEM CORRIGIDA (SEM EMOJI) -->
    root_logger.info("=================================================")
    root_logger.info("==         QUANTUM TRADING ROBOT v4.0          ==")
    root_logger.info("==   Aguardando login para iniciar os sistemas ==")
    root_logger.info("=================================================")
    
    try:
        app = App(trade_logger=trade_logger)
        app.mainloop()
    except Exception as e:
        root_logger.critical(f"Erro fatal na aplicação: {e}", exc_info=True)
        
    root_logger.info("Aplicação finalizada.\n")
