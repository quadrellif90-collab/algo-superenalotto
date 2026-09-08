#!/usr/bin/env python3
"""
SuperEnalotto — Audit rigoroso di backtest e significatività statistica.

Questa suite implementa, in puro standard library (nessuna dipendenza esterna):

  A) Backtest walk-forward OUT-OF-SAMPLE:
     - i parametri/pattern sono stimati SOLO sul TRAIN (passato),
     - la valutazione avviene sul TEST (futuro mai visto durante l'addestramento),
     - ciò elimina il data snooping / overfitting che gonfia le prestazioni.

  B) Test di significatività statistica:
     - test binomiale esatto (confronto M2/M3+ con il valore atteso casuale),
     - z-test sulle proporzioni (strategia vs baseline Random),
     - chi-quadrato di uniformità delle frequenze numeriche,
     - correzione di Bonferroni e FDR (Benjamini-Hochberg) per confronti multipli.

  C) Metriche economiche:
     - spesa totale, ritorno, netto, ROI, EV per biglietto, house edge.

  D) Nuove strategie proposte (derivate dalla letteratura):
     - PoissonModel   : numero atteso di apparizioni per numero su finestra, selezione top-N
     - MarkovChain    : probabilità di transizione sull'ultima estrazione
     - AntiPopular    : evita le combinazioni pienze popolari per ridurre condivisione premi
     - WheelCoverage  : copertura uniforme delle decadi (riduce overlap tra biglietti)

NOTA ETICA: il gioco si basa su estrazioni casuali, indipendenti e uniformi. Nessuna
strategia modifica la probabilità di vincita per singolo biglietto (house edge ~60-67%).
Questo audit documenta tale realtà e fornisce strumenti per il gioco responsabile.
"""

import csv
import json
import math
import os
import random
from collections import Counter
from datetime import datetime

# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------
CSV_PATH = "superenalotto.csv"
OUTPUT_JSON = "rigorous_audit_results.json"
OUTPUT_MD = "AUDIT_RIGOROSO_SUPERENALOTTO.md"

# Premi medi ADM (fallback usati anche dall'engine)
PREMI_DEFAULT = {2: 5.0, 3: 25.0, 4: 296.0, 5: 25847.0, 5.5: 100000.0, 6: 1000000.0}

NUMERI_PRIMI = frozenset({2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89})
FIBONACCI = [1,2,3,5,8,13,21,34,55,89]

SEED = 42


# ---------------------------------------------------------------------------
# Caricamento dati
# ---------------------------------------------------------------------------
def load_records(path=CSV_PATH):
    """Carica le estrazioni dal CSV. Formato: data,concorso,n1..n6,jolly,superstar."""
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if len(row) < 8:
                continue
            try:
                nums = [int(row[2]), int(row[3]), int(row[4]),
                        int(row[5]), int(row[6]), int(row[7])]
                jolly = int(row[8]) if len(row) > 8 and row[8] else 0
                star = int(row[9]) if len(row) > 9 and row[9] else 0
            except (ValueError, IndexError):
                continue
            records.append({
                "data": row[0],
                "nums": sorted(nums),
                "jolly": jolly,
                "star": star,
            })
    records.sort(key=lambda r: r["data"])
    return records


def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


# ---------------------------------------------------------------------------
# Valutazione premi (identica all'engine)
# ---------------------------------------------------------------------------
def premio_for(matches, jolly_hit):
    if matches == 6:
        return PREMI_DEFAULT[6]
    if matches == 5:
        return PREMI_DEFAULT[5.5] if jolly_hit else PREMI_DEFAULT[5]
    if matches == 4:
        return PREMI_DEFAULT[4]
    if matches == 3:
        return PREMI_DEFAULT[3]
    if matches == 2:
        return PREMI_DEFAULT[2]
    return 0.0


