# main.py

from ui.app import App
from utils.logger import setup_logger
import logging

if __name__ == "__main__":
    setup_logger()
    
    # <-- MENSAGEM CORRIGIDA (SEM EMOJI) -->
    logging.info("=================================================")
    logging.info("==         QUANTUM TRADING ROBOT v4.0          ==")
    logging.info("==   Aguardando login para iniciar os sistemas   ==")
    logging.info("=================================================")
    
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        logging.critical(f"Erro fatal na aplicação: {e}", exc_info=True)
        
    logging.info("Aplicação finalizada.\n")