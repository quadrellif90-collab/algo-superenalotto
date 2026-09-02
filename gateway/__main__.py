"""Entry point per PyInstaller"""
import sys
import os

# Assicura che la directory del pacchetto sia nel path
if getattr(sys, 'frozen', False):
    # PyInstaller
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(bundle_dir)
    if parent not in sys.path:
        sys.path.insert(0, parent)

from gateway.server import start_server

if __name__ == "__main__":
    start_server()
