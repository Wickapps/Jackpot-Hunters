# Nevada Analysis Scripts

Python scripts that parse **Nevada Gaming Control Board (NGCB) monthly PDF reports** to extract slot machine win percentages by denomination, location, and casino size tier.

---

## Data Source

All scripts in this directory use the **Nevada Gaming Control Board Gaming Revenue Reports**.

| Report | URL |
| --- | --- |
| **Nevada Gaming Board Monthly Reports** | https://www.gaming.nv.gov/about-us/gaming-revenue-information-gri/ |

Navigate to the link above and select a month/year from the list to download the PDF. Pass the downloaded PDF as the `input_file` argument, or place a full year of PDFs in a directory for the multi-month scripts.

---

## Scripts

| Script | Description |
| --- | --- |
| `NV_overview.py` | Statewide summary from a single monthly report |
| `NV_win_pct_location_annual.py` | Annual win% trends by denomination for a given location |
| `NV_win_pct_vegas_reno.py` | Side-by-side Strip vs Reno comparison |
| `NV_casino_size.py` | Win% by casino revenue size tier for a given location |

---

## `NV_overview.py`

Parses a single Nevada Gaming monthly PDF and produces a statewide summary — slot win percentages by denomination and a regional breakdown.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `input_file` | positional | Path to Nevada Gaming monthly PDF | *(required)* |
| `--output-dir` | optional | Output directory for reports | `output/` |

### Outputs

| File | Description |
| --- | --- |
| `{base_name}_overview.txt` | Statewide metrics, slot win% by denomination, regional breakdown |

### Run

```
python NV_overview.py docs/NV_2025_01.pdf
python NV_overview.py docs/NV_2025_01.pdf --output-dir output/
```

---

## `NV_win_pct_location_annual.py`

Iterates through **12 months** of Nevada Gaming monthly PDFs for a given year and location, extracting slot win percentages by denomination and charting annual trends.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `year` | positional | Year to analyze (e.g. `2025`) | *(required)* |
| `location` | positional | Location name (e.g. `"Las Vegas Strip"`, `"Reno"`, `"Statewide"`) | *(required)* |
| `--input-dir` | optional | Directory containing NV monthly PDFs | `docs/` |
| `--output-dir` | optional | Output directory for reports | `output/` |
| `--min-units` | optional | Minimum gaming units for a denomination to be included | `30` |

### Outputs

| File | Description |
| --- | --- |
| `NV_{year}_{location}_win_pct.png` | Line chart of monthly win% trends by denomination |
| `NV_{year}_{location}_win_pct.txt` | Monthly and annual statistics with analysis |

### Run

```
python NV_win_pct_location_annual.py 2025 "Las Vegas Strip"
python NV_win_pct_location_annual.py 2025 "Reno" --input-dir docs/ --output-dir output/
```

---

## `NV_win_pct_vegas_reno.py`

Side-by-side comparison of slot machine win percentages between **Las Vegas Strip and Reno** across one or more monthly Nevada Gaming reports.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `pdf_files` | positional (one or more) | NV monthly PDF file(s) to analyze | *(required)* |
| `--output-dir` | optional | Output directory for reports | `output/` |
| `--min-units` | optional | Minimum gaming units for a denomination to be included | `30` |

### Outputs

| File | Description |
| --- | --- |
| `NV_win_pct_vegas_vs_reno.png` | Grouped bar chart (single month) or line chart (multi-month) |
| `NV_win_pct_vegas_vs_reno.txt` | Per-file and multi-month comparison summary |

### Run

```
python NV_win_pct_vegas_reno.py docs/NV_2025_01.pdf
python NV_win_pct_vegas_reno.py docs/NV_2025_*.pdf
python NV_win_pct_vegas_reno.py docs/NV_2025_01.pdf docs/NV_2025_06.pdf --output-dir output/
```

---

## `NV_casino_size.py`

Tests whether **casino size (by revenue tier) correlates with slot hold percentage** for a given Nevada region and year.

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `year` | positional | Year to analyze (e.g. `2025`) | *(required)* |
| `location` | positional | Location name (e.g. `"Las Vegas Strip"`, `"Reno"`) | *(required)* |
| `--input-dir` | optional | Directory containing NV monthly PDFs | `docs/` |
| `--output-dir` | optional | Output directory for reports | `output/` |

### Outputs

| File | Description |
| --- | --- |
| `NV_{year}_{location}_casino_size.png` | Line chart showing annual win% trend by casino revenue tier |
| `NV_{year}_{location}_casino_size.txt` | Monthly data and analysis by size tier |

### Run

```
python NV_casino_size.py 2025 "Las Vegas Strip"
python NV_casino_size.py 2025 "Reno" --input-dir docs/ --output-dir output/
```