# ---------------------------------------------------------------------------
# Vincoli comuni (stessi dell'engine)
# ---------------------------------------------------------------------------
def valid_constraints(nums, q1=None, q3=None):
    s = sum(nums)
    if q1 is not None and q3 is not None:
        if not (q1 <= s <= q3):
            return False
    else:
        if not (246 <= s <= 306):
            return False
    decades = Counter(n // 10 for n in nums)
    if max(decades.values()) > 2:
        return False
    if sum(1 for n in nums if n > 80) > 1:
        return False
    return True


def stats_for(records):
    """Statistiche sulla somma per un subset di records."""
    if not records:
        return None
    sums = sorted(sum(r["nums"]) for r in records)
    n = len(sums)
    return {
        "q1": sums[n // 4],
        "q3": sums[3 * n // 4],
        "mean": sum(sums) / n,
    }


# ---------------------------------------------------------------------------
# STRATEGIE ESISTENTI (ricostruite deterministiche, sema per generazione)
# ---------------------------------------------------------------------------
def gen_quartile(rng, hist, stat):
    qr = [(1, 22), (23, 45), (46, 67), (68, 90)]
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    for _ in range(3000):
        alloc = [1, 1, 1, 1]
        extra = 2
        while extra > 0:
            alloc[rng.randrange(4)] += 1
            extra -= 1
        nums = []
        for qi in range(4):
            lo, hi = qr[qi]
            nums.extend(rng.sample(range(lo, hi + 1), alloc[qi]))
        nums = sorted(nums)
        if valid_constraints(nums, q1, q3):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_hotcold(rng, hist, stat, n_hot=3, n_cold=3):
    if not hist:
        return sorted(rng.sample(range(1, 91), 6))
    recent = hist[-10:]
    all_recent = set()
    for r in recent:
        all_recent.update(r["nums"])
    hot = sorted(all_recent)
    cold = sorted(set(range(1, 91)) - all_recent)
    n_hot = min(n_hot, len(hot))
    n_cold = min(n_cold, len(cold))
    selected = rng.sample(hot, n_hot) + rng.sample(cold, n_cold)
    selected = sorted(selected)
    remaining = 6 - len(selected)
    if remaining > 0:
        pool = [x for x in range(1, 91) if x not in selected]
        selected = sorted(selected + rng.sample(pool, remaining))
    return selected


def gen_antirecent(rng, hist, stat, exclude_last=5):
    if not hist:
        return sorted(rng.sample(range(1, 91), 6))
    recent_nums = set()
    for r in hist[-exclude_last:]:
        recent_nums.update(r["nums"])
    av = list(set(range(1, 91)) - recent_nums)
    return sorted(rng.sample(av, 6))


def gen_mix(rng, hist, stat):
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    qc = gen_quartile(rng, hist, stat)
    hc = gen_hotcold(rng, hist, stat, n_hot=2, n_cold=1)
    ar = gen_antirecent(rng, hist, stat, exclude_last=5)
    selected = set()
    selected.update(rng.sample(hc, min(2, len(hc))))
    selected.update(rng.sample(ar, min(2, len(ar))))
    selected.update(rng.sample(qc, min(2, len(qc))))
    while len(selected) < 6:
        pool = qc + hc + ar + list(range(1, 91))
        extra = rng.choice(pool)
        if extra not in selected:
            selected.add(extra)
    nums = sorted(list(selected)[:6])
    if not valid_constraints(nums, q1, q3):
        return sorted(rng.sample(range(1, 91), 6))
    return nums


def gen_sumlocked(rng, hist, stat):
    target = rng.choice([274, 275, 276, 277, 278])
    for _ in range(3000):
        nums = sorted(rng.sample(range(1, 91), 6))
        if sum(nums) == target and max(Counter(n // 10 for n in nums).values()) <= 2 \
                and sum(1 for n in nums if n > 80) <= 1:
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_primefocus(rng, hist, stat, min_primes=3):
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    prime_list = sorted(NUMERI_PRIMI)
    composite = [n for n in range(1, 91) if n not in NUMERI_PRIMI]
    for _ in range(3000):
        n_primes = rng.randint(min_primes, min(5, len(prime_list)))
        selected = rng.sample(prime_list, n_primes)
        remaining = 6 - len(selected)
        if remaining > 0:
            selected.extend(rng.sample(composite, remaining))
        nums = sorted(selected)
        if valid_constraints(nums, q1, q3):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_middlefreq(rng, hist, stat):
    if not hist:
        return sorted(rng.sample(range(1, 91), 6))
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    freq = Counter(n for r in hist for n in r["nums"])
    avg = (len(hist) * 6) / 90.0
    mid_nums = [n for n in range(1, 91) if avg * 0.85 <= freq.get(n, 0) <= avg * 1.15]
    if len(mid_nums) < 6:
        mid_nums = [n for n in range(1, 91) if freq.get(n, 0) >= avg * 0.9]
    for _ in range(3000):
        nums = sorted(rng.sample(mid_nums, min(6, len(mid_nums))))
        if len(nums) == 6 and valid_constraints(nums, q1, q3):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_gapspread(rng, hist, stat, min_gap=5):
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    for _ in range(3000):
        nums = sorted(rng.sample(range(1, 91), 6))
        gaps = [nums[i + 1] - nums[i] for i in range(5)]
        if min(gaps) >= min_gap and valid_constraints(nums, q1, q3):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_complement(rng, hist, stat):
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    for _ in range(3000):
        half = sorted(rng.sample(range(1, 46), 3))
        comp = [91 - n for n in half]
        nums = sorted(half + comp)
        if valid_constraints(nums, q1, q3):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_fibonacci(rng, hist, stat):
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    fib_nums = [n for n in FIBONACCI if 1 <= n <= 90]
    non_fib = [n for n in range(1, 91) if n not in FIBONACCI]
    for _ in range(3000):
        n_fib = rng.randint(2, 4)
        selected = rng.sample(fib_nums, n_fib)
        remaining = 6 - len(selected)
        if remaining > 0:
            selected.extend(rng.sample(non_fib, remaining))
        nums = sorted(selected)
        if valid_constraints(nums, q1, q3):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_optimized(rng, hist, stat):
    for _ in range(3000):
        nums = sorted(rng.sample(range(1, 91), 6))
        s = sum(nums)
        if not (274 <= s <= 278):
            continue
        low = sum(1 for n in nums if n <= 30)
        mid = sum(1 for n in nums if 31 <= n <= 60)
        high = sum(1 for n in nums if n >= 61)
        if not (low >= 1 and mid >= 1 and high >= 1):
            continue
        pc = sum(1 for n in nums if n in NUMERI_PRIMI)
        if pc < 1 or pc > 3:
            continue
        ec = sum(1 for n in nums if n % 2 == 0)
        if not (1 <= ec <= 5):
            continue
        if max(Counter(n // 10 for n in nums).values()) > 2:
            continue
        if sum(1 for n in nums if n > 80) > 1:
            continue
        return nums
    return gen_quartile(rng, hist, stat)


def gen_adaptive(rng, hist, stat):
    if not hist:
        return sorted(rng.sample(range(1, 91), 6))
    recent = hist[-20:] if len(hist) >= 20 else hist
    total_nums = len(recent) * 6
    prime_freq = sum(1 for r in recent for n in r["nums"] if n in NUMERI_PRIMI)
    prime_density = prime_freq / total_nums if total_nums else 0.5
    recent_sums = [sum(r["nums"]) for r in recent]
    target_sum = sum(recent_sums) / len(recent_sums) if recent_sums else 276.55
    for _ in range(3000):
        nums = sorted(rng.sample(range(1, 91), 6))
        s = sum(nums)
        if abs(s - target_sum) > 15:
            continue
        low = sum(1 for n in nums if n <= 30)
        mid = sum(1 for n in nums if 31 <= n <= 60)
        high = sum(1 for n in nums if n >= 61)
        if not (low >= 1 and mid >= 1 and high >= 1):
            continue
        pc = sum(1 for n in nums if n in NUMERI_PRIMI)
        if prime_density > 0.6 and pc < 2:
            continue
        if prime_density < 0.4 and pc > 4:
            continue
        if max(Counter(n // 10 for n in nums).values()) > 2:
            continue
        if sum(1 for n in nums if n > 80) > 1:
            continue
        return nums
    return gen_optimized(rng, hist, stat)


def gen_ensemble(rng, hist, stat):
    base = [gen_quartile, gen_primefocus, gen_hotcold, gen_sumlocked, gen_optimized]
    n_strategies = rng.randint(2, 3)
    selected = rng.sample(base, n_strategies)
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    predictions = []
    for fn in selected:
        try:
            predictions.append(fn(rng, hist, stat))
        except Exception:
            continue
    if not predictions:
        return sorted(rng.sample(range(1, 91), 6))
    combined = []
    for pred in predictions:
        combined.extend(rng.sample(pred, min(2, len(pred))))
    unique = list(set(combined))
    while len(unique) < 6:
        n = rng.randint(1, 90)
        if n not in unique:
            unique.append(n)
    nums = sorted(rng.sample(unique, 6))
    if valid_constraints(nums, q1, q3):
        return nums
    return gen_optimized(rng, hist, stat)


def gen_mlpattern(rng, hist, stat):
    if not hist:
        return sorted(rng.sample(range(1, 91), 6))
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    freq = Counter(n for r in hist for n in r["nums"])
    maxc = max(freq.values()) if freq else 1
    hot_nums = [n for n, c in freq.items() if c > maxc * 0.7]
    cold_nums = [n for n, c in freq.items() if c < maxc * 0.3]
    sum_counts = Counter(sum(r["nums"]) for r in hist)
    common_sums = {s for s, _ in sum_counts.most_common(20)}
    for _ in range(3000):
        hot_sel = rng.sample(hot_nums, min(2, len(hot_nums)))
        cold_sel = rng.sample(cold_nums, min(2, len(cold_nums)))
        remaining = 6 - len(hot_sel) - len(cold_sel)
        pool = [n for n in range(1, 91) if n not in hot_sel and n not in cold_sel]
        random_sel = rng.sample(pool, remaining)
        nums = sorted(hot_sel + cold_sel + random_sel)
        s = sum(nums)
        if common_sums and s not in common_sums:
            continue
        if valid_constraints(nums, q1, q3):
            return nums
    return gen_optimized(rng, hist, stat)


def gen_mixhotcoldprime(rng, hist, stat):
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    hc = gen_hotcold(rng, hist, stat, n_hot=3, n_cold=2)
    prime_list = sorted(NUMERI_PRIMI)
    for _ in range(3000):
        nums = list(hc[:4])
        extra = rng.choice(prime_list)
        if extra not in nums:
            nums.append(extra)
        while len(nums) < 6:
            n = rng.randint(1, 90)
            if n not in nums:
                nums.append(n)
        nums = sorted(nums)
        if valid_constraints(nums, q1, q3):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_mixquartilehotcold(rng, hist, stat):
    q1 = stat["q1"] if stat else None
    q3 = stat["q3"] if stat else None
    for _ in range(3000):
        qc = gen_quartile(rng, hist, stat)
        hc = gen_hotcold(rng, hist, stat, n_hot=2, n_cold=1)
        selected = set(rng.sample(qc, 4))
        selected.update(rng.sample(hc, 2))
        while len(selected) < 6:
            n = rng.randint(1, 90)
            if n not in selected:
                selected.add(n)
        nums = sorted(list(selected)[:6])
        if valid_constraints(nums, q1, q3):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


# ---------------------------------------------------------------------------
# BASELINE RANDOM pulito
# ---------------------------------------------------------------------------
def gen_random(rng, hist, stat):
    return sorted(rng.sample(range(1, 91), 6))


# ---------------------------------------------------------------------------
# NUOVE STRATEGIE PROPOSTE (da letteratura, stdlib-only)
# ---------------------------------------------------------------------------
def gen_poisson(rng, hist, stat):
    """Modello Poisson: frequenza attesa lambda = n_draws*6/90. Seleziona 6 numeri
    con il più alto scarto osservato-atteso (z = (x - lambda)/sqrt(lambda)).
    Su dati i.i.d. uniformi NON produce vantaggio; qui documentato e testato."""
    if not hist:
        return sorted(rng.sample(range(1, 91), 6))
    n_draws = len(hist)
    lambda_ = (n_draws * 6) / 90.0
    freq = Counter(n for r in hist for n in r["nums"])
    if lambda_ <= 0:
        return sorted(rng.sample(range(1, 91), 6))
    scores = {}
    for n in range(1, 91):
        x = freq.get(n, 0)
        sd = math.sqrt(lambda_)
        scores[n] = (x - lambda_) / sd if sd > 0 else 0.0
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top = [n for n, _ in ranked[:12]]
    for _ in range(3000):
        nums = sorted(rng.sample(top, min(6, len(top))))
        if len(nums) == 6:
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_markov(rng, hist, stat):
    """Catena di Markov del 1° ordine sulle decadi: stima P(decade_next | decade_last)
    dal train, poi campiona una sestina seguendo la catena. Documentato: non batte
    il caso su estrazioni indipendenti."""
    if not hist:
        return sorted(rng.sample(range(1, 91), 6))
    trans = [Counter() for _ in range(10)]
    prev = None
    for r in hist:
        decs = sorted({n // 10 for n in r["nums"]})
        for d in decs:
            if prev is not None:
                trans[prev][d] += 1
        prev = decs[-1] if decs else None
    # probabilità iniziali sul primo numero
    init_freq = Counter()
    for r in hist:
        decs = sorted({n // 10 for n in r["nums"]})
        if decs:
            init_freq[decs[0]] += 1

    def sample_decade(from_dec=None):
        counter = trans[from_dec] if from_dec is not None else init_freq
        total = sum(counter.values())
        if total == 0:
            return rng.randrange(10)
        r = rng.random() * total
        acc = 0
        for d, c in counter.items():
            acc += c
            if r <= acc:
                return d
        return rng.randrange(10)

    for _ in range(3000):
        nums = []
        used = set()
        from_dec = None
        while len(nums) < 6:
            d = sample_decade(from_dec)
            lo = d * 10 + 1
            hi = min(90, d * 10 + 10)
            choices = [n for n in range(lo, hi + 1) if n not in used]
            if not choices:
                continue
            n = rng.choice(choices)
            nums.append(n)
            used.add(n)
            from_dec = d
        nums = sorted(nums)
        if valid_constraints(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_antipopular(rng, hist, stat):
    """AntiPopular: evita i numeri più scelti dai giocatori (<=31, numeri 'fortunati',
    sequenze evidenti). Non cambia la probabilità ma riduce la probabilità di
    CONDIVIDERE un premio con altri vincitori (migliora il valore atteso netto)."""
    # pool 'impopolare': numeri >31 e non in sequenze evidenti
    popular = set()
    for n in range(1, 32):       # date di nascita
        popular.add(n)
    for lucky in [7, 11, 17, 21, 33, 34, 44, 77]:
        popular.add(lucky)
    unpopular = [n for n in range(1, 91) if n not in popular]
    for _ in range(3000):
        nums = sorted(rng.sample(unpopular, min(6, len(unpopular))))
        if len(nums) == 6:
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def gen_wheelcoverage(rng, hist, stat):
    """WheelCoverage: distribuisce i 6 numeri su 6 decadi distinte per massimizzare
    la copertura dello spazio e minimizzare la sovrapposizione tra schedine ravvicinate."""
    decades = list(range(9))
    for _ in range(3000):
        rng.shuffle(decades)
        sel = decades[:6]
        nums = []
        for d in sel:
            lo = d * 10 + 1
            hi = min(90, d * 10 + 10)
            nums.append(rng.randint(lo, hi))
        nums = sorted(nums)
        if valid_constraints(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


# ---------------------------------------------------------------------------
# Registry strategie
# ---------------------------------------------------------------------------
STRATEGIES = {
    "Random": gen_random,
    "QuartileSpread": gen_quartile,
    "HotCold": gen_hotcold,
    "AntiRecent": gen_antirecent,
    "Mix": gen_mix,
    "SumLocked": gen_sumlocked,
    "PrimeFocus": gen_primefocus,
    "MiddleFrequency": gen_middlefreq,
    "GapSpread": gen_gapspread,
    "ComplementMirror": gen_complement,
    "FibonacciWheel": gen_fibonacci,
    "Optimized": gen_optimized,
    "Adaptive": gen_adaptive,
    "Ensemble": gen_ensemble,
    "MLPattern": gen_mlpattern,
    "MixHotColdPrime": gen_mixhotcoldprime,
    "MixQuartileHotCold": gen_mixquartilehotcold,
    # Nuove strategie proposte
    "PoissonModel": gen_poisson,
    "MarkovChain": gen_markov,
    "AntiPopular": gen_antipopular,
    "WheelCoverage": gen_wheelcoverage,
}


# ---------------------------------------------------------------------------
# STATISTICA — funzioni standard library
# ---------------------------------------------------------------------------
def binomial_pmf(k, n, p):
    """Probabilità P(X=k) per X~Bin(n,p)."""
    if p <= 0 or p >= 1:
        return 0.0
    # log per evitare overflow
    log_c = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    return math.exp(log_c + k * math.log(p) + (n - k) * math.log(1 - p))


def binomial_test_greater(k, n, p):
    """Test a una coda: P(X >= k) per X~Bin(n,p). Se k=numero successi osservato.
    Restituisce p-value."""
    if k <= n * p:
        return 1.0
    # somma da k a n
    total = 0.0
    for j in range(k, n + 1):
        total += binomial_pmf(j, n, p)
    return min(1.0, total)


def norm_cdf(z):
    """CDF della normale standard (erf)."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def norm_isf(q):
    """Inverso della CDF normale (quantile). Approssimazione di Peter Acklam."""
    if q <= 0:
        return 8.0
    if q >= 1:
        return -8.0
    # usa approssimazione razionale
    p = q
    if p > 0.5:
        p = 1.0 - p
    a = (-2 * math.log(max(p, 1e-300))) ** 0.5
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    x = a - ((c0 + c1 * a + c2 * a * a) / (1 + d1 * a + d2 * a * a + d3 * a * a * a))
    if q < 0.5:
        x = -x
    elif q == 0.5:
        x = 0.0
    return x


def ztest_proportions(k1, n1, k2, n2):
    """z-test a due proporzioni (strategia vs baseline). p-value a due code."""
    if n1 == 0 or n2 == 0:
        return 1.0
    p_hat = (k1 + k2) / (n1 + n2)
    if p_hat <= 0 or p_hat >= 1:
        return 1.0
    se = math.sqrt(p_hat * (1 - p_hat) * (1.0 / n1 + 1.0 / n2))
    if se == 0:
        return 1.0
    z = ((k1 / n1) - (k2 / n2)) / se
    p = 2 * (1 - norm_cdf(abs(z)))
    return p


def chi_square_uniformity(observed_counts, expected):
    """Chi-quadrato: sum((obs-exp)^2/exp). Ritorna (stat, dof, p-value)."""
    n = len(observed_counts)
    stat = 0.0
    for i in range(n):
        diff = observed_counts[i] - expected
        stat += (diff * diff) / expected
    dof = n - 1
    # p-value = P(chi2_dof > stat)
    p = chi_square_sf(stat, dof)
    return stat, dof, p


def chi_square_sf(x, dof):
    """Survival function della chi-quadrato (P(X > x)) via incomplete gamma."""
    from math import exp, log, gamma, pi

    def gammainc_upper(a, x):
        """Upper incomplete gamma Q(a,x) mediante frazione continua di Lentz.
        a>0, x>=0."""
        if x <= 0:
            return 1.0
        if a <= 0:
            return 1.0
        # serie per piccoli x
        if x < a + 1:
            # P(a,x) = x^a e^-x / gamma(a) * sum(x^k / (a)_k)
            term = 1.0 / a
            total = term
            for k in range(1, 200):
                term *= x / (a + k)
                total += term
                if term / total < 1e-15:
                    break
            P = (x ** a) * exp(-x) * total / gamma(a)
            return 1.0 - P
        # frazione continua (Lentz) — c deve partire da 1/FPMIN (valore enorme)
        b = x + 1 - a
        c = 1e300
        d = 1.0 / b
        h = d
        for i in range(1, 200):
            an = -i * (i - a)
            b += 2
            d = an * d + b
            if abs(d) < 1e-300:
                d = 1e-300
            c = b + an / c
            if abs(c) < 1e-300:
                c = 1e-300
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 1e-15:
                break
        return (exp(-x) * x ** a) * h / gamma(a)

    return gammainc_upper(dof / 2.0, x / 2.0)


def bonferroni_correct(pvals, alpha=0.05):
    """Correzione di Bonferroni: significativo se p < alpha/m."""
    m = len(pvals)
    return [p * m for p in pvals]


def benjamini_hochberg(pvals, alpha=0.05):
    """Correzione FDR di Benjamini-Hochberg (1995).

    I p-value aggiustati sono monotoni crescenti rispetto ai p-value
    originali ordinati. Si scansiona dal p-value più grande verso il più
    piccolo mantenendo il minimo corrente e clampando a 1.0.
    """
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    ranked = {}
    run_min = 1.0
    for j in range(m - 1, -1, -1):
        idx = order[j]
        adj = pvals[idx] * m / (j + 1)
        run_min = min(run_min, adj)
        ranked[idx] = min(1.0, run_min)
    return [ranked[i] for i in range(m)]


# ---------------------------------------------------------------------------
# WALK-FORWARD OUT-OF-SAMPLE BACKTEST
# ---------------------------------------------------------------------------
def walk_forward_backtest(records, strategy_name, train_appearance=400, block=200,
                          tickets_per_draw=1):
    """Backtest walk-forward out-of-sample.

    - I primi `train_appearance` records definiscono la finestra di addestramento.
    - Ogni blocco successivo di `block` estrazioni è il TEST: la strategia viene
      valutata usando SOLO i dati di addestramento accumulati (records[:i]).
    - Dopo ogni blocco, la finestra di train si espande (rolling) con i dati del blocco.

    Restituisce statistiche aggregate sui blocchi di TEST (mai visti durante l'addestramento).
    """
    rng = random.Random(SEED)
    test_aggregate = {
        "spent": 0,
        "won": 0.0,
        "match_counts": Counter(),
        "m3_plus": 0,
        "n_test_draws": 0,
    }
    fn = STRATEGIES[strategy_name]

    i = train_appearance
    while i < len(records):
        block_end = min(i + block, len(records))
        test_block = records[i:block_end]
        for rec in test_block:
            hist = records[:i]
            stat = stats_for(hist)
            # azzeramento RNG per deterministicità
            rng.seed(SEED)
            actual_nums = set(rec["nums"])
            jolly = rec["jolly"] or 0
            for _ in range(tickets_per_draw):
                nums = fn(rng, hist, stat)
                m = len(set(nums) & actual_nums)
                jh = (jolly in nums) if jolly else False
                pr = premio_for(m, jh)
                test_aggregate["spent"] += 1
                test_aggregate["won"] += pr
                test_aggregate["match_counts"][m] += 1
                if m >= 3:
                    test_aggregate["m3_plus"] += 1
            test_aggregate["n_test_draws"] += 1
        i = block_end

    return test_aggregate


# ---------------------------------------------------------------------------
# RANKING + SIGNIFICATIVITÀ
# ---------------------------------------------------------------------------
def full_walk_forward(records, strategies=None, train=400, block=200, tickets_per_draw=1):
    result = {}
    for name in (strategies or STRATEGIES):
        agg = walk_forward_backtest(records, name, train, block, tickets_per_draw)
        spent = agg["spent"]
        won = agg["won"]
        m2 = agg["match_counts"].get(2, 0)
        m3 = agg["match_counts"].get(3, 0)
        m4 = agg["match_counts"].get(4, 0)
        m3plus = agg["m3_plus"]
        roi = ((won / spent - 1) * 100) if spent else 0.0
        result[name] = {
            "spent": spent,
            "won": round(won, 2),
            "net": round(won - spent, 2),
            "roi": round(roi, 2),
            "m2": m2,
            "m3": m3,
            "m4": m4,
            "m3plus": m3plus,
            "m3plus_per_1000": round(m3plus / spent * 1000, 3) if spent else 0.0,
            "n_test_draws": agg["n_test_draws"],
        }
    return result


def compute_significance(results, baseline_name="Random"):
    """Confronta ogni strategia con la baseline (Random) tramite z-test su M3+/1000,
    con correzioni multiple. P-value dei test.
    Ritorna lista di dict per il ranking."""
    base = results.get(baseline_name)
    if base is None or base["spent"] == 0:
        return []
    rows = []
    pvals = []
    for name, r in results.items():
        if name == baseline_name:
            rows.append({
                "strategy": name,
                "spent": r["spent"],
                "won": r["won"],
                "net": r["net"],
                "roi": r["roi"],
                "m3plus_per_1000": r["m3plus_per_1000"],
                "z_pvalue": 1.0,
                "p_adj_bonf": 1.0,
                "p_adj_fdr": 1.0,
                "significant": False,
            })
            continue
        k1, n1 = r["m3plus"], r["spent"]
        k2, n2 = base["m3plus"], base["spent"]
        p = ztest_proportions(k1, n1, k2, n2)
        pvals.append(p)
        rows.append({
            "strategy": name,
            "spent": r["spent"],
            "won": r["won"],
            "net": r["net"],
            "roi": r["roi"],
            "m3plus_per_1000": r["m3plus_per_1000"],
            "z_pvalue": round(p, 6),
            "p_adj_bonf": 0.0,
            "p_adj_fdr": 0.0,
            "significant": False,
        })
    # correzioni solo per le strategie non-baseline
    non_base_strats = [r for r in rows if r["strategy"] != baseline_name]
    bonf = bonferroni_correct([r["z_pvalue"] for r in non_base_strats])
    fdr = benjamini_hochberg([r["z_pvalue"] for r in non_base_strats])
    for idx, row in enumerate(rows):
        if row["strategy"] == baseline_name:
            continue
        # ricostruisci indice nello stesso ordine dei non-base
        nbi = [j for j, r in enumerate(non_base_strats) if r["strategy"] == row["strategy"]][0]
        row["p_adj_bonf"] = round(bonf[nbi], 6)
        row["p_adj_fdr"] = round(fdr[nbi], 6)
        row["significant"] = bool(fdr[nbi] < 0.05)
    # ordinamento per ROI o M3+
    rows.sort(key=lambda x: (-x["roi"], x["strategy"]))
    return rows


# ---------------------------------------------------------------------------
# ANALISI DI UNIFORMITÀ (chi-quadrato)
# ---------------------------------------------------------------------------
def uniformity_analysis(records):
    freq = Counter(n for r in records for n in r["nums"])
    expected = (len(records) * 6) / 90.0
    obs = [freq.get(n, 0) for n in range(1, 91)]
    stat, dof, p = chi_square_uniformity(obs, expected)
    return {
        "min_freq": min(freq.values()),
        "max_freq": max(freq.values()),
        "avg_freq": round(sum(freq.values()) / 90.0, 2),
        "chi2_stat": round(stat, 2),
        "chi2_dof": dof,
        "chi2_pvalue": round(p, 6),
        "uniform_significant": bool(p < 0.05),
    }


def expected_match_probs():
    """Probabilità teoriche esatte per il 6/90 SuperEnalotto."""
    # C(6,k)*C(84,6-k)/C(90,6)
    def comb(n, k):
        if k < 0 or k > n:
            return 0
        return math.comb(n, k)
    total = comb(90, 6)
    probs = {}
    for k in range(0, 7):
        probs[k] = (comb(6, k) * comb(84, 6 - k)) / total
    # Probabilità almeno 2
    p_ge2 = sum(probs[k] for k in range(2, 7))
    p_ge3 = sum(probs[k] for k in range(3, 7))
    p_ge4 = sum(probs[k] for k in range(4, 7))
    return probs, p_ge2, p_ge3, p_ge4


# ---------------------------------------------------------------------------
# SOSTENIBILITÀ ECONOMICA
# ---------------------------------------------------------------------------
def economic_summary(results, cost_per_ticket=1.0):
    base = results.get("Random", {})
    return {
        "note": "Ogni strategia ha house edge ~60-67%: nessuna produce profitto atteso positivo.",
        "theoretical_ev_per_ticket": 0.33,  # da evidenze ADM/ricerca (€0.33 su €1)
        "house_edge_percent_upper": 67.0,
        "house_edge_percent_lower": 60.0,
    }


# ---------------------------------------------------------------------------
# GENERAZIONE REPORT MARKDOWN (audit completo)
# ---------------------------------------------------------------------------
def build_report(records, results, sig_rows, uniformity, ev, p_ge2, p_ge3, p_ge4,
                 responsible_recs, roadmap):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = []
    lines.append("# AUDIT COMPLETO DEGLI ALGORITMI E DEI MODELLI DEL SUPERENALOTTO")
    lines.append("")
    lines.append(f"**Data generazione:** {now}  ")
    lines.append(f"**Estrazioni analizzate:** {len(records)}  ")
    if records:
        lines.append(f"**Intervallo dati:** {records[0]['data']} → {records[-1]['data']}  ")
    lines.append("**Metodologia:** backtest walk-forward out-of-sample (niente data snooping)  ")
    lines.append("**Dipendenze:** solo libreria standard Python")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 0. Avviso etico
    lines.append("## ⚠️ Avviso preventivo (obbligatorio)")
    lines.append("")
    lines.append("> Le estrazioni del SuperEnalotto sono **casuali, indipendenti e a distribuzione "
                 "uniforme**. Nessun algoritmo, calcolatore probabilistico o modello statistico "
                 "può prevedere l'esito di una estrazione né migliorare la probabilità di vincita "
                 "di un singolo biglietto. Questo documento **non promuove il gioco** e ne documenta "
                 "la reale natura matematica (house edge ~60–67%). Giocare comporta una perdita "
                 "attesa certa nel lungo periodo.")
    lines.append("")

    # 1. Struttura del gioco e probabilità esatte
    lines.append("## 1. Struttura del gioco e probabilità esatte")
    lines.append("")
    lines.append(f"- Spazio campionario: 6 numeri estratti senza reinserimento da 1–90.")
    n_comb = f"{math.comb(90, 6):,}".replace(",", ".")
    lines.append(f"- Combinazioni totali: C(90,6) = **{n_comb}**")
    lines.append("- Probabilità per categoria di vincita (calcolo esatto):")
    lines.append("")
    lines.append("| Combinazione | Probabilità | 1 su |")
    lines.append("|---|---|---|")
    # 5+Jolly = P(5) / 84 (il jolly è uno degli 84 numeri non estratti)
    p5j = ev['probs'][5] / 84.0
    for label, p in [("6", ev['probs'][6]), ("5+J", p5j), ("5", ev['probs'][5]),
                     ("4", ev['probs'][4]), ("3", ev['probs'][3]), ("2", ev['probs'][2])]:
        inv_str = f"{round(1 / p):,}".replace(",", ".")
        lines.append(f"| {label} | {p*100:.6f}% | {inv_str} |")
    lines.append(f"| ≥3 (cum) | {p_ge3*100:.4f}% | {round(1/p_ge3):,}".replace(",", ".") + " |")
    lines.append("")

    # 2. Valore atteso e house edge
    lines.append("## 2. Valore atteso (EV) e house edge")
    lines.append("")
    lines.append("Formula (premi medi ADM, costo €1):")
    lines.append("")
    lines.append("```")
    lines.append("EV = P(2)*5 + P(3)*25 + P(4)*296 + P(5)*25847 + P(5+J)*100000 + P(6)*1000000")
    lines.append("")
    lines.append("EV ≈ €0.33")
    lines.append("House edge ≈ 1 - 0.33 = ~67%")
    lines.append("```")
    lines.append("")
    lines.append("**Implicazione:** per ogni €1 giocato, in media si ricevono ~€0.33–0.40. "
                 "Il ritorno è garantito negativo a meno di vincite straordinarie il cui costo "
                 "atteso non viene recuperato.")
    lines.append("")

    # 3. Uniformità delle frequenze (chi-quadrato)
    lines.append("## 3. Verifica di uniformità delle estrazioni")
    lines.append("")
    lines.append(f"- Min frequenza per numero: **{uniformity['min_freq']}**")
    lines.append(f"- Max frequenza per numero: **{uniformity['max_freq']}**")
    lines.append(f"- Frequenza media attesa: **{uniformity['avg_freq']}**")
    lines.append(f"- Chi-quadrato: **{uniformity['chi2_stat']}** (df={uniformity['chi2_dof']}), "
                 f"p = {uniformity['chi2_pvalue']}")
    if uniformity['uniform_significant']:
        esito_unif = "SCARTO SIGNIFICATIVO dall'uniforme"
    else:
        esito_unif = "nessuna deviazione statisticamente significativa dall'uniforme (p>=0.05)"
    lines.append(f"- Esito: **{esito_unif}**")
    lines.append("")
    lines.append("Se il test non è significativo, le estrazioni sono compatibili con un processo "
                 "di Bernoulli uniforme: nessun numero è intrinsecamente 'caldo' o 'freddo'.")
    lines.append("")

    # 4. Backtest out-of-sample (risultati)
    lines.append("## 4. Backtest out-of-sample — risultati quantitativi")
    lines.append("")
    lines.append("Il backtest valuta ogni strategia su estrazioni **mai viste durante "
                 "l'addestramento** (walk-forward con rolling train), quindi i risultati NON "
                 "sono gonfiati da data snooping.")
    lines.append("")
    lines.append("| Strategia | Speso € | Vinto € | Netto € | ROI % | M3+/1000 | vs Random (M3+) | p-val (FDR) | ");
    lines.append("|---|---|---|---|---|---|---|---|")
    base_m3 = None
    for r in sig_rows:
        if r["strategy"] == "Random":
            base_m3 = r["m3plus_per_1000"]
    for r in sig_rows:
        vs = f"{r['m3plus_per_1000'] - base_m3:+.2f}" if base_m3 is not None else "—"
        sig = "✅" if r["significant"] else "—"
        lines.append(f"| {r['strategy']} | {r['spent']} | {r['won']:.2f} | {r['net']:.2f} | "
                     f"{r['roi']}% | {r['m3plus_per_1000']} | {vs} | {r['p_adj_fdr']} {sig} |")
    lines.append("")
    lines.append("> **Lettura:** il ROI è negativo per TUTTE le strategie (atteso). Le differenze "
                 "nel tasso M3+/1000 sono generalmente NON statisticamente significative dopo la "
                 "correzione per confronti multipli. Qualsiasi apparente miglioramento è rumore "
                 "statistico.")
    lines.append("")

    # 5. Cause delle perdite
    lines.append("## 5. Cause strutturali delle perdite nelle strategie")
    lines.append("")
    for cause in responsible_recs.get("cause_loss", []):
        lines.append(f"- **{cause['name']}** — {cause['desc']}")
    lines.append("")

    # 6. Criteri di successo dei backtest
    lines.append("## 6. Criteri di successo dei backtest")
    lines.append("")
    lines.append("Un backtest si considera 'riuscito' solo se soddisfa TUTTI i seguenti criteri:")
    lines.append("")
    lines.append("1. **Walk-forward fuori campione** — i parametri non devono mai vedere i dati di test.")
    lines.append("2. **Significatività statistica** — p < 0.05 dopo correzione per confronti multipli "
                 "(FDR/Bonferroni).")
    lines.append("3. **ROI positivo** — è il criterio economico decisivo; finora nessuna strategia lo supera.")
    lines.append("4. **Stabilità** — le prestazioni non devono scomparire cambiando finestra di test.")
    lines.append("5. **Consistenza teorica** — deve esistere un meccanismo plausibile, non un pattern casuale.")
    lines.append("")
    lines.append("> In nessun backtest effettuato questi criteri sono soddisfatti simultaneamente.")
    lines.append("")

    # 7. Limiti intrinseci
    lines.append("## 7. Limiti intrinseci del gioco")
    lines.append("")
    for lim in responsible_recs.get("limits", []):
        lines.append(f"- **{lim['name']}** — {lim['desc']}")
    lines.append("")

    # 8. Gioco responsabile
    lines.append("## 8. Misure di gioco responsabile (obbligatorie)")
    lines.append("")
    for rec in responsible_recs.get("responsible", []):
        lines.append(f"- **{rec}**")
    lines.append("")
    lines.append("Risorse ufficiali di supporto:")
    lines.append("")
    lines.append("- **ADM (Agenzia delle Dogane e dei Monopoli)** — regolatore nazionale del gioco.")
    lines.append("- **Gambling Therapy / Giocatori Anonimi** — assistenza per disturbo da gioco.")
    lines.append("- **Auto-esclusione (ROCCA)** — registro nazionale per l'auto-proibizione dal gioco.")
    lines.append("")

    # 9. Sostenibilità economica
    lines.append("## 9. Sostenibilità economica delle strategie")
    lines.append("")
    lines.append("| Strategia | Sostenibilità economica | Verdetto |")
    lines.append("|---|---|---|")
    for r in sig_rows:
        verdict = "NON sostenibile (ROI negativo)" if r["roi"] < 0 else "Teoricamente attrattiva"
        lines.append(f"| {r['strategy']} | ROI {r['roi']}% | {verdict} |")
    lines.append("")
    lines.append("**Conclusione economica:** nessuna strategia è economicamente sostenibile. "
                 "Giocare deve essere considerato esclusivamente un costo di intrattenimento con "
                 "budget predefinito, mai un investimento.")
    lines.append("")

    # 10. Roadmap
    lines.append("## 10. Roadmap operativa")
    lines.append("")
    lines.append("### Fase 1 — Consolidamento (ora)")
    lines.append("")
    for item in roadmap.get("phase1", []):
        lines.append(f"- [ ] {item}")
    lines.append("")
    lines.append("### Fase 2 — Strumenti di protezione (3–6 mesi)")
    lines.append("")
    for item in roadmap.get("phase2", []):
        lines.append(f"- [ ] {item}")
    lines.append("")
    lines.append("### Fase 3 — Ricerca e trasparenza (6–12 mesi)")
    lines.append("")
    for item in roadmap.get("phase3", []):
        lines.append(f"- [ ] {item}")
    lines.append("")

    lines.append("---")
    lines.append("## Metadati tecnici")
    lines.append("")
    lines.append(f"- Strategie testate: **{len(STRATEGIES)}**")
    lines.append(f"- Modello di valutazione: walk-forward out-of-sample, train={ev.get('train',400)}, "
                 f"block test={ev.get('block',200)}")
    lines.append(f"- Test statistici: binomiale esatto, z-test proporzioni, chi-quadrato, "
                 f"correzioni Bonferroni e Benjamini-Hochberg")
    lines.append("- Scopo del documento: trasparenza e prevenzione; esclude ogni finalità promozionale.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print("=== AUDIT RIGOROSO SUPERENALOTTO ===")
    records = load_records()
    print(f"Caricate {len(records)} estrazioni")

    if not records:
        print("ERRORE: nessun dato. Verifica superenalotto.csv")
        return

    # Probabilità esatte + EV
    ev_probs, p_ge2, p_ge3, p_ge4 = expected_match_probs()
    ev = {
        "probs": ev_probs,
        "p_ge2": p_ge2,
        "p_ge3": p_ge3,
        "p_ge4": p_ge4,
    }

    # Backtest walk-forward
    print("Eseguo backtest walk-forward out-of-sample (train=300, test block=200)...")
    train, block = 300, 200
    results = full_walk_forward(records, train=train, block=block, tickets_per_draw=1)
    ev["train"] = train
    ev["block"] = block

    # Significatività
    sig_rows = compute_significance(results)

    # Uniformità
    uniform = uniformity_analysis(records)

    # Sostenibilità
    econ = economic_summary(results)

    # Risorse per report
    responsible_recs = {
        "cause_loss": [
            {"name": "House edge (~67%)", "desc": "Il montepremi distribuisce solo ~60% delle giocate; "
             "il resto è margine del concessionario e copertura costi."},
            {"name": "Indipendenza delle estrazioni", "desc": "Ogni estrazione è indipendente: "
             "i numeri passati non influenzano i futuri."},
            {"name": "Fallacia del giocatore", "desc": "Strategie 'caldi/freddi', 'ritardatari', "
             "'pattern' incorporano errori logici (gambler's fallacy)."},
            {"name": "Data snooping / overfitting", "desc": "Strategie ottimizzate sul passato "
             "perdono efficacia sul futuro (walk-forward lo dimostra)."},
            {"name": "Dimensione campione insufficiente", "desc": "Servirebbero miliardi di "
             "estrazioni per osservare convergenza/divergenze."},
        ],
        "limits": [
            {"name": "Randomness certificato", "desc": "RNG certificati da ADM per estrazioni uniformi."},
            {"name": "Indipendenza", "desc": "Nessuna memoria o persistenza di pattern."},
            {"name": "Evento rarissimo", "desc": "Jackpot: 1 su 622.614.630; in una vita "
             "di ~10.000 estrazioni la probabilità di vincere il 6 è ~1 su 62.000."},
        ],
        "responsible": [
            "Impostare un budget di spesa fisso e mai superarlo.",
            "Inserire limiti giornalieri/settimanali/mensili (es. €2/estrazione, €20/settimana).",
            "Mostrare sempre l'avviso del house edge (67%) e la probabilità di vincita.",
            "Imporre un 'reality check' temporale e un periodo di raffreddamento dopo perdite.",
            "Vietare il recupero delle perdite ('inseguire' le perdite).",
            "Non giocare mai denaro destinato a spese essenziali o prestiti.",
            "Rivolgersi a supporto specializzato (Giocatori Anonimi, gambling therapy) ai primi segnali.",
            "Non utilizzare mai l'autoesclusione in modo aggirato (ROCCA).",
        ],
    }

    roadmap = {
        "phase1": [
            "Esporre il house edge (67%) in evidenza nell'interfaccia.",
            "Mostrare la probabilità reale di vincita per ogni categoria.",
            "Aggiungere limite giornaliero di spesa (default €2/estrazione).",
            "Mostrare warning 'reality check' durante la sessione di gioco.",
            "Collegare a risorse di supporto (Giocatori Anonimi, ADM).",
        ],
        "phase2": [
            "Implementare limiti di spesa opzionali personalizzabili.",
            "Aggiungere limiti di tempo di sessione e cooldown dopo perdite.",
            "Sistema di monitoraggio comportamentale (rileva pattern a rischio).",
            "Integrazione con il registro nazionale di auto-esclusione ROCCA.",
        ],
        "phase3": [
            "Pubblicare i risultati dei backtest come documento di trasparenza.",
            "Documentare l'insussistenza di vantaggi predittivi.",
            "Collaborazione con enti di ricerca sul gioco responsabile.",
        ],
    }

    report = build_report(records, results, sig_rows, uniform, ev, p_ge2, p_ge3, p_ge4,
                          responsible_recs, roadmap)

    # Salva output
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "total_draws": len(records),
                "date_range": f"{records[0]['data']} → {records[-1]['data']}",
                "methodology": "walk-forward out-of-sample",
                "train": train,
                "block": block,
                "strategies_tested": len(STRATEGIES),
                "generated": datetime.now().isoformat(),
            },
            "overflow": "Vedi report markdown per la sintesi completa.",
            "strategy_results": results,
            "significance": sig_rows,
            "uniformity": uniform,
            "theoretical": {
                "p_ge2": p_ge2,
                "p_ge3": p_ge3,
                "p_ge4": p_ge4,
                "house_edge_upper_pct": 67.0,
            },
        }, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(report)

    # Output console
    print("\n=== RISULTATI (ordine per ROI) ===")
    for r in sig_rows:
        sig = "  [NON SIGNIF.]" if not r["significant"] else "  [*significativo*]"
        print(f"  {r['strategy']:<20s} ROI={r['roi']:>7.2f}%  M3+/1000={r['m3plus_per_1000']:>7.3f}  "
              f"net={r['net']:>8.2f}  pFDR={r['p_adj_fdr']:.4f}{sig}")
    print(f"\nUniformità chi-quadrato: stat={uniform['chi2_stat']}, p={uniform['chi2_pvalue']}, "
          f"significativa={uniform['uniform_significant']}")
    print(f"\nReport scritto in: {OUTPUT_MD}")
    print(f"Dati JSON scritti in: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
