#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point per il server backend (usato da desktop_app.py)"""
import sys
import os

# In frozen PyInstaller, i moduli gateway sono in _MEIPASS (hiddenimports)
# In dev mode, gateway/ è nella stessa directory del progetto
if getattr(sys, 'frozen', False):
    # PyInstaller: moduli già in sys.path tramite hiddenimports
    pass
else:
    # Dev mode: aggiungi la directory progetto al path
    project_dir = os.path.dirname(os.path.abspath(__file__))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

# Avvia il server (usa sempre il prefisso gateway. per compatibilità frozen)
from gateway.server import start_server

if __name__ == '__main__':
    start_server()
