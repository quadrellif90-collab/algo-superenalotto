#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point per il server backend (usato da desktop_app.py)"""
import sys
import os

# Aggiungi gateway al path
if getattr(sys, 'frozen', False):
    gateway_dir = os.path.join(os.path.dirname(sys.executable), 'gateway')
else:
    gateway_dir = os.path.join(os.path.dirname(__file__), 'gateway')

if gateway_dir not in sys.path:
    sys.path.insert(0, gateway_dir)

# Avvia il server
from server import start_server

if __name__ == '__main__':
    start_server()
