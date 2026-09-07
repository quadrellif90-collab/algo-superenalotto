#!/usr/bin/env python3
import sys
import threading
import time

print("Testing desktop app functions...")

# Test launcher imports (funzioni corrette da launcher.py)
from launcher import acquire_lock, release_lock, bring_existing_to_front, wait_server, start_backend, PORT, URL
print("Launcher imports successful")

# Test lock functions
print("\nTesting lock functions...")
lock_fp = acquire_lock()
if lock_fp:
    print("Lock acquired successfully")
    release_lock(lock_fp)
    print("Lock released successfully")
else:
    print("Lock failed (expected if another instance is running)")

# Test bring_existing_to_front
print("\nTesting bring_existing_to_front...")
if callable(bring_existing_to_front):
    print("bring_existing_to_front function exists")
    bring_existing_to_front()
    print("bring_existing_to_front executed")
else:
    print("bring_existing_to_front function not found")

# Test server wait function
print("\nTesting server wait function...")
if callable(wait_server):
    print("wait_server function exists")
else:
    print("wait_server function not found")

print("\nDesktop app tests complete")