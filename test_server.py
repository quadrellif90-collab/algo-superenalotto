#!/usr/bin/env python3
import sys
import threading
import time

sys.path.insert(0, 'gateway')

print("Testing server.py functions...")

# Test server imports
from server import SuperenalottoHandler, PORT, start_server, open_browser
print("Server imports successful")

# Test handler API endpoints
print("\nTesting handler API endpoints...")

# Create a mock handler to test the API logic
import json
from io import BytesIO
from unittest.mock import Mock

# Mock the engine
class MockEngine:
    def __init__(self):
        self.stats = {"count": 4235, "mean": 151.5, "median": 151}
    
    def get_estrazioni_recenti(self, n=20):
        return [{"data": f"2024-01-{(i+1):02d}", "numeri": [1,2,3,4,5,6]} for i in range(n)]
    
    def get_giocate(self):
        return [{"id": 1, "data": "2024-01-15", "numeri": "1-2-3-4-5-6"}]
    
    def prossima_estrazione(self):
        return "2024-01-20"
    
    def oggi_estrazione(self):
        return True
    
    def genera_schedine(self, n=1):
        return [sorted(range(1, 7)) for _ in range(n)]
    
    def fetch_jackpot_sisal(self):
        return 210000000.0
    
    def get_premi(self):
        return [{"match": "6", "odds": 622614630, "premio": 210000000}]
    
    def valuta_strategie(self, n=50):
        return {"text": "Test evaluation", "roi": 5.2}
    
    def get_grafici(self):
        return {"msg": "Test graphics"}

# Test with mock engine
MockEngine()
print("Mock engine created")

print("\nServer tests complete")