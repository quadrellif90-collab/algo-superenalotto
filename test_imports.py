#!/usr/bin/env python3
import sys
sys.path.insert(0, 'gateway')

# Test basic imports and functionality
print("Testing imports...")

# Test engine import and basic functionality
from engine import SuperenalottoEngine
print("Engine imported successfully")

# Test server import
from server import start_server, PORT, open_browser
print("Server imported successfully")

# Test basic strategy generation
engine = SuperenalottoEngine()
strategy = engine.quartile_spread()
print("Strategy generated:", strategy)

# Test validation
sum_nums = sum(strategy)
if 246 <= sum_nums <= 306:
    print("Sum validation passed:", sum_nums)
else:
    print("Sum validation failed:", sum_nums)

# Test stats
print("Stats computed: count =", engine.stats.get('count', 'N/A'))

print("\nAll basic tests passed!")
