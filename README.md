# Jackpot Hunters

### Companion Repository for

## *The Jackpot Hunter's Guide to Slot Machines*

### A Data-Driven Field Guide

This repository contains the **Python analysis scripts, datasets, and generated outputs** used in the book:

> **The Jackpot Hunter's Guide to Slot Machines — A Data-Driven Field Guide**

The purpose of this repository is to provide readers with **reproducible analysis tools** that explore public casino data, including slot machine hold percentages, jackpot distributions, denomination performance, and regional comparisons.

The scripts allow readers to **replicate the statistical analysis used in the book**, explore new datasets, and develop their own insights into slot machine behavior.

------

# Repository Structure

```
Jackpot-Hunters/
│
├─ python/
│   Python analysis scripts used throughout the book
│
├─ out/
│   Generated output files produced by the scripts
│
├─ data/   (optional depending on repo)
│   Raw or intermediate datasets
│
└─ README.md
```

### Key directories

| Directory   | Description                                             |
| ----------- | ------------------------------------------------------- |
| **python/** | All analysis scripts referenced in the book             |
| **out/**    | Script outputs including tables, summaries, and reports |
| **data/**   | Raw or intermediate datasets used by the scripts        |

------

# Purpose of the Repository

This repository supports the **data-driven approach described in the book** by allowing readers to:

• Analyze **public gaming reports**
 • Compare **casino regions and machine performance**
 • Examine **slot machine hold percentages**
 • Identify **statistical patterns relevant to jackpot hunting**

The scripts transform raw regulatory data into **interpretable metrics for players and researchers**.

------

# Requirements

The scripts require Python 3.9+ and several common data-analysis libraries.

Install dependencies:

```
pip install pandas numpy matplotlib
```

Some scripts may additionally require:

```
pip install seaborn tabulate
```

------

# Running the Scripts

All scripts are located in the **`python/` directory**.

Example:

```
cd python
python NV_overview.py
```

Outputs will be written to the **`out/` directory**.

------

# Python Script Documentation

Below is a summary of the analysis tools included in the repository.

------

# Nevada Analysis Scripts

These scripts analyze **Nevada Gaming Control Board slot data**.

------

## `NV_overview.py`

### Purpose

Provides a **statewide overview of slot machine performance** across Nevada.

### What it analyzes

• Total slot win percentage
 • Revenue distribution
 • Regional comparisons

### Output

The script produces:

• Statewide hold percentages
 • Regional breakdown summaries
 • Aggregated statistics tables

Outputs are saved to:

```
out/nevada/
```

### Run

```
python NV_overview.py
```

------

## `NV_win_pct_location_annual.py`

### Purpose

Compares **slot hold percentages across major Nevada regions**.

The script focuses on:

• Las Vegas Strip
 • Reno
 • Other Nevada markets

### What it produces

• Month-by-month Win% comparisons
 • Strip vs Reno performance differences
 • Denomination-level hold variations

### Example Output

```
Las Vegas Strip average hold: X%
Reno average hold: Y%
Delta: Z%
```

### Run

```
python NV_win_pct_location_annual.py
```

Outputs are written to:

```
out/nevada/location/
```

------

## `NV_win_pct_casino_size.py`

### Purpose

Tests whether **casino size correlates with slot hold percentage**.

Casinos are grouped by revenue tiers to determine if larger properties operate with different hold strategies.

### What the script examines

• Small casino properties
 • Mid-tier casinos
 • Major resort casinos

### Output

The script produces:

• Win% comparisons by property size
 • Regional size-tier breakdowns
 • Comparative statistics tables

Results are written to:

```
out/nevada/casino_size/
```

### Run

```
python NV_win_pct_casino_size.py
```

------

# New Jersey Analysis Scripts

These scripts analyze **New Jersey Division of Gaming Enforcement jackpot data**.

------

## `NJ_jackpots_by_casino.py`

### Purpose

Analyzes jackpot frequency across **Atlantic City casinos**.

### Metrics produced

• Total jackpots by casino
 • Average jackpot size
 • Jackpot frequency distribution

### Output

Tables ranking casinos by jackpot activity.

### Run

```
python NJ_jackpots_by_casino.py
```

Outputs:

```
out/new_jersey/
```

------

## `NJ_jackpot_distribution.py`

### Purpose

Analyzes the **distribution of jackpot sizes**.

### Output

• Jackpot size histograms
 • Frequency tables
 • Distribution analysis

### Run

```
python NJ_jackpot_distribution.py
```

------

# Understanding the Outputs

The scripts generate **structured text summaries and tables** intended to help readers interpret casino statistics.

Key concepts explored include:

• **Hold percentage (Win%)**
 • **Regional differences in slot performance**
 • **Denomination behavior**
 • **Jackpot frequency distributions**

These outputs provide empirical insight into how casinos configure and operate slot machines.

------

# Educational Purpose

This repository is provided for **educational and analytical purposes**.

The scripts demonstrate how public gaming data can be transformed into statistical insights. They are intended to help readers understand:

• Casino reporting structures
 • Slot machine economics
 • Statistical variance in gambling outcomes

------

# License

This repository is released under the MIT License unless otherwise specified.

------

# Related Book

**The Jackpot Hunter's Guide to Slot Machines — A Data-Driven Field Guide**

This book explains the statistical framework behind the scripts and shows how to interpret the results.

------

# Contributing

Contributions are welcome.

Potential improvements include:

• Additional state datasets
 • Improved visualization tools
 • Extended statistical analysis