"""
NJ Jackpot Analysis by Denomination

Processes New Jersey slot machine jackpot PDF data and creates analysis
by denomination with visualizations.

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NJ_jackpots_by_denom.py <input_pdf> [--ignore-nan] [--output-dir DIR]
"""

import tabula
import pandas as pd
import logging
import matplotlib.pyplot as plt
import numpy as np
import argparse
import os
from pypdf import PdfReader

# Suppress noisy warnings
logging.getLogger('tabula').setLevel(logging.ERROR)

pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', 10)

# ────────────────────────────────────────────────
# OUTPUT CAPTURE
# ────────────────────────────────────────────────
all_output = []  # Store all output for saving to file

def tprint(*args, **kwargs):
    """Print to console and capture output"""
    msg = ' '.join(str(arg) for arg in args)
    print(msg, **kwargs)
    all_output.append(msg)

# ────────────────────────────────────────────────
# COMMAND LINE ARGUMENTS
# ────────────────────────────────────────────────
parser = argparse.ArgumentParser(description='Process NJ slot machine jackpot PDF data by denomination')
parser.add_argument('input_file', help='Path to input PDF file')
parser.add_argument('--ignore-nan', action='store_true',
                    help='Exclude jackpots without denomination')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for files (default: output/)')

args = parser.parse_args()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

# https://www.nj.gov/lps/ge/docs/Financials/Jackpot/JACKPOT_PUBLICATION.pdf
# https://www.nj.gov/oag/ge/docs/Financials/AnnualSlotTableGameData/2024.pdf
# https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/slot-laboratory-tsb/

# Parse input filename and generate output filenames
input_path = args.input_file
IGNORE_NAN_DENOMINATIONS = args.ignore_nan
output_dir = args.output_dir
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

# Get base filename
base_name = os.path.splitext(os.path.basename(input_path))[0]

# Generate output filenames based on input
fn_input = os.path.basename(input_path)
fn_out = f"{base_name}_by_denom.xlsx"
fn_histo = f"{base_name}_by_denom.png"
fn_summary = f"{base_name}_by_denom_summary.txt"

tprint("=" * 60)
tprint("NJ JACKPOT ANALYSIS BY DENOMINATION")
tprint("=" * 60)
tprint(f"Input file: {input_path}")
tprint(f"Output directory: {output_dir}")
tprint(f"Output Excel: {output_dir}{fn_out}")
tprint(f"Output chart: {output_dir}{fn_histo}")
tprint(f"Output summary: {output_dir}{fn_summary}")
tprint(f"Ignore NaN denominations: {IGNORE_NAN_DENOMINATIONS}")
tprint("=" * 60 + "\n")

tprint("Using tabula-py with stream mode for large PDF")

# Detect actual page count
try:
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    tprint(f"Detected {total_pages} pages in PDF\n")
except Exception as e:
    tprint(f"Warning: Could not detect page count, defaulting to 182 pages. Error: {e}\n")
    total_pages = 182

all_tables = []
batch_size = 30

for start in range(1, total_pages + 1, batch_size):
    end = min(start + batch_size - 1, total_pages)
    tprint(f"Processing pages {start}-{end}...", end=' ')
    try:
        batch = tabula.read_pdf(
            input_path,
            pages=f"{start}-{end}",
            stream=True,                 # Use stream mode for tables without borders
            guess=True,                  # Allow guessing column boundaries
            pandas_options={'header': 0},
            multiple_tables=True,
            java_options=["-Xmx6g"],
            silent=True
        )
        all_tables.extend(batch)
        tprint(f"✓ ({len(batch)} tables)")
    except Exception as e:
        tprint(f"✗ Error: {str(e)[:100]}")

tprint(f"\nTotal tables extracted: {len(all_tables)}")

if not all_tables:
    tprint("No tables found at all.")
    exit()

# Remove summary table (usually first one)
if 'Summary' in str(all_tables[0].to_string()) or all_tables[0].shape[0] < 5:
    all_tables.pop(0)
    tprint("Removed summary table")

clean_tables = []
for df in all_tables:
    # Remove fully empty rows/columns
    df = df.dropna(how='all').dropna(axis=1, how='all')

    # If more than 6 columns (common with lattice on whitespace)
    if df.shape[1] > 6:
        # Drop any fully empty or near-empty left/right columns
        df = df.loc[:, df.notna().any()]
        if df.shape[1] > 6:
            df = df.iloc[:, :6]  # force truncate

    # If less than 6, skip or log
    if df.shape[1] != 6:
        continue

    # Assign columns
    df.columns = ['Date', 'Casino', 'Amount', 'Denomination', 'Manufacturer', 'Description']

    # Strip whitespace from all cells
    df = df.map(lambda x: str(x).strip() if pd.notna(x) else x)

    clean_tables.append(df)

