#!/usr/bin/env python3
"""
Verify statistical analysis on latest SuperEnalotto data
"""
import csv
from collections import Counter
from datetime import datetime

# Load data
records = []
with open('superenalotto.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            nums = sorted([int(row['n1']), int(row['n2']), int(row['n3']), 
                          int(row['n4']), int(row['n5']), int(row['n6'])])
            records.append({'nums': nums, 'data': row['data']})
        except:
            continue

print(f'Total records: {len(records)}')
print(f'Date range: {records[0]["data"]} to {records[-1]["data"]}')

# Statistical analysis
all_nums = [n for r in records for n in r['nums']]
freq = Counter(all_nums)
print(f'Number frequency stats: min={min(freq.values())}, max={max(freq.values())}, avg={sum(freq.values())/90:.1f}')

# Sum analysis
sums = [sum(r['nums']) for r in records]
mean_sum = sum(sums)/len(sums)
median_sum = sorted(sums)[len(sums)//2]
std_sum = (sum((s-mean_sum)**2 for s in sums)/len(sums))**0.5
print(f'Sum stats: mean={mean_sum:.2f}, median={median_sum}, std={std_sum:.2f}')

# Prime analysis
primes = {2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89}
prime_counts = Counter(sum(1 for n in r['nums'] if n in primes) for r in records)
print(f'Prime distribution: {dict(sorted(prime_counts.items()))}')

# Low/Mid/High analysis
low_mid_high = Counter()
for r in records:
    low = sum(1 for n in r['nums'] if n <= 30)
    mid = sum(1 for n in r['nums'] if 31 <= n <= 60)
    high = sum(1 for n in r['nums'] if n >= 61)
    low_mid_high[(low, mid, high)] += 1
print(f'Top patterns (low,mid,high): {low_mid_high.most_common(5)}')

# Expected vs Observed for Chi-Square
expected = len(records) * 6 / 90  # ~282.5 per number
chi_sq = sum((freq[n] - expected)**2 / expected for n in range(1, 91))
print(f'Chi-square statistic: {chi_sq:.2f} (df=89, critical=112.0 at p=0.05)')
print(f'Chi-square p-value interpretation: {"Significant" if chi_sq > 112 else "Not significant"}')

# Parity analysis
parity_dist = Counter()
for r in records:
    even = sum(1 for n in r['nums'] if n % 2 == 0)
    parity_dist[(even, 6-even)] += 1
print(f'Top parity patterns (even,odd): {parity_dist.most_common(5)}')

# Decade analysis
decade_dist = Counter()
for r in records:
    decades = tuple(sorted(Counter(n // 10 for n in r['nums']).keys()))
    decade_dist[decades] += 1
print(f'Top decade patterns: {decade_dist.most_common(5)}')

print('\n=== BACKTEST VERIFICATION ===')

# Simple backtest simulation
import random

random.seed(42)
PRIMES_SET = {2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89}

def valid_constraints(nums):
    s = sum(nums)
    if not (246 <= s <= 306):
        return False
    decades = Counter(n // 10 for n in nums)
    if max(decades.values()) > 2:
        return False
    if sum(1 for n in nums if n > 80) > 1:
        return False
    return True

def quartile_spread():
    qr = [(1, 22), (23, 45), (46, 67), (68, 90)]
    for _ in range(2000):
        alloc = [1, 1, 1, 1]
        extra = 2
        while extra > 0:
            alloc[random.randrange(4)] += 1
            extra -= 1
        nums = []
        for qi in range(4):
            lo, hi = qr[qi]
            nums.extend(random.sample(range(lo, hi + 1), alloc[qi]))
        nums = sorted(nums)
        if valid_constraints(nums):
            return nums
    return sorted(random.sample(range(1, 91), 6))

def hot_cold_spread(records):
    if not records:
        return sorted(random.sample(range(1, 91), 6))
    recent = records[-10:]
    hot = sorted(set(n for r in recent for n in r['nums']))
    cold = sorted(set(range(1, 91)) - set(hot))
    n_hot = min(3, len(hot))
    n_cold = min(3, len(cold))
    selected = random.sample(hot, n_hot) + random.sample(cold, n_cold)
    selected = sorted(selected)
    remaining = 6 - len(selected)
    if remaining > 0:
        pool = [x for x in range(1, 91) if x not in selected]
        selected = sorted(selected + random.sample(pool, remaining))
    return selected

def random_pure():
    return sorted(random.sample(range(1, 91), 6))

PREMI = {2: 5, 3: 25, 4: 296, 5: 25847, 5.5: 100000, 6: 1000000}

def backtest_strategy(records, strategy_fn, name):
    random.seed(42)
    spent = 0
    won = 0
    m2 = m3 = m4 = 0
    
    for i, rec in enumerate(records):
        # Use records before this one for strategy
        history = records[:i] if i > 0 else []
        ticket = strategy_fn(history)
        matches = len(set(ticket) & set(rec['nums']))
        spent += 1
        
        if matches >= 2:
            premio = PREMI.get(matches, 0)
            won += premio
            if matches == 2: m2 += 1
            elif matches == 3: m3 += 1
            elif matches >= 4: m4 += 1
    
    roi = ((won - spent) / spent * 100) if spent > 0 else 0
    m3_rate = (m3 / spent * 1000) if spent > 0 else 0
    
    print(f'{name}:')
    print(f'  M2={m2}, M3={m3}, M4={m4}')
    print(f'  Spent={spent}, Won={won}, Net={won-spent}')
    print(f'  ROI={roi:.2f}%, M3+/1000={m3_rate:.2f}')
    return {'name': name, 'm2': m2, 'm3': m3, 'm4': m4, 'spent': spent, 'won': won, 'roi': roi, 'm3_rate': m3_rate}

print('\nTesting strategies on', len(records), 'draws:')

results = []
results.append(backtest_strategy(records, lambda h: random_pure(), 'Random (baseline)'))
results.append(backtest_strategy(records, lambda h: quartile_spread(), 'QuartileSpread'))
results.append(backtest_strategy(records, lambda h: hot_cold_spread(h), 'HotCold'))

# Find best by M3 rate
best = max(results, key=lambda x: x['m3_rate'])
print(f'\nBest by M3 rate: {best["name"]} ({best["m3_rate"]:.2f} M3+/1000)')

# Expected values
print('\n=== EXPECTED VALUES ===')
print(f'Expected M2: {len(records)/22:.1f} (1 in 22)')
print(f'Expected M3: {len(records)/327:.1f} (1 in 327)')
print(f'Expected M4: {len(records)/11180:.1f} (1 in 11180)')

# House edge calculation
total_expected_return = (len(records) * (1/22 * 5 + 1/327 * 25 + 1/11180 * 296))
print(f'\nExpected total return (ADM odds): EUR {total_expected_return:.2f}')
print(f'Actual total spent: EUR {len(records)}')
print(f'House edge: {(1 - total_expected_return/len(records)) * 100:.1f}%')
