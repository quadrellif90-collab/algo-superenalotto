#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, json, random
from collections import Counter, defaultdict
from datetime import datetime

CSV_PATH = "superenalotto.csv"
OUTPUT_JSON = "reverse_engineering_results.json"
PREMI = {2: 5, 3: 25, 4: 200, 5: 25000, 6: 1000000}
QUARTILES = [(1, 22), (23, 45), (46, 67), (68, 90)]
DECADES = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80), (81, 90)]

def load_draws():
    draws = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                nums = sorted([int(row["n1"]), int(row["n2"]), int(row["n3"]), int(row["n4"]), int(row["n5"]), int(row["n6"])])
                jolly = int(row["jolly"]) if row.get("jolly") else 0
                star = int(row["superstar"]) if row.get("superstar") else 0
                draws.append({"data": row["data"], "nums": nums, "jolly": jolly, "star": star})
            except (ValueError, KeyError):
                continue
    return draws

def pair_frequency(draws):
    freq = Counter()
    for d in draws:
        for i in range(6):
            for j in range(i + 1, 6):
                freq[(d["nums"][i], d["nums"][j])] += 1
    return freq

def triplet_frequency(draws):
    freq = Counter()
    for d in draws:
        for i in range(6):
            for j in range(i + 1, 6):
                for k in range(j + 1, 6):
                    freq[(d["nums"][i], d["nums"][j], d["nums"][k])] += 1
    return freq

def number_frequency(draws):
    freq = Counter()
    for d in draws:
        for n in d["nums"]:
            freq[n] += 1
    return freq

def gap_analysis(draws):
    last_seen = {}
    gaps = {}
    for i, d in enumerate(draws):
        for n in d["nums"]:
            if n in last_seen:
                gaps.setdefault(n, []).append(i - last_seen[n])
            last_seen[n] = i
    total = len(draws)
    result = {}
    for n in range(1, 91):
        cg = total - last_seen.get(n, 0)
        ag = sum(gaps.get(n, [total])) / max(len(gaps.get(n, [1])), 1)
        result[n] = {"current_gap": cg, "avg_gap": round(ag, 2), "appearances": len(gaps.get(n, []))}
    return result

