# Math Package

**Educational 5×3 20-Line Slot Machine — Transparent Math Model**

This directory contains a complete, transparent slot machine math package that lets readers **design and simulate their own slot machine** and produce a PAR sheet — exactly as described in the book.

Every component of the game math is defined in plain JSON files. Change the reel strips, pay values, or payline patterns and re-run the simulator to instantly see how your changes affect RTP, hit frequency, and volatility.

> This is an educational model. It is not based on any proprietary game and is not a certified gambling device.

---

## Quick Start

```
cd Math-package
python simulator.py
```

Default run: **300,000 spins**, seed `42`. Outputs a PAR sheet to the console.

```
python simulator.py --spins 1000000 --seed 123
```

---

## `simulator.py`

Runs a **Monte Carlo simulation** of the slot machine defined by the four JSON files below. Simulates millions of spins and outputs a complete PAR sheet — the same statistical profile real game designers use to certify a slot machine.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `--spins` | optional | Number of spins to simulate | `300000` |
| `--seed` | optional | Random seed for reproducibility | `42` |

### Output

Results are printed to the console as JSON:

| Field | Description |
| --- | --- |
| `rtp` | Return to player (e.g. `0.9041` = 90.41%) |
| `hold` | House edge — complement of RTP |
| `hit_frequency` | Fraction of spins that produce any win |
| `scatter_hit_rate` | Fraction of spins landing 3+ scatters |
| `avg_win_credits` | Average win per spin in credits |
| `stdev_win_credits` | Standard deviation of wins |
| `volatility_index` | Stdev / total bet — measures game volatility |
| `max_win_observed_credits` | Largest single win seen in the simulation |

---

## PAR Sheet — Default Configuration

The included `par_sheet.md` shows a completed run with 600,000 spins:

| Metric | Value |
| --- | --- |
| RTP | **90.41%** |
| Hold | **9.59%** |
| Hit frequency | **31.69%** |
| Scatter hit rate (3+) | **4.18%** |
| Volatility index | **4.232** |
| Max win observed | **2,232 credits** |

---

## JSON Configuration Files

Edit these files to customize your machine. The simulator loads all four automatically.

---

### `config.json` — Game Setup

Defines the **grid dimensions, symbol roster, and betting structure**.

```json
{
  "grid": { "reels": 5, "rows": 3 },
  "paylines_count": 20,
  "symbols": {
    "regular": ["A", "K", "Q", "J", "T", "9"],
    "wild": "W",
    "scatter": "S"
  },
  "betting": {
    "line_bet_credits": 1,
    "lines": 20,
    "total_bet_credits": 20
  }
}
```

| Field | Description |
| --- | --- |
| `grid.reels` | Number of reels (columns) |
| `grid.rows` | Number of visible rows |
| `paylines_count` | Number of active paylines |
| `symbols.regular` | Symbol codes for standard paying symbols |
| `symbols.wild` | Wild symbol — substitutes for any regular symbol on a payline |
| `symbols.scatter` | Scatter symbol — pays anywhere on the grid |
| `betting.line_bet_credits` | Bet per line in credits |
| `betting.lines` | Number of lines played |
| `betting.total_bet_credits` | Total bet per spin (`line_bet × lines`) |

---

### `paytable.json` — Pay Values

Defines **how much each symbol pays** for 3-, 4-, and 5-of-a-kind combinations. Scatter pays are expressed as **multiples of the total bet**.

```json
{
  "A": { "3": 9,  "4": 30, "5": 120 },
  "K": { "3": 7,  "4": 24, "5": 99  },
  "Q": { "3": 6,  "4": 21, "5": 82  },
  "J": { "3": 5,  "4": 17, "5": 69  },
  "T": { "3": 4,  "4": 14, "5": 56  },
  "9": { "3": 3,  "4": 10, "5": 47  },
  "S": { "3": 3,  "4": 17, "5": 86  }
}
```

**Line pays** (A–9): credits paid per winning line (e.g. five-of-a-kind A pays 120 credits).

**Scatter pays** (S): multiples of total bet (e.g. 5 scatters pays 86× the total bet of 20 = 1,720 credits).

Wild (`W`) substitutes for any regular symbol but has no pay entry of its own.

---

### `reel_strips.json` — Virtual Reels

Defines the **symbol sequence on each of the 5 reels**. Each spin randomly selects a stop position; the three visible symbols are read from that stop and the two positions that follow it.

```json
{
  "reels": [
    ["A","A","A","K","K","K","Q","Q","Q","J","J","J",
     "T","T","T","9","9","9","W","W","S","S", ...],
    ...
  ],
  "length": 50
}
```

| Field | Description |
| --- | --- |
| `reels` | Array of 5 reel strips, each an ordered list of symbol codes |
| `length` | Number of stops per reel (all reels are 50 stops) |

**Customization tip:** Symbol frequency on the reel strip directly controls hit probability. Adding more `A` stops makes `A` land more often; more `W` stops increases wild frequency. Increasing `S` count raises scatter hit rate and thus RTP from scatter pays.

**Default reel composition (per reel, 50 stops):**

| Symbol | Stops | Frequency |
| --- | --- | --- |
| A | ~7 | ~14% |
| K | ~7 | ~14% |
| Q | ~6 | ~12% |
| J | ~6 | ~12% |
| T | ~6 | ~12% |
| 9 | ~6 | ~12% |
| W (Wild) | 2 | 4% |
| S (Scatter) | 2 | 4% |

`reel_strips_horizontal.json` contains the same data in a compact single-line-per-reel format.

---

### `paylines.json` — Payline Patterns

Defines the **20 payline paths** across the 5×3 grid. Each payline is an array of 5 row indices (one per reel), tracing the path left to right.

Row indexing: `0 = top row`, `1 = middle row`, `2 = bottom row`

```json
{
  "paylines": [
    [1, 1, 1, 1, 1],   ← middle row straight across
    [0, 0, 0, 0, 0],   ← top row straight across
    [2, 2, 2, 2, 2],   ← bottom row straight across
    [0, 1, 2, 1, 0],   ← V-shape
    [2, 1, 0, 1, 2],   ← inverted V
    ...
  ]
}
```

The first three lines are the three straight horizontal rows. The remaining 17 are zigzag and diagonal patterns. `paylines_horizontal.json` contains the identical data in a more compact format.

---

## Notes

- No bonus rounds, free spins, or progressive jackpots are implemented — this keeps the math fully transparent and easy to follow.
- Wild does not pay on its own; it only substitutes on paylines.
- Scatter pays anywhere on the 5×3 grid regardless of paylines.
- Results vary slightly between runs unless you fix `--seed`.
