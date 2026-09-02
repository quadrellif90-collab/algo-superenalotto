#!/usr/bin/env python3

# Test launcher.py functions
import threading
import time
import sys
import os

# Add gateway to path
sys.path.insert(0, 'gateway')

print("Testing launcher.py functions...")

# Test lock functions
from launcher import acquire_lock, release_lock, bring_existing_to_front, wait_server, start_backend

# Test acquire_lock (should work since no other instance)
print("Testing lock acquisition...")
lock_fp = acquire_lock()
if lock_fp:
    print("Lock acquired successfully")
    # Test release_lock
    release_lock(lock_fp)
    print("Lock released successfully")
else:
    print("Lock failed (expected if another instance is running)")

print("Launcher tests complete")