if not clean_tables:
    tprint("No valid 6-column tables after normalization. PDF layout incompatible with tabula defaults.")
    exit()

combined = pd.concat(clean_tables, ignore_index=True)
tprint(f"\nCombined rows before cleanup: {len(combined)}")

# ────────────────────────────────────────────────
# CLEAN AMOUNT → numeric
# ────────────────────────────────────────────────
def clean_amount(v):
    if pd.isna(v):
        return np.nan
    v = str(v).strip().replace('$', '').replace(',', '')
    try:
        return float(v)
    except (ValueError, TypeError):
        return np.nan

combined['Amount'] = combined['Amount'].apply(clean_amount)
combined['Amount'] = pd.to_numeric(combined['Amount'], errors='coerce')

# ────────────────────────────────────────────────
# CLEAN DENOMINATION → numeric
# ────────────────────────────────────────────────
def clean_denom(v):
    if pd.isna(v):
        return np.nan
    v = str(v).strip().replace('$', '').replace(',', '').replace('¢', '0.01').upper()
    if v in ['', '-', 'N/A', 'VARIOUS', 'VAR', 'N\\A']:
        return np.nan
    # Handle common patterns like "0.25", "1", "5", "25", "100", "0.01"
    try:
        return float(v)
    except (ValueError, TypeError):
        # rare cases — keep as string for now (will become NaN later)
        return np.nan

combined['Denomination'] = combined['Denomination'].apply(clean_denom)
combined['Denomination'] = pd.to_numeric(combined['Denomination'], errors='coerce')

# ────────────────────────────────────────────────
# ONLINE FLAG
# ────────────────────────────────────────────────
combined['Online'] = combined['Casino'].str.contains(r'\.com', case=False, na=False).astype(int)

# ────────────────────────────────────────────────
# FILTER NaN DENOMINATIONS (if enabled)
# ────────────────────────────────────────────────
if IGNORE_NAN_DENOMINATIONS:
    original_count = len(combined)
    combined = combined[combined['Denomination'].notna()]
    filtered_count = original_count - len(combined)
    tprint(f"Filtered out {filtered_count} jackpots without denomination")
    tprint(f"Remaining jackpots: {len(combined)}")

# ────────────────────────────────────────────────
# BASIC INFO
# ────────────────────────────────────────────────
tprint(f"\nTable Rows={len(combined)}, Columns={len(combined.columns)}")

# Save cleaned data
combined.to_excel(output_dir + fn_out, index=False)
tprint(f"Saved Excel to: {output_dir}{fn_out}")

# ────────────────────────────────────────────────
# SUMMARY STATS
# ────────────────────────────────────────────────
summary_lines = []

summary_lines.append("=" * 60)
summary_lines.append("NEW JERSEY JACKPOT ANALYSIS SUMMARY")
summary_lines.append("=" * 60)
summary_lines.append(f"\nInput file: {fn_input}")
summary_lines.append(f"Filter NaN denominations: {IGNORE_NAN_DENOMINATIONS}")
summary_lines.append("\n" + "-" * 60)
summary_lines.append("BASIC STATISTICS")
summary_lines.append("-" * 60)
summary_lines.append(f"Start date:      {combined['Date'].min()}")
summary_lines.append(f"End date:        {combined['Date'].max()}")
summary_lines.append(f"Total jackpots:  {len(combined)}")

over_1m = (combined['Amount'] > 1_000_000).sum()
summary_lines.append(f"Jackpots > $1M:  {over_1m} ({over_1m/len(combined):.2%})")

total = combined['Amount'].sum()
summary_lines.append(f"Total amount:    ${total:,.2f}")
summary_lines.append(f"Average:         ${total/len(combined):,.2f}")

online_count = combined['Online'].sum()
summary_lines.append(f"Online jackpots: {online_count} ({online_count/len(combined):.2%})")

# Top manufacturers
summary_lines.append("\n" + "-" * 60)
summary_lines.append("TOP 10 MANUFACTURERS")
summary_lines.append("-" * 60)
top_mfr = combined['Manufacturer'].value_counts().head(10)
for mfr, count in top_mfr.items():
    summary_lines.append(f"{mfr:30s} {count:5d}")

