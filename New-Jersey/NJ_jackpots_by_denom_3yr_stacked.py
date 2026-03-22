"""
NJ Jackpot Analysis - 3 Year Stacked Comparison by Denomination

Processes three years of New Jersey slot machine jackpot PDF data and creates
stacked bar chart comparison showing denomination trends across years.

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NJ_jackpots_by_denom_stacked.py <pdf_2023> <pdf_2024> <pdf_2025> [--ignore-nan] [--output-dir DIR]
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
parser = argparse.ArgumentParser(description='Process 3 years of NJ jackpot data and create stacked bar chart')
parser.add_argument('file_2023', help='Path to 2023 PDF file')
parser.add_argument('file_2024', help='Path to 2024 PDF file')
parser.add_argument('file_2025', help='Path to 2025 PDF file')
parser.add_argument('--ignore-nan', action='store_true',
                    help='Exclude jackpots without denomination')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for files (default: output/)')

args = parser.parse_args()

IGNORE_NAN_DENOMINATIONS = args.ignore_nan
output_dir = args.output_dir
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

tprint("=" * 60)
tprint("NJ JACKPOTS BY DENOMINATION - 3 YEAR COMPARISON")
tprint("=" * 60)
tprint(f"2023 file: {args.file_2023}")
tprint(f"2024 file: {args.file_2024}")
tprint(f"2025 file: {args.file_2025}")
tprint(f"Ignore NaN denominations: {IGNORE_NAN_DENOMINATIONS}")
tprint(f"Output directory: {output_dir}")
tprint("=" * 60 + "\n")

# ────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────

def clean_amount(v):
    """Convert amount strings to numeric"""
    if pd.isna(v):
        return np.nan
    v = str(v).strip().replace('$', '').replace(',', '')
    try:
        return float(v)
    except (ValueError, TypeError):
        return np.nan

def clean_denom(v):
    """Convert denomination strings to numeric"""
    if pd.isna(v):
        return np.nan
    v = str(v).strip().replace('$', '').replace(',', '').replace('¢', '0.01').upper()
    if v in ['', '-', 'N/A', 'VARIOUS', 'VAR', 'N\\A']:
        return np.nan
    try:
        return float(v)
    except (ValueError, TypeError):
        return np.nan

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

def process_pdf(file_path, year_label):
    """Process a single PDF file and return cleaned dataframe"""
    tprint(f"\nProcessing {year_label}...")
    tprint(f"File: {file_path}")

    # Detect actual page count
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        tprint(f"  Detected {total_pages} pages in PDF")
    except Exception as e:
        tprint(f"  Warning: Could not detect page count, defaulting to 182 pages. Error: {e}")
        total_pages = 182

    all_tables = []
    batch_size = 30

    for start in range(1, total_pages + 1, batch_size):
        end = min(start + batch_size - 1, total_pages)
        tprint(f"  Pages {start}-{end}...", end=' ')
        try:
            batch = tabula.read_pdf(
                file_path,
                pages=f"{start}-{end}",
                stream=True,
                guess=True,
                pandas_options={'header': 0},
                multiple_tables=True,
                java_options=["-Xmx6g"],
                silent=True
            )
            all_tables.extend(batch)
            tprint(f"✓ ({len(batch)} tables)")
        except Exception as e:
            tprint(f"✗ Error: {str(e)[:100]}")

    tprint(f"  Total tables extracted: {len(all_tables)}")

    if not all_tables:
        tprint(f"  ERROR: No tables found in {year_label}")
        return None

    # Remove summary table if present
    if 'Summary' in str(all_tables[0].to_string()) or all_tables[0].shape[0] < 5:
        all_tables.pop(0)

    # Clean tables
    clean_tables = []
    for df in all_tables:
        df = df.dropna(how='all').dropna(axis=1, how='all')

        if df.shape[1] > 6:
            df = df.loc[:, df.notna().any()]
            if df.shape[1] > 6:
                df = df.iloc[:, :6]

        if df.shape[1] != 6:
            continue

        df.columns = ['Date', 'Casino', 'Amount', 'Denomination', 'Manufacturer', 'Description']
        df = df.map(lambda x: str(x).strip() if pd.notna(x) else x)
        clean_tables.append(df)

    if not clean_tables:
        tprint(f"  ERROR: No valid tables in {year_label}")
        return None

    combined = pd.concat(clean_tables, ignore_index=True)
    tprint(f"  Combined rows: {len(combined)}")

    # Clean data
    combined['Amount'] = combined['Amount'].apply(clean_amount)
    combined['Amount'] = pd.to_numeric(combined['Amount'], errors='coerce')

    combined['Denomination'] = combined['Denomination'].apply(clean_denom)
    combined['Denomination'] = pd.to_numeric(combined['Denomination'], errors='coerce')

    combined['Online'] = combined['Casino'].str.contains(r'\.com', case=False, na=False).astype(int)

    # Filter NaN if requested
    if IGNORE_NAN_DENOMINATIONS:
        original_count = len(combined)
        combined = combined[combined['Denomination'].notna()]
        tprint(f"  Filtered out {original_count - len(combined)} jackpots without denomination")
        tprint(f"  Remaining: {len(combined)}")

    # Add year column
    combined['Year'] = year_label

    return combined

# ────────────────────────────────────────────────
# PROCESS ALL THREE YEARS
# ────────────────────────────────────────────────

df_2023 = process_pdf(args.file_2023, "2023")
df_2024 = process_pdf(args.file_2024, "2024")
df_2025 = process_pdf(args.file_2025, "2025")

# Check if all files processed successfully
if df_2023 is None or df_2024 is None or df_2025 is None:
    tprint("\nERROR: Failed to process one or more files. Exiting.")
    exit(1)

# Combine all years
all_data = pd.concat([df_2023, df_2024, df_2025], ignore_index=True)

# Save combined data to Excel
combined_excel = f"{output_dir}NJ_jackpots_2023-2025_combined.xlsx"
all_data.to_excel(combined_excel, index=False)
tprint(f"\n✓ Combined data saved to: {combined_excel}")

# ────────────────────────────────────────────────
# CREATE DENOMINATION CATEGORIES FOR EACH YEAR
# ────────────────────────────────────────────────

# Add denomination categories
for df in [df_2023, df_2024, df_2025]:
    df['Denom_Category'] = df['Denomination'].apply(categorize_denomination)

# Define category order
if IGNORE_NAN_DENOMINATIONS:
    category_order = ['$0.01', '$0.05', '$0.25', '$1', '$5', '$10', '$20', '$100', 'Multi']
else:
    category_order = ['$0.01', '$0.05', '$0.25', '$1', '$5', '$10', '$20', '$100', 'Multi', 'NaN']

# Get counts for each year
counts_2023 = df_2023['Denom_Category'].value_counts().reindex(category_order, fill_value=0)
counts_2024 = df_2024['Denom_Category'].value_counts().reindex(category_order, fill_value=0)
counts_2025 = df_2025['Denom_Category'].value_counts().reindex(category_order, fill_value=0)

# Create summary
summary_lines = []
summary_lines.append("=" * 70)
summary_lines.append("NJ JACKPOTS BY DENOMINATION - 3 YEAR COMPARISON")
summary_lines.append("=" * 70)
summary_lines.append(f"\nFilter NaN denominations: {IGNORE_NAN_DENOMINATIONS}")
summary_lines.append("\n" + "-" * 70)
summary_lines.append("JACKPOT COUNTS BY YEAR AND DENOMINATION")
summary_lines.append("-" * 70)
summary_lines.append(f"{'Category':<12} {'2023':>10} {'2024':>10} {'2025':>10} {'Total':>12}")
summary_lines.append("-" * 70)

for category in category_order:
    c23 = counts_2023[category]
    c24 = counts_2024[category]
    c25 = counts_2025[category]
    total = c23 + c24 + c25
    summary_lines.append(f"{category:<12} {c23:>10} {c24:>10} {c25:>10} {total:>12}")

summary_lines.append("-" * 70)
summary_lines.append(f"{'TOTAL':<12} {len(df_2023):>10} {len(df_2024):>10} {len(df_2025):>10} {len(all_data):>12}")
summary_lines.append("=" * 70)

# Print summary
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# ────────────────────────────────────────────────
# CREATE STACKED BAR CHART
# ────────────────────────────────────────────────

facecolor = '#EAEAEA'
text_color = '#252525'

# Colors for each year
colors_years = ['#2E86AB', '#A23B72', '#F18F01']  # Blue, Purple, Orange for 2023, 2024, 2025

fig, ax = plt.subplots(figsize=(14, 8), facecolor=facecolor)
ax.set_facecolor(facecolor)

years = ['2023', '2024', '2025']
x_pos = np.arange(len(category_order))
width = 0.6

# Create stacked bars - now stacking years for each denomination
bottom = np.zeros(len(category_order))
for i, year in enumerate(years):
    if year == '2023':
        values = [counts_2023[cat] for cat in category_order]
    elif year == '2024':
        values = [counts_2024[cat] for cat in category_order]
    else:  # 2025
        values = [counts_2025[cat] for cat in category_order]

    bars = ax.bar(x_pos, values, width, bottom=bottom, label=year,
                   color=colors_years[i], edgecolor='black', linewidth=0.5)
    bottom += values

# Customize chart
ax.set_xlabel('Denomination', fontsize=14, color=text_color, fontweight='bold')
ax.set_ylabel('Number of Jackpots', fontsize=14, color=text_color, fontweight='bold')
title_suffix = ' (Excluding Unknown)' if IGNORE_NAN_DENOMINATIONS else ''
ax.set_title(f'New Jersey Jackpots by Denomination - 3 Year Comparison{title_suffix}',
             fontsize=16, color='#234234', pad=20, fontweight='bold')

ax.set_xticks(x_pos)
ax.set_xticklabels(category_order, fontsize=12, color=text_color)
ax.tick_params(colors=text_color)

# Add legend
ax.legend(title='Year', loc='upper right', frameon=True, fancybox=True, shadow=True)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()

chart_file = f"{output_dir}NJ_jackpots_2023-2025_stacked.png"
plt.savefig(chart_file, facecolor=facecolor, dpi=150, bbox_inches='tight')
tprint(f"\n✓ Stacked bar chart saved to: {chart_file}")
plt.close()

tprint("\n" + "=" * 70)
tprint("PROCESSING COMPLETE!")
tprint("=" * 70)

# Save all output to file
summary_file = f"{output_dir}NJ_jackpots_2023-2025_summary.txt"
with open(summary_file, 'w') as f:
    f.write('\n'.join(all_output))
tprint(f"\n✓ Full output saved to: {summary_file}")
