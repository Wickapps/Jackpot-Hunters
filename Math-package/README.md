# Educational Transparent Slot Math Package (5×3, 20 lines)

This folder is a **teaching example** that mimics the structure of a slot “math package” in a fully transparent way.

It includes:
- Reel strips (weighted by repetition)
- A 20-payline map
- A paytable (line pays + scatter pays)
- A simulator that estimates RTP, hit frequency, and volatility

## Quick start

```bash
python3 simulator.py --spins 1000000 --seed 123
```

## Notes
- This is **not** a real manufacturer math package.
- No bonus rounds, free spins, progressives, or mystery features are included.
- Wild does not pay on its own (simplifies evaluation).