# Top games – online / in-person
summary_lines.append("\n" + "-" * 60)
summary_lines.append("TOP 10 GAMES (ONLINE)")
summary_lines.append("-" * 60)
top_online = combined[combined['Online']==1]['Description'].value_counts().head(10)
for game, count in top_online.items():
    summary_lines.append(f"{game:40s} {count:5d}")

summary_lines.append("\n" + "-" * 60)
summary_lines.append("TOP 10 GAMES (LAND-BASED)")
summary_lines.append("-" * 60)
top_land = combined[combined['Online']==0]['Description'].value_counts().head(10)
for game, count in top_land.items():
    summary_lines.append(f"{game:40s} {count:5d}")

# ────────────────────────────────────────────────
# BAR CHART – Denomination (discrete buckets)
# ────────────────────────────────────────────────
def categorize_denomination(value):
    """Map denomination values to discrete buckets"""
    if pd.isna(value):
        return 'NaN'

    # Define exact denomination buckets
    if value == 0.01:
        return '$0.01'
    elif value == 0.05:
        return '$0.05'
    elif value == 0.25:
        return '$0.25'
    elif value == 1.0:
        return '$1'
    elif value == 5.0:
        return '$5'
    elif value == 10.0:
        return '$10'
    elif value == 20.0:
        return '$20'
    elif value == 100.0:
        return '$100'
    else:
        # Any other value (e.g., 2, 25, 50, 500, etc.) goes to Multi
        return 'Multi'

# Create denomination categories
combined['Denom_Category'] = combined['Denomination'].apply(categorize_denomination)

# Count jackpots per category
denom_counts = combined['Denom_Category'].value_counts()

# Define the order of categories (conditionally include NaN)
if IGNORE_NAN_DENOMINATIONS:
    category_order = ['$0.01', '$0.05', '$0.25', '$1', '$5', '$10', '$20', '$100', 'Multi']
else:
    category_order = ['$0.01', '$0.05', '$0.25', '$1', '$5', '$10', '$20', '$100', 'Multi', 'NaN']

# Reindex to ensure all categories appear in order (fill missing with 0)
denom_counts = denom_counts.reindex(category_order, fill_value=0)

# Add denomination breakdown to summary
summary_lines.append("\n" + "-" * 60)
summary_lines.append("JACKPOTS BY DENOMINATION")
summary_lines.append("-" * 60)
for category, count in denom_counts.items():
    pct = (count / len(combined) * 100) if len(combined) > 0 else 0
    summary_lines.append(f"{category:10s} {count:5d}  ({pct:5.2f}%)")

summary_lines.append("\n" + "=" * 60)

# Print summary
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# Plot
facecolor  = '#EAEAEA'
bar_color  = '#3475D0'
text1      = '#252525'
text2      = '#004C74'

fig, ax = plt.subplots(figsize=(12, 7), facecolor=facecolor)
ax.set_facecolor(facecolor)

# Create bar chart
x_pos = np.arange(len(category_order))
bars = ax.bar(x_pos, denom_counts.values, color=bar_color, edgecolor='black', linewidth=0.8)

# Add count labels on top of bars
for i, (category, count) in enumerate(zip(category_order, denom_counts.values)):
    if count > 0:
        ax.text(i, count, f"{int(count)}", ha='center', va='bottom',
                fontsize=10, color=text2, fontweight='bold')

# Set x-axis labels
ax.set_xticks(x_pos)
ax.set_xticklabels(category_order, fontsize=11, color=text1)

plt.xlabel('Denomination', fontsize=13, color=text1, fontweight='bold')
plt.ylabel('Number of Jackpots', fontsize=13, color=text1, fontweight='bold')
title_suffix = ' (Excluding Unknown)' if IGNORE_NAN_DENOMINATIONS else ''
plt.title(f'New Jersey Jackpots by Denomination{title_suffix}', fontsize=16, color='#234234', pad=15, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors=text1)

plt.tight_layout()
plt.savefig(output_dir + fn_histo, facecolor=facecolor, dpi=150)
tprint(f"\nBar chart saved to: {output_dir}{fn_histo}")
plt.close()  # Close the figure without displaying

tprint("\n" + "=" * 60)
tprint("PROCESSING COMPLETE!")
tprint("=" * 60)

# Save all output to file
with open(output_dir + fn_summary, 'w') as f:
    f.write('\n'.join(all_output))
tprint(f"\n✓ Full output saved to: {output_dir}{fn_summary}")