def sum_distribution(draws):
    dist = Counter()
    for d in draws:
        dist[(sum(d["nums"]) // 10) * 10] += 1
    return dict(sorted(dist.items()))

def parity_distribution(draws):
    dist = Counter()
    for d in draws:
        dist[sum(1 for n in d["nums"] if n % 2 == 1)] += 1
    return dict(sorted(dist.items()))

def decade_distribution(draws):
    dist = Counter()
    for d in draws:
        for n in d["nums"]:
            dist[(n - 1) // 10] += 1
    return dict(sorted(dist.items()))

def quartile_distribution(draws):
    dist = Counter()
    for d in draws:
        for n in d["nums"]:
            for qi, (lo, hi) in enumerate(QUARTILES):
                if lo <= n <= hi:
                    dist[qi] += 1
                    break
    return dict(sorted(dist.items()))

def markov_transitions(draws):
    trans = defaultdict(Counter)
    for i in range(len(draws) - 1):
        for n1 in set(draws[i]["nums"]):
            for n2 in set(draws[i + 1]["nums"]):
                trans[n1][n2] += 1
    return trans

def autocorrelation(draws):
    appeared = Counter()
    appeared_next = Counter()
    for i in range(len(draws) - 1):
        curr = set(draws[i]["nums"])
        nxt = set(draws[i + 1]["nums"])
        for n in curr:
            appeared[n] += 1
            if n in nxt:
                appeared_next[n] += 1
    return {n: round(appeared_next.get(n, 0) / max(appeared.get(n, 1), 1), 4) for n in range(1, 91)}

def consecutive_numbers(draws):
    count = 0
    for d in draws:
        nums = d["nums"]
        for i in range(5):
            if nums[i + 1] - nums[i] == 1:
                count += 1
    return count

def print_analysis(draws):
    print("=" * 70)
    print("ANALISI STATISTICA REALE - {} estrazioni".format(len(draws)))
    print("=" * 70)
    pf = pair_frequency(draws)
    print("\n--- TOP 20 COPPIE PIU FREQUENTI ---")
    for (a, b), c in pf.most_common(20):
        print("  ({:>2},{:>2}): {} volte ({:.2f}%)".format(a, b, c, c / len(draws) * 100))
    tf = triplet_frequency(draws)
    print("\n--- TOP 15 TRIPLETTE PIU FREQUENTI ---")
    for (a, b, c), cnt in tf.most_common(15):
        print("  ({:>2},{:>2},{:>2}): {} volte ({:.3f}%)".format(a, b, c, cnt, cnt / len(draws) * 100))
    nf = number_frequency(draws)
    print("\n--- TOP 20 NUMERI PIU FREQUENTI ---")
    for n, c in nf.most_common(20):
        print("  {:>2}: {} volte ({:.2f}%)".format(n, c, c / len(draws) * 100))
    print("\n--- BOTTOM 10 NUMERI MENO FREQUENTI ---")
    for n, c in nf.most_common()[-10:]:
        print("  {:>2}: {} volte ({:.2f}%)".format(n, c, c / len(draws) * 100))
    sd = sum_distribution(draws)
    print("\n--- DISTRIBUZIONE SOMMA (bucket da 10) ---")
    for bucket, c in list(sd.items())[:20]:
        print("  Somma {}-{}: {} estrazioni".format(bucket, bucket + 9, c))
    ms = sum(sum(d["nums"]) for d in draws) / len(draws)
    print("  Somma media: {:.2f}".format(ms))
    print("  Somma min: {}, max: {}".format(min(sum(d["nums"]) for d in draws), max(sum(d["nums"]) for d in draws)))
    pd = parity_distribution(draws)
    print("\n--- DISTRIBUZIONE PARITA (numeri dispari) ---")
    for odd, c in sorted(pd.items()):
        print("  {} dispari: {} estrazioni ({:.2f}%)".format(odd, c, c / len(draws) * 100))
    dd = decade_distribution(draws)
    print("\n--- DISTRIBUZIONE DECADI ---")
    for dec, c in sorted(dd.items()):
        print("  Decade {}: {} ({:.2f}%)".format((dec + 1) * 10 - 9, c, c / (len(draws) * 6) * 100))
    qd = quartile_distribution(draws)
    print("\n--- DISTRIBUZIONE QUARTILI ---")
    for qi, c in sorted(qd.items()):
        lo, hi = QUARTILES[qi]
        print("  Q{} ({}-{}): {} ({:.2f}%)".format(qi + 1, lo, hi, c, c / (len(draws) * 6) * 100))
    ac = autocorrelation(draws)
    print("\n--- AUTOCORRELAZIONE TOP 10 (P(apparso in i | apparso in i-1)) ---")
    for n, p in sorted(ac.items(), key=lambda x: -x[1])[:10]:
        print("  Numero {:>2}: {:.4f}".format(n, p))
    print("  Autocorrelazione media: {:.4f}".format(sum(ac.values()) / len(ac)))
    cons = consecutive_numbers(draws)
    print("\n--- NUMERI CONSECUTIVI ---")
    print("  Coppie consecutive totali: {} (su {} estrazioni, {:.2f} per estrazione)".format(cons, len(draws), cons / len(draws)))
    gaps = gap_analysis(draws)
    print("\n--- GAP ANALYSIS TOP 10 OVERDUE ---")
    for n, g in sorted(gaps.items(), key=lambda x: -x[1]["current_gap"])[:10]:
        print("  Numero {:>2}: gap {} (media {:.1f}, apparso {} volte)".format(n, g["current_gap"], g["avg_gap"], g["appearances"]))
    mt = markov_transitions(draws)
    print("\n--- MARKOV: TOP 10 transizioni per numero 85 ---")
    if 85 in mt:
        for n2, c in mt[85].most_common(10):
            print("  85 -> {}: {} volte".format(n2, c))
    print("=" * 70)

def _valid(nums):
    s = sum(nums)
    if not (200 <= s <= 360):
        return False
    dec = Counter((n - 1) // 10 for n in nums)
    if max(dec.values()) > 2:
        return False
    return True

def _seed(name, idx):
    return random.Random(hash(name) % 2**31 + idx)

def strat_random(h, di):
    rng = _seed("Random", di)
    for _ in range(200):
        nums = sorted(rng.sample(range(1, 91), 6))
        if _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_hot(h, di):
    if not h:
        return strat_random(h, di)
    freq = Counter(n for d in h for n in d["nums"])
    top = [n for n, _ in freq.most_common(20)]
    return sorted(_seed("Hot", di).sample(top, 6))

def strat_cold(h, di):
    if not h:
        return strat_random(h, di)
    freq = Counter(n for d in h for n in d["nums"])
    bottom = [n for n, _ in freq.most_common()[-20:]]
    return sorted(_seed("Cold", di).sample(bottom, 6))

def strat_hotcold_mix(h, di):
    if not h:
        return strat_random(h, di)
    freq = Counter(n for d in h for n in d["nums"])
    top = [n for n, _ in freq.most_common(30)]
    bottom = [n for n, _ in freq.most_common()[-30:]]
    rng = _seed("HotColdMix", di)
    for _ in range(200):
        nh = rng.randint(2, 4)
        nc = 6 - nh
        nums = sorted(rng.sample(top, nh) + rng.sample(bottom, nc))
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_sum_locked(h, di):
    if len(h) < 50:
        return strat_random(h, di)
    recent = h[-100:]
    target = int(sum(sum(d["nums"]) for d in recent) / len(recent))
    rng = _seed("SumLocked", di)
    for _ in range(200):
        nums = sorted(rng.sample(range(1, 91), 6))
        if abs(sum(nums) - target) <= 15 and _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_quartile_balanced(h, di):
    rng = _seed("QuartileBalanced", di)
    for _ in range(200):
        alloc = [1, 1, 2, 2]
        rng.shuffle(alloc)
        nums = []
        for qi, (lo, hi) in enumerate(QUARTILES):
            nums.extend(rng.sample(range(lo, hi + 1), alloc[qi]))
        nums = sorted(nums)
        if _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_decade_balanced(h, di):
    rng = _seed("DecadeBalanced", di)
    for _ in range(200):
        chosen = rng.sample(range(9), 6)
        nums = []
        for dec in chosen:
            lo, hi = DECADES[dec]
            nums.append(rng.randint(lo, hi))
        nums = sorted(set(nums))
        if len(nums) == 6 and _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_odd_even(h, di):
    odds = list(range(1, 91, 2))
    evens = list(range(2, 91, 2))
    rng = _seed("OddEven", di)
    for _ in range(200):
        nums = sorted(rng.sample(odds, 3) + rng.sample(evens, 3))
        if _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_gap_weighted(h, di):
    if len(h) < 50:
        return strat_random(h, di)
    last_seen = {}
    for i, d in enumerate(h):
        for n in d["nums"]:
            last_seen[n] = i
    total = len(h)
    pool = list(range(1, 91))
    w = [total - last_seen.get(n, 0) + 1 for n in pool]
    rng = _seed("GapWeighted", di)
    for _ in range(200):
        nums = []
        p = list(pool)
        wc = list(w)
        for _ in range(6):
            ch = rng.choices(p, weights=wc)[0]
            nums.append(ch)
            idx = p.index(ch)
            p.pop(idx)
            wc.pop(idx)
        nums = sorted(nums)
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_frequency_weighted(h, di):
    if not h:
        return strat_random(h, di)
    freq = Counter(n for d in h for n in d["nums"])
    pool = list(range(1, 91))
    w = [freq.get(n, 0) + 1 for n in pool]
    rng = _seed("FreqWeighted", di)
    for _ in range(200):
        nums = []
        p = list(pool)
        wc = list(w)
        for _ in range(6):
            ch = rng.choices(p, weights=wc)[0]
            nums.append(ch)
            idx = p.index(ch)
            p.pop(idx)
            wc.pop(idx)
        nums = sorted(nums)
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_anti_recent(h, di):
    if len(h) < 10:
        return strat_random(h, di)
    recent = set()
    for d in h[-3:]:
        recent.update(d["nums"])
    available = [n for n in range(1, 91) if n not in recent]
    rng = _seed("AntiRecent", di)
    for _ in range(200):
        nums = sorted(rng.sample(available, 6))
        if _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_consecutive_avoid(h, di):
    rng = _seed("ConsecutiveAvoid", di)
    for _ in range(200):
        nums = sorted(rng.sample(range(1, 91), 6))
        if not any(nums[i + 1] - nums[i] == 1 for i in range(5)) and _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_markov_chain(h, di):
    if len(h) < 50:
        return strat_random(h, di)
    trans = defaultdict(Counter)
    for i in range(len(h) - 1):
        for n1 in set(h[i]["nums"]):
            for n2 in set(h[i + 1]["nums"]):
                trans[n1][n2] += 1
    last_draw = set(h[-1]["nums"])
    votes = Counter()
    for n1 in last_draw:
        for n2, c in trans[n1].items():
            votes[n2] += c
    top = [n for n, _ in votes.most_common(20)]
    rng = _seed("MarkovChain", di)
    if len(top) >= 6:
        for _ in range(200):
            nums = sorted(rng.sample(top, 6))
            if _valid(nums):
                return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_pair_markov(h, di):
    if len(h) < 50:
        return strat_random(h, di)
    pf = pair_frequency(h)
    last_nums = set(h[-1]["nums"])
    votes = Counter()
    for (a, b), c in pf.items():
        if a in last_nums:
            votes[b] += c
        if b in last_nums:
            votes[a] += c
    top = [n for n, _ in votes.most_common(20)]
    rng = _seed("PairMarkov", di)
    if len(top) >= 6:
        for _ in range(200):
            nums = sorted(rng.sample(top, 6))
            if _valid(nums):
                return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_sum_quartile_combo(h, di):
    if len(h) < 50:
        return strat_random(h, di)
    recent = h[-100:]
    target = int(sum(sum(d["nums"]) for d in recent) / len(recent))
    rng = _seed("SumQuartile", di)
    for _ in range(200):
        alloc = [1, 1, 2, 2]
        rng.shuffle(alloc)
        nums = []
        for qi, (lo, hi) in enumerate(QUARTILES):
            nums.extend(rng.sample(range(lo, hi + 1), alloc[qi]))
        nums = sorted(nums)
        if abs(sum(nums) - target) <= 20 and _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_overdue_hot_combo(h, di):
    if len(h) < 50:
        return strat_random(h, di)
    freq = Counter(n for d in h for n in d["nums"])
    last_seen = {}
    for i, d in enumerate(h):
        for n in d["nums"]:
            last_seen[n] = i
    total = len(h)
    overdue = sorted(range(1, 91), key=lambda n: -(total - last_seen.get(n, 0)))[:30]
    hot = [n for n, _ in freq.most_common(30)]
    pool = list(set(overdue) | set(hot))
    rng = _seed("OverdueHot", di)
    for _ in range(200):
        nums = sorted(rng.sample(pool, 6))
        if _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))

def strat_ensemble(h, di):
    strats = [strat_hotcold_mix, strat_sum_locked, strat_gap_weighted, strat_markov_chain]
    votes = Counter()
    for s in strats:
        for n in s(h, di):
            votes[n] += 1
    top = [n for n, _ in votes.most_common(20)]
    rng = _seed("Ensemble", di)
    if len(top) >= 6:
        for _ in range(200):
            nums = sorted(rng.sample(top, 6))
            if _valid(nums):
                return nums
    return sorted(rng.sample(range(1, 91), 6))

STRATEGIES = {
    "Random": strat_random,
    "HotNumbers": strat_hot,
    "ColdNumbers": strat_cold,
    "HotColdMix": strat_hotcold_mix,
    "SumLocked": strat_sum_locked,
    "QuartileBalanced": strat_quartile_balanced,
    "DecadeBalanced": strat_decade_balanced,
    "OddEvenBalanced": strat_odd_even,
    "GapWeighted": strat_gap_weighted,
    "FrequencyWeighted": strat_frequency_weighted,
    "AntiRecent": strat_anti_recent,
    "ConsecutiveAvoid": strat_consecutive_avoid,
    "MarkovChain": strat_markov_chain,
    "PairMarkov": strat_pair_markov,
    "SumQuartileCombo": strat_sum_quartile_combo,
    "OverdueHotCombo": strat_overdue_hot_combo,
    "Ensemble": strat_ensemble,
}

def run_backtest(draws, start_index=200):
    n = len(draws)
    results = {name: {"match2": 0, "match3": 0, "match4": 0, "match5": 0, "match6": 0, "jolly_hit": 0, "total_spent": 0, "total_won": 0, "m3_plus": 0} for name in STRATEGIES}
    print("\n" + "=" * 70)
    print("BACKTEST WALK-FORWARD (estrazioni {}-{})".format(start_index, n - 1))
    print("=" * 70)
    print("Strategie: {}".format(len(STRATEGIES)))
    print("Predizioni per strategia: {}".format(n - start_index))
    print("Totale predizioni: {}".format(len(STRATEGIES) * (n - start_index)))
    print("=" * 70)
    for i in range(start_index, n):
        history = draws[:i]
        actual = set(draws[i]["nums"])
        jolly = draws[i]["jolly"]
        for name, fn in STRATEGIES.items():
            ticket = fn(history, i)
            matches = len(set(ticket) & actual)
            results[name]["total_spent"] += 1
            if matches == 6:
                results[name]["match6"] += 1; results[name]["total_won"] += PREMI[6]; results[name]["m3_plus"] += 1
            elif matches == 5:
                results[name]["match5"] += 1; results[name]["total_won"] += PREMI[5]; results[name]["m3_plus"] += 1
                if jolly and jolly in ticket: results[name]["jolly_hit"] += 1
            elif matches == 4:
                results[name]["match4"] += 1; results[name]["total_won"] += PREMI[4]; results[name]["m3_plus"] += 1
            elif matches == 3:
                results[name]["match3"] += 1; results[name]["total_won"] += PREMI[3]; results[name]["m3_plus"] += 1
            elif matches == 2:
                results[name]["match2"] += 1; results[name]["total_won"] += PREMI[2]
        if (i - start_index) % 500 == 0:
            print("  Progresso: {}/{} ({:.1f}%)".format(i - start_index, n - start_index, (i - start_index) / (n - start_index) * 100))
    ranking = []
    for name, r in results.items():
        spent = r["total_spent"]; won = r["total_won"]
        roi = ((won - spent) / spent * 100) if spent > 0 else 0
        m3 = (r["m3_plus"] / spent * 1000) if spent > 0 else 0
        m2 = (r["match2"] / spent * 1000) if spent > 0 else 0
        ranking.append({"strategy": name, "match2": r["match2"], "match3": r["match3"], "match4": r["match4"], "match5": r["match5"], "match6": r["match6"], "jolly_hit": r["jolly_hit"], "m3_plus": r["m3_plus"], "m3_per_1000": round(m3, 2), "m2_per_1000": round(m2, 2), "total_spent": spent, "total_won": won, "roi_percent": round(roi, 2)})
    ranking.sort(key=lambda x: x["roi_percent"], reverse=True)
    return ranking

def main():
    print("Caricamento estrazioni da {} ...".format(CSV_PATH))
    draws = load_draws()
    print("Caricate {} estrazioni ({} - {})".format(len(draws), draws[0]["data"], draws[-1]["data"]))
    print_analysis(draws)
    ranking = run_backtest(draws, start_index=200)
    print("\n" + "=" * 70)
    print("RISULTATI BACKTEST - RANKING FINALE")
    print("=" * 70)
    print("{:<22} {:>8} {:>8} {:>6} {:>6} {:>6} {:>6} {:>10} {:>10} {:>8}".format("Strategia", "M2/1000", "M3/1000", "M2", "M3", "M4", "M5+", "Speso", "Vinto", "ROI%"))
    print("-" * 100)
    for r in ranking:
        m5p = r["match5"] + r["match6"]
        print("{:<22} {:>8.2f} {:>8.2f} {:>6} {:>6} {:>6} {:>6} {:>10} {:>10} {:>8.2f}".format(r["strategy"], r["m2_per_1000"], r["m3_per_1000"], r["match2"], r["match3"], r["match4"], m5p, r["total_spent"], r["total_won"], r["roi_percent"]))
    print("\n" + "=" * 70)
    print("MIGLIORE STRATEGIA: {}".format(ranking[0]["strategy"]))
    print("  ROI: {:.2f}%".format(ranking[0]["roi_percent"]))
    print("  M3+/1000: {:.2f}".format(ranking[0]["m3_per_1000"]))
    print("  M2/1000: {:.2f}".format(ranking[0]["m2_per_1000"]))
    m5p = ranking[0]["match5"] + ranking[0]["match6"]
    print("  Match 2: {}  Match 3: {}  Match 4: {}  Match 5+: {}".format(ranking[0]["match2"], ranking[0]["match3"], ranking[0]["match4"], m5p))
    print("  Speso: {} EUR  Vinto: {} EUR".format(ranking[0]["total_spent"], ranking[0]["total_won"]))
    print("=" * 70)
    output = {"metadata": {"total_draws": len(draws), "date_range": "{} to {}".format(draws[0]["data"], draws[-1]["data"]), "backtest_start": 200, "predictions_per_strategy": len(draws) - 200, "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, "ranking": ranking, "best_strategy": ranking[0]}
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("\nRisultati salvati in: {}".format(OUTPUT_JSON))

if __name__ == "__main__":
    main()
