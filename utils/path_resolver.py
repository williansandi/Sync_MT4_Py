# utils/path_resolver.py
import sys
import os

def resource_path(relative_path):
    """Sempre retorna o caminho absoluto a partir da raiz do projeto (onde este arquivo está)."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Caminho absoluto da pasta do projeto (onde está este arquivo)
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.abspath(os.path.join(base_path, '..'))
    return os.path.join(base_path, relative_path)