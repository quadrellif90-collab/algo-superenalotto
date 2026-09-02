#!/usr/bin/env python3
import csv
import random

print("Testing backtest_window_analysis.py functions...")

# Import the script's logic directly
from backtest_window_analysis import (
    valid, quartile_spread, last_digit_spread, fib_wheel, random_pure,
    STRAT, PREMI, roi_on_window, records
)

print(f"Loaded {len(records)} records from superenalotto.csv")

# Test validation function
print("\nTesting validation function...")
test_cases = [
    ([3, 17, 37, 43, 58, 80], False),  # Sum=238 < 246, invalid
    ([1, 2, 3, 4, 5, 6], False),  # Sum=21 < 246, invalid
    ([80, 81, 82, 83, 84, 85], False),  # Too many >80
    ([10, 10, 20, 20, 30, 40], False),  # Decadence has 2 duplicates
]

for nums, expected in test_cases:
    result = valid(nums)
    if result == expected:
        print(f"{nums}: {'Valid' if result else 'Invalid'}")
    else:
        print(f"{nums}: Expected {expected}, got {result}")

# Test strategy functions
print("\nTesting strategy functions...")

strategy_tests = [
    ("QuartileSpread", quartile_spread),
    ("LastDigitSpread", last_digit_spread),
    ("FibonacciWheel", fib_wheel),
    ("RandomPuro", random_pure),
]

for name, func in strategy_tests:
    try:
        result = func()
        if isinstance(result, list) and len(result) == 6 and all(1 <= n <= 90 for n in result):
            print(f"{name}: {result}")
        else:
            print(f"{name}: invalid output {result}")
    except Exception as e:
        print(f"{name}: {e}")

# Test ROI function
print("\nTesting ROI function...")
if len(records) > 0:
    test_window = records[:10]
    roi, net = roi_on_window(test_window, random_pure, n_sched=5)
    print(f"ROI calculation: ROI={roi:.2f}%, Net profit/loss={net}EUR")
    print(f"  Spent: 10 schedine x 5 each = 50 estrazioni")
    print(f"  Won: {net:+d}EUR")

print("\nBacktest analysis tests complete")