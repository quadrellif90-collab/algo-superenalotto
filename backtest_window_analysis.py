# Backtest analisi finestra: quale N massimizza affidabilita' Auto?
# e la logica "antiumana" (copertura spaziale) batte il caso?
import csv, random
from collections import Counter

random.seed(42)
PATH = "superenalotto.csv"

# carica records (formato A: data,conc,n1..n6,jolly,star)
records = []
with open(PATH, encoding="utf-8") as f:
    r = csv.reader(f); next(r)
    for row in r:
        if len(row) < 9: continue
        try:
            nums = [int(row[2]), int(row[3]), int(row[4]), int(row[5]), int(row[6]), int(row[7])]
            records.append({"nums": nums})
        except (ValueError, IndexError):
            try:
                nums = [int(row[4]), int(row[5]), int(row[6]), int(row[7]), int(row[8]), int(row[9])]
                records.append({"nums": nums})
            except (ValueError, IndexError):
                continue

print(f"Records totali: {len(records)}")

def valid(n):
    s = sum(n)
    if s < 246 or s > 306: return False
    dec = Counter(x // 10 for x in n)
    if max(dec.values()) > 2: return False
    if sum(1 for x in n if x > 80) > 1: return False
    return True

def quartile_spread():
    qr = [(1, 22), (23, 45), (46, 67), (68, 90)]
    for _ in range(2000):
        alloc = [1, 1, 1, 1]; extra = 2
        while extra > 0:
            alloc[random.randrange(4)] += 1; extra -= 1
        nums = []
        for qi in range(4):
            lo, hi = qr[qi]
            nums.extend(random.sample(range(lo, hi + 1), alloc[qi]))
        nums = sorted(nums)
        if valid(nums): return nums
    return sorted(random.sample(range(1, 91), 6))

def last_digit_spread():
    for _ in range(2000):
        nums = []; used = set(); ok = True
        while len(nums) < 6:
            n = random.randint(1, 90)
            if n in nums: continue
            if n % 10 in used: ok = False; break
            used.add(n % 10); nums.append(n)
        if ok and valid(sorted(nums)): return sorted(nums)
    return sorted(random.sample(range(1, 91), 6))

def fib_wheel():
    fib = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    pool = fib + [n for n in range(1, 91) if n not in fib]
    for _ in range(2000):
        nums = sorted(random.sample(pool, 6))
        if valid(nums): return nums
    return sorted(random.sample(range(1, 91), 6))

def random_pure():
    return sorted(random.sample(range(1, 91), 6))

STRAT = {
    "QuartileSpread": quartile_spread,
    "LastDigitSpread": last_digit_spread,
    "FibonacciWheel": fib_wheel,
    "RandomPuro": random_pure,
}
PREMI = {2: 5, 3: 10, 4: 100, 5: 1000, 6: 1000000}

def roi_on_window(window, fn, n_sched=1):
    spent = 0; won = 0
    for rec in window:
        for _ in range(n_sched):
            nums = fn()
            spent += 1
            m = len(set(nums) & set(rec["nums"]))
            if m >= 2: won += PREMI.get(m, 0)
    return (won / spent * 100) if spent else 0, won - spent

# 1) ROI fisso su TUTTO lo storico per ogni strategia
print("\n=== ROI su TUTTO lo storico (4195 estrazioni, 1 sched/estraz) ===")
hist = {}
for name, fn in STRAT.items():
    roi, net = roi_on_window(records, fn)
    hist[name] = roi
    print(f"  {name:16} ROI {roi:6.2f}%  net EUR{net}")

# 2) Rolling: per ogni N, quante volte cambia il vincitore? stabilita'
print("\n=== ROLLING: stabilita' del vincitore per finestra N ===")
Ns = [10, 25, 50, 100, 200, 500, 1000]
for N in Ns:
    winners = []
    for start in range(0, len(records) - N, max(1, N // 2)):
        win = records[start:start + N]
        ros = {n: roi_on_window(win, f)[0] for n, f in STRAT.items()}
        winners.append(max(ros, key=ros.get))
    cnt = Counter(winners)
    top = cnt.most_common(1)[0]
    print(f"  N={N:4}: vincitore piu frequente = {top[0]} ({top[1]}/{len(winners)} = {top[1]*100//len(winners)}%)  | tutti: {dict(cnt)}")

# 3) Confronto: storico lungo vs finestra adattiva (split test)
print("\n=== TRAIN/TEST: storico (train) vs adattivo (rolling test) ===")
TRAIN = records[:3000]; TEST = records[3000:]
# Auto fisso = migliore su TRAIN
ros_train = {n: roi_on_window(TRAIN, f)[0] for n, f in STRAT.items()}
best_fixed = max(ros_train, key=ros_train.get)
roi_fixed_test = roi_on_window(TEST, STRAT[best_fixed])[0]
# Auto adattivo = rolling 50 su TEST
winners_test = []
for s in range(0, len(TEST) - 50, 25):
    w = TEST[s:s + 50]
    ros = {n: roi_on_window(w, f)[0] for n, f in STRAT.items()}
    winners_test.append(max(ros, key=ros.get))
roi_adapt_test = roi_on_window(TEST, STRAT[Counter(winners_test).most_common(1)[0][0]])[0]
print(f"  Train best fisso: {best_fixed} (ROI train {ros_train[best_fixed]:.1f}%)")
print(f"  ROI su TEST - fisso:     {roi_fixed_test:.2f}%")
print(f"  ROI su TEST - adattivo:  {roi_adapt_test:.2f}%")
print(f"  => {'ADATTIVO' if roi_adapt_test > roi_fixed_test else 'FISSO'} migliore sul test")

# 4) Significativita: QuartileSpread vs RandomPuro su 100 split
print("\n=== SIGNIFICATIVITA': QuartileSpread vs RandomPuro (100 split da 200) ===")
qs_wins = 0; tot = 100
for _ in range(tot):
    samp = random.sample(records, 200)
    r_qs = roi_on_window(samp, quartile_spread)[0]
    r_rp = roi_on_window(samp, random_pure)[0]
    if r_qs > r_rp: qs_wins += 1
print(f"  QuartileSpread batte RandomPuro in {qs_wins}/{tot} split ({qs_wins}%)")
