#!/usr/bin/env python3
import sys
sys.path.insert(0, 'gateway')

from engine import SuperenalottoEngine

# Test game logic and verification
engine = SuperenalottoEngine()
print('Testing game logic and verification...')

# Test validation
valid_nums = [3, 17, 37, 43, 58, 80]
if engine._valid_constraints(valid_nums):
    print('Valid constraints passed')
else:
    print('Valid constraints failed')

# Check what records exist in the database
print('First few records in database:')
for i, record in enumerate(engine.records[:5]):
    print(' ', i+1, '.', record)

# Test verifying against the first record
if engine.records:
    first_record = engine.records[0]
    test_result = engine.verifica_giocata(first_record['data'], first_record['nums'])
    print(f'Testing verification against record {first_record["data"]}: {first_record["nums"]}')
    print('Result:', test_result)

# Test stats
if engine.stats and 'count' in engine.stats:
    print('Stats computed: count =', engine.stats['count'])
else:
    print('Stats not computed')

print('Game logic tests complete')
