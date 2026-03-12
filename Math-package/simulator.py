#!/usr/bin/env python3
"""
Educational 5x3 20-line slot simulator.
Not a real / certified gambling device.
"""
import argparse, json, random, math, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent

WILD = "W"
SCAT = "S"

def load():
    reels = json.loads((HERE/"reel_strips.json").read_text())["reels"]
    paylines = json.loads((HERE/"paylines.json").read_text())["paylines"]
    paytable = json.loads((HERE/"paytable.json").read_text())
    config = json.loads((HERE/"config.json").read_text())
    return reels, paylines, paytable, config

def spin_once(reels, rng):
    stops = [rng.randrange(len(reels[r])) for r in range(5)]
    grid = [[None]*5 for _ in range(3)]
    for r in range(5):
        strip = reels[r]
        L = len(strip)
        for row in range(3):
            grid[row][r] = strip[(stops[r] + row) % L]
    return grid, stops

def eval_line_symbols(line_syms, paytable):
    base = None
    count = 0
    for s in line_syms:
        if s == SCAT:
            break
        if s == WILD:
            count += 1
            continue
        if base is None:
            base = s
            count += 1
        else:
            if s == base:
                count += 1
            else:
                break
    if base is None:
        return 0, None, 0
    win = 0
    kind = 0
    for k in (5,4,3):
        if count >= k and base in paytable and str(k) in paytable[base]:
            win = paytable[base][str(k)]
            kind = k
            break
    return win, base, kind

def evaluate_spin(grid, paylines, paytable, total_bet):
    total = 0
    # paylines
    for line in paylines:
        syms = [grid[line[reel]][reel] for reel in range(5)]
        w, _, _ = eval_line_symbols(syms, paytable)
        total += w
    # scatter
    scat_count = sum(1 for row in range(3) for col in range(5) if grid[row][col] == SCAT)
    if scat_count >= 3 and str(scat_count) in paytable[SCAT]:
        total += paytable[SCAT][str(scat_count)] * total_bet
    return total, scat_count

def monte_carlo(spins, seed):
    reels, paylines, paytable_raw, config = load()
    # normalize paytable keys to strings for JSON compatibility
    paytable = {}
    for sym, table in paytable_raw.items():
        paytable[sym] = {str(k): int(v) for k, v in table.items()}

    rng = random.Random(seed)
    lines = config["betting"]["lines"]
    line_bet = config["betting"]["line_bet_credits"]
    total_bet = lines * line_bet

    wins = []
    hit = 0
    scat_hit = 0
    max_win = 0

    for _ in range(spins):
        grid, _ = spin_once(reels, rng)
        w, scat = evaluate_spin(grid, paylines, paytable, total_bet)
        wins.append(w)
        if w > 0:
            hit += 1
        if scat >= 3:
            scat_hit += 1
        if w > max_win:
            max_win = w

    rtp = sum(wins) / (spins * total_bet)
    mean = statistics.fmean(wins)
    var = statistics.pvariance(wins)
    sd = math.sqrt(var)
    vol_index = sd / total_bet

    return {
        "spins": spins,
        "seed": seed,
        "total_bet": total_bet,
        "rtp": rtp,
        "hold": 1-rtp,
        "hit_frequency": hit/spins,
        "scatter_hit_rate": scat_hit/spins,
        "avg_win_credits": mean,
        "stdev_win_credits": sd,
        "volatility_index": vol_index,
        "max_win_observed_credits": max_win,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spins", type=int, default=300_000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    s = monte_carlo(args.spins, args.seed)
    print(json.dumps(s, indent=2))

if __name__ == "__main__":
    main()
