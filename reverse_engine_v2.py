#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import json
import random
import math
from collections import Counter, defaultdict

CSV_PATH = "superenalotto.csv"
OUTPUT_JSON = "reverse_engineering_v2_results.json"
PREMI = {2: 5, 3: 25, 4: 200, 5: 25000, 6: 1000000}
QUARTILES = [(1, 22), (23, 45), (46, 67), (68, 90)]
DECADES = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80), (81, 90)]


# ---------------------------------------------------------------------------
# Data loading & analysis helpers
# ---------------------------------------------------------------------------
def load_draws():
    draws = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                nums = sorted([int(row["n1"]), int(row["n2"]), int(row["n3"]),
                                int(row["n4"]), int(row["n5"]), int(row["n6"])])
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


def markov_transitions(draws):
    trans = defaultdict(Counter)
    for i in range(len(draws) - 1):
        for n1 in set(draws[i]["nums"]):
            for n2 in set(draws[i + 1]["nums"]):
                trans[n1][n2] += 1
    return trans


# ---------------------------------------------------------------------------
# Validation & seeding
# ---------------------------------------------------------------------------
def _valid(nums):
    s = sum(nums)
    if not (200 <= s <= 360):
        return False
    dec = Counter((n - 1) // 10 for n in nums)
    if max(dec.values()) > 2:
        return False
    return True


def _rng(name, di, ti=0):
    return random.Random(hash(name) % (2 ** 31) + di + ti)


def _fallback(rng):
    for _ in range(300):
        nums = sorted(rng.sample(range(1, 91), 6))
        if _valid(nums):
            return nums
    return sorted(rng.sample(range(1, 91), 6))


def _sample_unique(rng, pool, k):
    pool = list(pool)
    if len(pool) < k:
        pool = list(range(1, 91))
    return rng.sample(pool, k)


# ---------------------------------------------------------------------------
# Base strategies (history, draw_index, ticket_index=0)
# ---------------------------------------------------------------------------
def strat_random(h, di, ti=0):
    rng = _rng("Random", di, ti)
    return _fallback(rng)


def strat_hot_numbers(h, di, ti=0):
    rng = _rng("HotNumbers", di, ti)
    if len(h) < 20:
        return _fallback(rng)
    freq = number_frequency(h)
    top = [n for n, _ in freq.most_common(20)]
    for _ in range(200):
        nums = sorted(_sample_unique(rng, top, 6))
        if _valid(nums):
            return nums
    return _fallback(rng)


def strat_pair_markov(h, di, ti=0):
    rng = _rng("PairMarkov", di, ti)
    if len(h) < 50:
        return _fallback(rng)
    pf = pair_frequency(h)
    last_nums = set(h[-1]["nums"])
    votes = Counter()
    for (a, b), c in pf.items():
        if a in last_nums:
            votes[b] += c
        if b in last_nums:
            votes[a] += c
    top = [n for n, _ in votes.most_common(20)]
    if len(top) < 6:
        return _fallback(rng)
    for _ in range(200):
        nums = sorted(_sample_unique(rng, top, 6))
        if _valid(nums):
            return nums
    return _fallback(rng)


def strat_odd_even(h, di, ti=0):
    rng = _rng("OddEvenBalanced", di, ti)
    odds = list(range(1, 91, 2))
    evens = list(range(2, 91, 2))
    for _ in range(200):
        nums = sorted(_sample_unique(rng, odds, 3) + _sample_unique(rng, evens, 3))
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return _fallback(rng)


def strat_sum_quartile_combo(h, di, ti=0):
    rng = _rng("SumQuartileCombo", di, ti)
    if len(h) < 50:
        return _fallback(rng)
    recent = h[-100:]
    target = int(sum(sum(d["nums"]) for d in recent) / len(recent))
    for _ in range(200):
        alloc = [1, 1, 2, 2]
        rng.shuffle(alloc)
        nums = []
        for qi, (lo, hi) in enumerate(QUARTILES):
            nums.extend(_sample_unique(rng, range(lo, hi + 1), alloc[qi]))
        nums = sorted(nums)
        if abs(sum(nums) - target) <= 20 and _valid(nums):
            return nums
    return _fallback(rng)


def strat_hotcold_mix(h, di, ti=0, nh=3, nc=3, window=30):
    """Default HotColdMix: 3 hot + 3 cold from top/bottom 30."""
    rng = _rng("HotColdMix", di, ti)
    if len(h) < 20:
        return _fallback(rng)
    freq = number_frequency(h)
    top = [n for n, _ in freq.most_common(window)]
    bottom = [n for n, _ in freq.most_common()[-window:]]
    for _ in range(200):
        try:
            nums = sorted(_sample_unique(rng, top, nh) + _sample_unique(rng, bottom, nc))
        except ValueError:
            continue
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return _fallback(rng)


def strat_ensemble(h, di, ti=0):
    rng = _rng("Ensemble", di, ti)
    if len(h) < 50:
        return _fallback(rng)
    sub_strats = [strat_hotcold_mix, strat_pair_markov, strat_odd_even,
                  strat_hot_numbers, strat_sum_quartile_combo]
    votes = Counter()
    for s in sub_strats:
        for n in s(h, di, ti):
            votes[n] += 1
    top = [n for n, _ in votes.most_common(20)]
    if len(top) < 6:
        return _fallback(rng)
    for _ in range(200):
        nums = sorted(_sample_unique(rng, top, 6))
        if _valid(nums):
            return nums
    return _fallback(rng)


# ---------------------------------------------------------------------------
# A. HotColdMix variants (varying hot/cold ratio & window)
# ---------------------------------------------------------------------------
def make_hc_variant(name, nh, nc, window):
    def fn(h, di, ti=0):
        return strat_hotcold_mix(h, di, ti, nh=nh, nc=nc, window=window)
    fn.__name__ = name
    return fn


HC_VARIANTS = {
    "HC_2_4": make_hc_variant("HC_2_4", 2, 4, 20),
    "HC_3_3": make_hc_variant("HC_3_3", 3, 3, 30),
    "HC_4_2": make_hc_variant("HC_4_2", 4, 2, 20),
    "HC_1_5": make_hc_variant("HC_1_5", 1, 5, 20),
    "HC_5_1": make_hc_variant("HC_5_1", 5, 1, 20),
    "HC_2_4_wide": make_hc_variant("HC_2_4_wide", 2, 4, 40),
    "HC_3_3_wide": make_hc_variant("HC_3_3_wide", 3, 3, 40),
    "HC_3_3_top10": make_hc_variant("HC_3_3_top10", 3, 3, 10),
    "HC_3_3_top50": make_hc_variant("HC_3_3_top50", 3, 3, 50),
}


# ---------------------------------------------------------------------------
# E. Advanced strategies
# ---------------------------------------------------------------------------
def strat_hot_warm(h, di, ti=0):
    """3 hot (top 15) + 3 medium (rank 38-52)."""
    rng = _rng("HotWarm", di, ti)
    if len(h) < 20:
        return _fallback(rng)
    freq = number_frequency(h)
    ranked = [n for n, _ in freq.most_common()]
    hot = ranked[:15]
    medium = ranked[37:52] if len(ranked) >= 52 else ranked[len(ranked)//2:]
    for _ in range(200):
        try:
            nums = sorted(_sample_unique(rng, hot, 3) + _sample_unique(rng, medium, 3))
        except ValueError:
            continue
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return _fallback(rng)


def strat_cold_gap(h, di, ti=0):
    """3 coldest (most overdue) + 3 with avg gap (rank 38-52)."""
    rng = _rng("ColdGap", di, ti)
    if len(h) < 50:
        return _fallback(rng)
    gaps = gap_analysis(h)
    coldest = sorted(range(1, 91), key=lambda n: -gaps[n]["current_gap"])[:20]
    avg_ranked = sorted(range(1, 91), key=lambda n: gaps[n]["avg_gap"])
    mid = avg_ranked[37:52] if len(avg_ranked) >= 52 else avg_ranked[len(avg_ranked)//2:]
    for _ in range(200):
        try:
            nums = sorted(_sample_unique(rng, coldest, 3) + _sample_unique(rng, mid, 3))
        except ValueError:
            continue
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return _fallback(rng)


def strat_pair_based(h, di, ti=0):
    """Pick numbers forming best pairs with last draw numbers."""
    rng = _rng("PairBased", di, ti)
    if len(h) < 50:
        return _fallback(rng)
    pf = pair_frequency(h)
    last_nums = set(h[-1]["nums"])
    votes = Counter()
    for (a, b), c in pf.items():
        if a in last_nums:
            votes[b] += c
        if b in last_nums:
            votes[a] += c
    pool = [n for n, _ in votes.most_common(30)]
    pool += [n for n in range(1, 91) if n not in votes][:20]
    pool = list(dict.fromkeys(pool))
    if len(pool) < 6:
        return _fallback(rng)
    for _ in range(200):
        nums = sorted(_sample_unique(rng, pool, 6))
        if _valid(nums):
            return nums
    return _fallback(rng)


def strat_recent20(h, di, ti=0):
    """Pick from numbers appearing in last 20 draws (frequency weighted)."""
    rng = _rng("Recent20", di, ti)
    if len(h) < 20:
        return _fallback(rng)
    recent = h[-20:]
    freq = number_frequency(recent)
    pool = list(freq.keys())
    if not pool:
        return _fallback(rng)
    weights = [freq[n] + 1 for n in pool]
    for _ in range(200):
        nums = []
        p = list(pool)
        wc = list(weights)
        for _ in range(6):
            if not p:
                break
            ch = rng.choices(p, weights=wc)[0]
            nums.append(ch)
            idx = p.index(ch)
            p.pop(idx)
            wc.pop(idx)
        nums = sorted(nums)
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return _fallback(rng)


def strat_anti_recent5(h, di, ti=0):
    """Exclude numbers from last 5 draws."""
    rng = _rng("AntiRecent5", di, ti)
    if len(h) < 10:
        return _fallback(rng)
    recent = set()
    for d in h[-5:]:
        recent.update(d["nums"])
    available = [n for n in range(1, 91) if n not in recent]
    if len(available) < 6:
        return _fallback(rng)
    for _ in range(200):
        nums = sorted(_sample_unique(rng, available, 6))
        if _valid(nums):
            return nums
    return _fallback(rng)


def strat_sum_optimal(h, di, ti=0):
    """Target sum = running mean +/- 10, with decade constraint."""
    rng = _rng("SumOptimal", di, ti)
    if len(h) < 50:
        return _fallback(rng)
    recent = h[-100:]
    target = int(sum(sum(d["nums"]) for d in recent) / len(recent))
    for _ in range(300):
        nums = sorted(rng.sample(range(1, 91), 6))
        if abs(sum(nums) - target) <= 10 and _valid(nums):
            return nums
    return _fallback(rng)


def strat_three_quartile(h, di, ti=0):
    """2-2-2 across first 3 quartiles (skip Q4)."""
    rng = _rng("ThreeQuartile", di, ti)
    for _ in range(200):
        nums = []
        for qi in range(3):
            lo, hi = QUARTILES[qi]
            nums.extend(_sample_unique(rng, range(lo, hi + 1), 2))
        nums = sorted(nums)
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return _fallback(rng)


def strat_spread43(h, di, ti=0):
    """4 numbers in range 1-50, 2 in range 51-90."""
    rng = _rng("Spread43", di, ti)
    for _ in range(200):
        nums = sorted(_sample_unique(rng, range(1, 51), 4) + _sample_unique(rng, range(51, 91), 2))
        if len(set(nums)) == 6 and _valid(nums):
            return nums
    return _fallback(rng)


# ---------------------------------------------------------------------------
# C. Combined strategies (2-strategy tickets, 3 + 3)
# ---------------------------------------------------------------------------
def _combine_three_three(h, di, ti, name, fn_a, fn_b):
    a = fn_a(h, di, ti)
    b = fn_b(h, di, ti + 50000)
    chosen = list(a[:3])
    for n in b:
        if n not in chosen and len(chosen) < 6:
            chosen.append(n)
    for n in a[3:]:
        if n not in chosen and len(chosen) < 6:
            chosen.append(n)
    nums = sorted(chosen)
    if len(nums) == 6 and _valid(nums):
        return nums
    rng = _rng(name, di, ti)
    return _fallback(rng)


def strat_hc_pm(h, di, ti=0):
    return _combine_three_three(h, di, ti, "HC_PM", strat_hotcold_mix, strat_pair_markov)


def strat_hc_oe(h, di, ti=0):
    return _combine_three_three(h, di, ti, "HC_OE", strat_hotcold_mix, strat_odd_even)


def strat_hc_hn(h, di, ti=0):
    return _combine_three_three(h, di, ti, "HC_HN", strat_hotcold_mix, strat_hot_numbers)


def strat_pm_oe(h, di, ti=0):
    return _combine_three_three(h, di, ti, "PM_OE", strat_pair_markov, strat_odd_even)


def strat_hc_sq(h, di, ti=0):
    return _combine_three_three(h, di, ti, "HC_SQ", strat_hotcold_mix, strat_sum_quartile_combo)


# ---------------------------------------------------------------------------
# Strategy registries
# ---------------------------------------------------------------------------
BASE_STRATEGIES = {
    "HotColdMix": strat_hotcold_mix,
    "PairMarkov": strat_pair_markov,
    "OddEvenBalanced": strat_odd_even,
    "HotNumbers": strat_hot_numbers,
    "Ensemble": strat_ensemble,
    "SumQuartileCombo": strat_sum_quartile_combo,
}

ADVANCED_STRATEGIES = {
    "HotWarm": strat_hot_warm,
    "ColdGap": strat_cold_gap,
    "PairBased": strat_pair_based,
    "Recent20": strat_recent20,
    "AntiRecent5": strat_anti_recent5,
    "SumOptimal": strat_sum_optimal,
    "ThreeQuartile": strat_three_quartile,
    "Spread43": strat_spread43,
}

COMBINED_STRATEGIES = {
    "HC_PM": strat_hc_pm,
    "HC_OE": strat_hc_oe,
    "HC_HN": strat_hc_hn,
    "PM_OE": strat_pm_oe,
    "HC_SQ": strat_hc_sq,
}

MULTI_TICKET_STRATEGIES = {
    "HotColdMix": strat_hotcold_mix,
    "PairMarkov": strat_pair_markov,
    "OddEvenBalanced": strat_odd_even,
    "HotNumbers": strat_hot_numbers,
    "Ensemble": strat_ensemble,
}

ALL_SINGLE_STRATEGIES = {}
ALL_SINGLE_STRATEGIES.update(BASE_STRATEGIES)
ALL_SINGLE_STRATEGIES.update(HC_VARIANTS)
ALL_SINGLE_STRATEGIES.update(ADVANCED_STRATEGIES)
ALL_SINGLE_STRATEGIES.update(COMBINED_STRATEGIES)


# ---------------------------------------------------------------------------
# Walk-forward backtest core
# ---------------------------------------------------------------------------
def evaluate_ticket(ticket, actual, jolly):
    matches = len(set(ticket) & actual)
    won = PREMI.get(matches, 0)
    m3_plus = 1 if matches >= 3 else 0
    jolly_hit = 1 if (jolly and matches >= 5 and jolly in ticket) else 0
    return matches, won, m3_plus, jolly_hit


def backtest(draws, strategies, start_index=200, num_tickets=1, label=""):
    n = len(draws)
    if start_index >= n:
        return []
    results = {name: {"match2": 0, "match3": 0, "match4": 0, "match5": 0, "match6": 0,
                      "jolly_hit": 0, "total_spent": 0, "total_won": 0, "m3_plus": 0,
                      "matches_list": [0] * 7}
               for name in strategies}
    total_steps = n - start_index
    for i in range(start_index, n):
        history = draws[:i]
        actual = set(draws[i]["nums"])
        jolly = draws[i]["jolly"]
        for name, fn in strategies.items():
            for ti in range(num_tickets):
                ticket = fn(history, i, ti)
                m, won, m3, jh = evaluate_ticket(ticket, actual, jolly)
                r = results[name]
                r["total_spent"] += 1
                r["total_won"] += won
                r["m3_plus"] += m3
                r["jolly_hit"] += jh
                r["matches_list"][m] += 1
                if m == 6:
                    r["match6"] += 1
                elif m == 5:
                    r["match5"] += 1
                elif m == 4:
                    r["match4"] += 1
                elif m == 3:
                    r["match3"] += 1
                elif m == 2:
                    r["match2"] += 1
        if (i - start_index) % 500 == 0:
            print("  [{}] Progresso: {}/{} ({:.1f}%)".format(
                label, i - start_index, total_steps,
                (i - start_index) / total_steps * 100))
    ranking = []
    for name, r in results.items():
        spent = r["total_spent"]
        won = r["total_won"]
        roi = ((won - spent) / spent * 100) if spent > 0 else 0.0
        m3 = (r["m3_plus"] / spent * 1000) if spent > 0 else 0.0
        m2 = (r["match2"] / spent * 1000) if spent > 0 else 0.0
        ranking.append({
            "strategy": name, "tickets": num_tickets,
            "match2": r["match2"], "match3": r["match3"], "match4": r["match4"],
            "match5": r["match5"], "match6": r["match6"],
            "jolly_hit": r["jolly_hit"], "m3_plus": r["m3_plus"],
            "m3_per_1000": round(m3, 2), "m2_per_1000": round(m2, 2),
            "total_spent": spent, "total_won": won,
            "roi_percent": round(roi, 2),
        })
    ranking.sort(key=lambda x: x["roi_percent"], reverse=True)
    return ranking


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Caricamento estrazioni da {} ...".format(CSV_PATH))
    draws = load_draws()
    print("Caricate {} estrazioni ({} - {})".format(
        len(draws), draws[0]["data"], draws[-1]["data"]))

    all_rankings = []

    # ----- Main backtest: all single-ticket strategies -----
    print("\n" + "=" * 70)
    print("FASE 1 - BACKTEST PRINCIPALE (strategie singole)")
    print("=" * 70)
    main_rank = backtest(draws, ALL_SINGLE_STRATEGIES, start_index=200,
                         num_tickets=1, label="MAIN")
    all_rankings.extend(main_rank)

    # ----- B. Multi-ticket tests -----
    print("\n" + "=" * 70)
    print("FASE 2 - MULTI-TICKET (2, 5, 10 biglietti)")
    print("=" * 70)
    for nt in (2, 5, 10):
        mt_rank = backtest(draws, MULTI_TICKET_STRATEGIES, start_index=200,
                           num_tickets=nt, label="MT{}".format(nt))
        for r in mt_rank:
            r["strategy"] = "{}_x{}".format(r["strategy"], nt)
        all_rankings.extend(mt_rank)

    # ----- D. Time window tests on top 5 from main backtest -----
    print("\n" + "=" * 70)
    print("FASE 3 - TIME WINDOW (top 5 strategie)")
    print("=" * 70)
    top5_names = [r["strategy"] for r in main_rank[:5]]
    print("Top 5 strategie per time window: {}".format(top5_names))
    top5_strats = {name: ALL_SINGLE_STRATEGIES[name] for name in top5_names
                   if name in ALL_SINGLE_STRATEGIES}
    windows = {
        "Full": draws[200:],
        "Last2000": draws[-2000:],
        "Last1000": draws[-1000:],
        "Last500": draws[-500:],
        "Last200": draws[-200:],
    }
    for wname, wdraws in windows.items():
        if len(wdraws) < 250:
            continue
        start = 200 if len(wdraws) > 200 else len(wdraws) // 2
        tw_rank = backtest(wdraws, top5_strats, start_index=start,
                           num_tickets=1, label="TW_{}".format(wname))
        for r in tw_rank:
            r["strategy"] = "{}_{}".format(r["strategy"], wname)
        all_rankings.extend(tw_rank)

    # ----- Aggregate & rank -----
    all_rankings.sort(key=lambda x: x["roi_percent"], reverse=True)

    print("\n" + "=" * 70)
    print("RISULTATI COMPLETI - RANKING PER ROI")
    print("=" * 70)
    print("{:<28} {:>4} {:>8} {:>8} {:>6} {:>6} {:>6} {:>6} {:>10} {:>10} {:>9}".format(
        "Strategia", "Tkt", "M2/1k", "M3/1k", "M2", "M3", "M4", "M5+", "Speso", "Vinto", "ROI%"))
    print("-" * 116)
    for r in all_rankings:
        m5p = r["match5"] + r["match6"]
        print("{:<28} {:>4} {:>8.2f} {:>8.2f} {:>6} {:>6} {:>6} {:>6} {:>10} {:>10} {:>9.2f}".format(
            r["strategy"], r["tickets"], r["m2_per_1000"], r["m3_per_1000"],
            r["match2"], r["match3"], r["match4"], m5p,
            r["total_spent"], r["total_won"], r["roi_percent"]))

    print("\n" + "=" * 70)
    print("TOP 10 ASSOLUTO")
    print("=" * 70)
    for i, r in enumerate(all_rankings[:10], 1):
        m5p = r["match5"] + r["match6"]
        print("  #{}: {:<28} ROI={:.2f}%  M3+/1k={:.2f}  M2/1k={:.2f}  "
              "M2={} M3={} M4={} M5+={}  Jolly={}  Speso={} Vinto={}".format(
                  i, r["strategy"], r["roi_percent"], r["m3_per_1000"],
                  r["m2_per_1000"], r["match2"], r["match3"], r["match4"],
                  m5p, r["jolly_hit"], r["total_spent"], r["total_won"]))

    winner = all_rankings[0]
    print("\n" + "=" * 70)
    print("VINCITORE ASSOLUTO: {}".format(winner["strategy"]))
    print("  ROI: {:.2f}%".format(winner["roi_percent"]))
    print("  M3+/1000: {:.2f}  M2/1000: {:.2f}".format(
        winner["m3_per_1000"], winner["m2_per_1000"]))
    m5p = winner["match5"] + winner["match6"]
    print("  Match 2: {}  Match 3: {}  Match 4: {}  Match 5+: {}".format(
        winner["match2"], winner["match3"], winner["match4"], m5p))
    print("  Jolly hit: {}  Speso: {} EUR  Vinto: {} EUR".format(
        winner["jolly_hit"], winner["total_spent"], winner["total_won"]))
    print("=" * 70)

    output = {
        "metadata": {
            "total_draws": len(draws),
            "date_range": "{} to {}".format(draws[0]["data"], draws[-1]["data"]),
            "backtest_start": 200,
            "predictions_per_strategy": len(draws) - 200,
            "single_strategies": len(ALL_SINGLE_STRATEGIES),
            "multi_ticket_configs": len(MULTI_TICKET_STRATEGIES) * 3,
            "time_windows": list(windows.keys()),
            "total_configs": len(all_rankings),
        },
        "ranking": all_rankings,
        "top5_single": main_rank[:5],
        "absolute_winner": winner,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("\nRisultati salvati in: {}".format(OUTPUT_JSON))


if __name__ == "__main__":
    main()
