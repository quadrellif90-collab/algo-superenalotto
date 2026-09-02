#!/usr/bin/env python3
import sys
import threading
import time

sys.path.insert(0, 'gateway')

print("Testing desktop_app.py functions...")

# Test desktop app imports
from desktop_app import (
    acquire_single_instance_lock, 
    release_single_instance_lock, 
    bring_existing_to_front,
    start_backend,
    wait_server,
    PORT,
    URL
)
print("Desktop app imports successful")

# Test lock functions
print("\nTesting lock functions...")
lock_fp = acquire_single_instance_lock()
if lock_fp:
    print("Lock acquired successfully")
    release_single_instance_lock(lock_fp)
    print("Lock released successfully")
else:
    print("Lock failed (expected if another instance is running)")

# Test server wait function
print("\nTesting server wait function...")
if callable(wait_server):
    print("wait_server function exists")
else:
    print("wait_server function not found")

print("\nDesktop app tests complete")