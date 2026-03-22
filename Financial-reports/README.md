# Financial Reports

**SEC Filing Downloader and Jackpot Disclosure Scanner**

This directory contains a two-script pipeline for downloading and scanning public casino operator SEC filings for jackpot-related disclosures. The scan output is then fed into an AI model to generate an analyst-style report — as described in the book.

```
Step 1: download_filings.py   →   sec-edgar-filings/
Step 2: scan_filings.py       →   scan_results.txt
Step 3: Feed scan_results.txt into an AI model to generate a report
```

The included `scan_findings_summary.md` shows a completed example of the AI-generated report from this pipeline.

---

## Requirements

```
pip install sec-edgar-downloader beautifulsoup4 lxml
```

Or install from the included requirements file:

```
pip install -r requirements.txt
```

---

## Step 1 — `download_filings.py`

Downloads **SEC 10-K and 10-Q filings** for pre-configured casino operators directly from the EDGAR database. Filings are saved locally for offline scanning.

### Pre-configured operators

| Ticker | Company |
| --- | --- |
| `MGM` | MGM Resorts International |
| `CZR` | Caesars Entertainment |
| `PENN` | Penn Entertainment |

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `--operators` | optional | One or more operator tickers to download | all three (`MGM CZR PENN`) |
| `--after` | optional | Only download filings after this date (`YYYY-MM-DD`) | `2023-01-01` |
| `--dir` | optional | Local directory to save filings into | script directory |

### Output

Filings are saved to:

```
sec-edgar-filings/{TICKER}/{FORM}/{ACCESSION}/full-submission.txt
```

### Run

```
python download_filings.py
python download_filings.py --operators MGM CZR
python download_filings.py --operators PENN --after 2024-01-01
python download_filings.py --operators MGM --after 2024-01-01 --dir ./filings
```

---

## Step 2 — `scan_filings.py`

Scans the downloaded filings **offline** for jackpot-related keywords and dollar amounts. Extracts a context window around each match and prints a structured report ready to be fed into an AI model.

### Built-in keywords

The scanner searches for these phrases by default (case-insensitive):

| Keyword |
| --- |
| `progressive jackpot liability` |
| `progressive jackpot` |
| `jackpot liability` |
| `accrued jackpot` |
| `accrued progressive` |
| `progressive liability` |
| `jackpot win` |
| `large payout` |
| `significant payout` |
| `hold percentage` |
| `gaming win` |
| `slot revenue` |

The scanner also automatically extracts any **dollar amounts** found within 300 characters of each match (e.g. `$47.6 million`, `$1,234,567`).

### Arguments

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `--dir` | optional | Directory containing downloaded filings | `sec-edgar-filings/` |
| `--keywords` | optional | Additional keywords to search for (appended to the built-in list) | none |
| `--list-keywords` | flag | Print the built-in keyword list and exit | off |

### Output

Results are printed to stdout. Redirect to a file to capture for AI analysis:

```
python scan_filings.py > scan_results.txt
```

Each match is printed with:
- Operator ticker, form type, and filing accession number
- The matched keyword phrase
- 300 characters of surrounding context
- Any dollar amounts found in that context window

A summary at the end shows total filings scanned, total matches, and dollar amounts found per operator.

### Run

```
python scan_filings.py
python scan_filings.py --dir ./filings
python scan_filings.py --keywords "jackpot reserve" "slot handle"
python scan_filings.py --list-keywords
python scan_filings.py > scan_results.txt
```

---

## Step 3 — AI Analysis

Once `scan_results.txt` is generated, feed it into an AI model (such as Claude or ChatGPT) with a prompt asking it to:

- Identify which operators disclose progressive jackpot liabilities and at what dollar levels
- Extract and compare hold percentages across operators and business segments
- Summarize trends in jackpot pool growth over time
- Flag language around large payouts and their business impact

The book provides example prompts and walks through how to interpret the output.

---

## Example Report — `scan_findings_summary.md`

The included `scan_findings_summary.md` shows a completed AI-generated report from a March 2026 scan covering **39 filings** (MGM, CZR, PENN — January 2023 onward).

### Summary at a Glance

| Operator | Filings | Matches | Jackpot Liability Disclosed | Dollar Range |
| --- | ---: | ---: | --- | --- |
| **PENN** | 13 | 232 | Yes — dedicated balance sheet line item | $47.6M – $79.1M |
| **CZR** | 13 | 61 | Policy mention only | None |
| **MGM** | 13 | 37 | No disclosure | None |

### Key Finding — Penn's Progressive Jackpot Liability

Penn Entertainment is the only operator reporting a specific **Accrued Progressive Jackpot Liability** as a separate balance sheet line item, tracked via its own XBRL tag. The liability grew **66% over four years**:

| Period | Jackpot Liability | YoY Change |
| --- | ---: | ---: |
| Dec 31, 2021 | $47.6M | — |
| Dec 31, 2022 | $51.4M | +8.0% |
| Dec 31, 2023 | $60.8M | +18.3% |
| Dec 31, 2024 | $69.3M | +14.0% |
| Dec 31, 2025 | $79.1M | +14.1% |

See `scan_findings_summary.md` for the full report including hold percentage comparisons and keyword match distributions across all three operators.
