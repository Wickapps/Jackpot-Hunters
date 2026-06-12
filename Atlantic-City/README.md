# Atlantic City Analysis Scripts

Python scripts that parse **New Jersey Office of the Attorney General annual slot and table game revenue reports** to analyze hold percentages across Atlantic City casinos by denomination.

---

## Data Sources

| Report | URL |
| --- | --- |
| **Atlantic City Casino Industry Slot Win Data — 2024** | https://www.nj.gov/oag/ge/docs/Financials/AnnualSlotTableGameData/2024.pdf |
| **Atlantic City Casino Industry Slot Win Data — 2023** | https://www.nj.gov/oag/ge/docs/Financials/AnnualSlotTableGameData/2023.pdf |
| **Atlantic City Casino Industry Slot Win Data — 2022** | https://www.nj.gov/oag/ge/docs/Financials/AnnualSlotTableGameData/2022.pdf |

Download the annual PDF for your target year and pass it as the `input_file` argument. New years follow the same URL pattern — replace the year in the path.

> **Data availability (checked June 2026):** The latest annual report published by the state is **2024**. Calendar-year **2025 data is not yet available** — it is not present on the DGE [Annual Slot and Table Game Data](https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/financial-and-statistical-information/annual-slot-and-table-game-data/) index, and the predictable `…/AnnualSlotTableGameData/2025.pdf` URL returns HTTP 404. The annual report is released well after year-end, so 2025 should appear at the same location/pattern in a later release. Until then, the Atlantic City scripts can only be validated against the 2024 (or earlier) reports.

---

## Scripts

| Script | Description |
| --- | --- |
| `AC_hold_percentage.py` | Hold percentage by casino and denomination — identifies the loosest machines |

---

## `AC_hold_percentage.py`

Analyzes **Atlantic City casino hold percentages by denomination** from the NJ annual slot/table game revenue report. Identifies which casinos run the loosest machines across each denomination.

> **Lower Win% = Lower hold = More player-friendly = "Looser" slots**

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `input_file` | positional | Path to AC annual data PDF | *(required)* |
| `--output-dir` | optional | Output directory for files | `output/` |

### Outputs

| File | Description |
| --- | --- |
| `{base_name}_hold_analysis.xlsx` | Casino-by-denomination hold percentage data |
| `{base_name}_hold_heatmap.png` | Heatmap of hold% across all casinos and denominations |
| `{base_name}_hold_rankings.png` | Bar chart ranking casinos by overall hold percentage |
| `{base_name}_hold_summary.txt` | Rankings and key insights |

### Run

```
python AC_hold_percentage.py data/AC_annual_2024.pdf
python AC_hold_percentage.py data/AC_annual_2024.pdf --output-dir output/
```
