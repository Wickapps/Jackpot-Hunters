# New Jersey Analysis Scripts

Python scripts that parse **New Jersey Division of Gaming Enforcement (NJDGE) jackpot PDF reports** to analyze slot machine jackpot activity across Atlantic City casinos.

---

## Data Sources

| Report | URL |
| --- | --- |
| **Atlantic City Jackpot (Year-To-Date)** | https://www.nj.gov/lps/ge/docs/Financials/Jackpot/JACKPOT_PUBLICATION.pdf |
| **Atlantic City Jackpots (Select by Year)** | https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/slot-laboratory-tsb/ |
| **Atlantic City Jackpots (2025)** | https://www.nj.gov/oag/ge/docs/Financials/Jackpot/2025/JACKPOT_PUBLICATION.pdf |

Download the PDF for your target year and pass it as the `input_file` argument. For the three-year stacked comparison script, download three separate annual PDFs.

---

## Scripts

| Script | Description |
| --- | --- |
| `NJ_jackpots_by_casino.py` | Jackpot frequency ranked by casino |
| `NJ_jackpots_by_denom.py` | Jackpot frequency by denomination |
| `NJ_jackpots_by_denom_3yr_stacked.py` | Three-year denomination comparison (stacked bar chart) |
| `NJ_jackpots_by_game.py` | Top jackpot-paying game titles |
| `NJ_jackpots_by_time.py` | Jackpot patterns by day of week and month |

---

## `NJ_jackpots_by_casino.py`

Analyzes **jackpot frequency by casino** — identifying which Atlantic City venues pay out most frequently.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `input_file` | positional | Path to NJ jackpot PDF | *(required)* |
| `--top-n` | optional | Number of top casinos to display separately | `15` |
| `--output-dir` | optional | Output directory for files | `output/` |

### Outputs

| File | Description |
| --- | --- |
| `{base_name}_by_casino.xlsx` | Cleaned jackpot data with casino-level stats |
| `{base_name}_by_casino.png` | Bar chart ranking casinos by jackpot count |
| `{base_name}_by_casino_summary.txt` | Rankings and statistical summary |

### Run

```
python NJ_jackpots_by_casino.py data/NJ_jackpots_2024.pdf
python NJ_jackpots_by_casino.py data/NJ_jackpots_2024.pdf --top-n 10 --output-dir output/
```

---

## `NJ_jackpots_by_denom.py`

Analyzes **jackpot frequency by denomination** — showing which bet sizes produce the most jackpots.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `input_file` | positional | Path to NJ jackpot PDF | *(required)* |
| `--ignore-nan` | flag | Exclude jackpots with no denomination listed | off |
| `--output-dir` | optional | Output directory for files | `output/` |

### Outputs

| File | Description |
| --- | --- |
| `{base_name}_by_denom.xlsx` | Cleaned jackpot data by denomination |
| `{base_name}_by_denom.png` | Bar chart by denomination |
| `{base_name}_by_denom_summary.txt` | Summary statistics |

### Run

```
python NJ_jackpots_by_denom.py data/NJ_jackpots_2024.pdf
python NJ_jackpots_by_denom.py data/NJ_jackpots_2024.pdf --ignore-nan
```

---

## `NJ_jackpots_by_denom_3yr_stacked.py`

Compares **denomination trends across three years** using stacked bar charts — reveals shifts in jackpot mix over time.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `file_2023` | positional | Path to 2023 NJ jackpot PDF | *(required)* |
| `file_2024` | positional | Path to 2024 NJ jackpot PDF | *(required)* |
| `file_2025` | positional | Path to 2025 NJ jackpot PDF | *(required)* |
| `--ignore-nan` | flag | Exclude jackpots with no denomination listed | off |
| `--output-dir` | optional | Output directory for files | `output/` |

### Outputs

| File | Description |
| --- | --- |
| `NJ_jackpots_2023-2025_combined.xlsx` | Combined data across all three years |
| `NJ_jackpots_2023-2025_stacked.png` | Stacked bar chart by denomination and year |
| `NJ_jackpots_2023-2025_summary.txt` | Multi-year summary |

### Run

```
python NJ_jackpots_by_denom_3yr_stacked.py data/NJ_2023.pdf data/NJ_2024.pdf data/NJ_2025.pdf
python NJ_jackpots_by_denom_3yr_stacked.py data/NJ_2023.pdf data/NJ_2024.pdf data/NJ_2025.pdf --ignore-nan
```

---

## `NJ_jackpots_by_game.py`

Identifies **which specific slot game titles hit jackpots most frequently** in Atlantic City (land-based only).

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `input_file` | positional | Path to NJ jackpot PDF | *(required)* |
| `--top-n` | optional | Number of top game titles to display | `30` |
| `--output-dir` | optional | Output directory for files | `output/` |

### Outputs

| File | Description |
| --- | --- |
| `{base_name}_by_game.xlsx` | Cleaned land-based jackpot data by game title |
| `{base_name}_by_game.png` | Horizontal bar chart of top games |
| `{base_name}_by_game_summary.txt` | Summary with manufacturer diversity analysis |

### Run

```
python NJ_jackpots_by_game.py data/NJ_jackpots_2024.pdf
python NJ_jackpots_by_game.py data/NJ_jackpots_2024.pdf --top-n 20
```

---

## `NJ_jackpots_by_time.py`

Analyzes **jackpot patterns by time** — day of week, month, and week — for land-based Atlantic City casinos.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `input_file` | positional | Path to NJ jackpot PDF | *(required)* |
| `--output-dir` | optional | Output directory for files | `output/` |

### Outputs

| File | Description |
| --- | --- |
| `{base_name}_by_time.xlsx` | Jackpot data with parsed time components |
| `{base_name}_by_time.png` | Bar chart of jackpot frequency by day of week |
| `{base_name}_by_time_summary.txt` | Day/month/week pattern analysis |

### Run

```
python NJ_jackpots_by_time.py data/NJ_jackpots_2024.pdf
python NJ_jackpots_by_time.py data/NJ_jackpots_2024.pdf --output-dir output/
```
