"""
NJ Jackpot Analysis by Time - "When to Hunt"

Processes New Jersey slot machine jackpot PDF data and creates analysis
by time patterns (day of week, month, etc.) for land-based casinos only.

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NJ_jackpots_by_time.py <input_pdf> [--output-dir DIR]
"""

import tabula
import pandas as pd
import logging
import matplotlib.pyplot as plt
import numpy as np
import argparse
import os
from pypdf import PdfReader
from datetime import datetime

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
parser = argparse.ArgumentParser(description='Process NJ slot machine jackpot PDF data by time patterns (land-based only)')
parser.add_argument('input_file', help='Path to input PDF file')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for files (default: output/)')

args = parser.parse_args()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

# Parse input filename and generate output filenames
input_path = args.input_file
output_dir = args.output_dir
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

# Get base filename
base_name = os.path.splitext(os.path.basename(input_path))[0]

# Generate output filenames based on input
fn_input = os.path.basename(input_path)
fn_out = f"{base_name}_by_time.xlsx"
fn_chart = f"{base_name}_by_time.png"
fn_summary = f"{base_name}_by_time_summary.txt"

tprint("=" * 60)
tprint("NJ JACKPOT ANALYSIS BY TIME - WHEN TO HUNT")
tprint("=" * 60)
tprint(f"Input file: {input_path}")
tprint(f"Output directory: {output_dir}")
tprint(f"Output Excel: {output_dir}{fn_out}")
tprint(f"Output chart: {output_dir}{fn_chart}")
tprint(f"Output summary: {output_dir}{fn_summary}")
tprint(f"Filter: LAND-BASED CASINOS ONLY")
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
    try:
        return float(v)
    except (ValueError, TypeError):
        return np.nan

combined['Denomination'] = combined['Denomination'].apply(clean_denom)
combined['Denomination'] = pd.to_numeric(combined['Denomination'], errors='coerce')

# ────────────────────────────────────────────────
# ONLINE FLAG & FILTER TO LAND-BASED ONLY
# ────────────────────────────────────────────────
combined['Online'] = combined['Casino'].str.contains(r'\.com', case=False, na=False).astype(int)

# Filter to land-based casinos only
original_count = len(combined)
combined = combined[combined['Online'] == 0]
tprint(f"\nFiltered to land-based casinos only")
tprint(f"Removed {original_count - len(combined)} online jackpots")
tprint(f"Remaining land-based jackpots: {len(combined)}")

# ────────────────────────────────────────────────
# PARSE DATES AND EXTRACT TIME COMPONENTS
# ────────────────────────────────────────────────
tprint("\nParsing dates...")

def parse_date(date_str):
    """Parse date strings to datetime objects"""
    if pd.isna(date_str):
        return pd.NaT
    date_str = str(date_str).strip()

    # Try common date formats
    for fmt in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%m-%d-%Y']:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue

    # Try pandas generic parser as fallback
    try:
        return pd.to_datetime(date_str)
    except:
        return pd.NaT

combined['Date_Parsed'] = combined['Date'].apply(parse_date)

# Remove rows with unparseable dates
before_date_filter = len(combined)
combined = combined[combined['Date_Parsed'].notna()]
date_failures = before_date_filter - len(combined)
if date_failures > 0:
    tprint(f"Removed {date_failures} rows with unparseable dates")

# Extract time components
combined['DayOfWeek'] = combined['Date_Parsed'].dt.dayofweek  # 0=Monday, 6=Sunday
combined['DayName'] = combined['Date_Parsed'].dt.day_name()
combined['Month'] = combined['Date_Parsed'].dt.month
combined['MonthName'] = combined['Date_Parsed'].dt.month_name()
combined['DayOfMonth'] = combined['Date_Parsed'].dt.day
combined['Year'] = combined['Date_Parsed'].dt.year
combined['Quarter'] = combined['Date_Parsed'].dt.quarter

# Categorize day of month
def categorize_day_of_month(day):
    if day <= 7:
        return 'Week 1 (1-7)'
    elif day <= 14:
        return 'Week 2 (8-14)'
    elif day <= 21:
        return 'Week 3 (15-21)'
    else:
        return 'Week 4+ (22-31)'

combined['WeekOfMonth'] = combined['DayOfMonth'].apply(categorize_day_of_month)

# Weekend flag
combined['IsWeekend'] = combined['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday=5, Sunday=6

tprint(f"Successfully parsed {len(combined)} dates")

# ────────────────────────────────────────────────
# BASIC INFO
# ────────────────────────────────────────────────
tprint(f"\nTable Rows={len(combined)}, Columns={len(combined.columns)}")

# Save cleaned data
combined.to_excel(output_dir + fn_out, index=False)
tprint(f"Saved Excel to: {output_dir}{fn_out}")

# ────────────────────────────────────────────────
# TIME PATTERN ANALYSIS
# ────────────────────────────────────────────────

# Day of week analysis
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
dow_counts = combined['DayName'].value_counts().reindex(day_order, fill_value=0)
dow_avg_amount = combined.groupby('DayName')['Amount'].mean().reindex(day_order)
dow_total_amount = combined.groupby('DayName')['Amount'].sum().reindex(day_order)

# Month analysis
month_order = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
month_counts = combined['MonthName'].value_counts().reindex(month_order, fill_value=0)
month_avg_amount = combined.groupby('MonthName')['Amount'].mean().reindex(month_order)

# Week of month analysis
week_order = ['Week 1 (1-7)', 'Week 2 (8-14)', 'Week 3 (15-21)', 'Week 4+ (22-31)']
week_counts = combined['WeekOfMonth'].value_counts().reindex(week_order, fill_value=0)
week_avg_amount = combined.groupby('WeekOfMonth')['Amount'].mean().reindex(week_order)

# Weekend vs Weekday
weekend_data = combined[combined['IsWeekend'] == 1]
weekday_data = combined[combined['IsWeekend'] == 0]

# ────────────────────────────────────────────────
# SUMMARY STATS
# ────────────────────────────────────────────────
summary_lines = []

summary_lines.append("=" * 80)
summary_lines.append("NEW JERSEY JACKPOT ANALYSIS - WHEN TO HUNT (LAND-BASED ONLY)")
summary_lines.append("=" * 80)
summary_lines.append(f"\nInput file: {fn_input}")
summary_lines.append(f"Date range: {combined['Date_Parsed'].min().strftime('%Y-%m-%d')} to {combined['Date_Parsed'].max().strftime('%Y-%m-%d')}")
summary_lines.append("\n" + "-" * 80)
summary_lines.append("BASIC STATISTICS")
summary_lines.append("-" * 80)
summary_lines.append(f"Total land-based jackpots: {len(combined)}")

over_1m = (combined['Amount'] > 1_000_000).sum()
summary_lines.append(f"Jackpots > $1M:            {over_1m} ({over_1m/len(combined):.2%})")

total = combined['Amount'].sum()
summary_lines.append(f"Total amount:              ${total:,.2f}")
summary_lines.append(f"Average jackpot:           ${total/len(combined):,.2f}")

# Weekend vs Weekday comparison
summary_lines.append("\n" + "-" * 80)
summary_lines.append("WEEKEND VS WEEKDAY")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Metric':<35} {'Weekend':>20} {'Weekday':>20}")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Total Jackpots':<35} {len(weekend_data):>20,} {len(weekday_data):>20,}")
summary_lines.append(f"{'Percentage':<35} {len(weekend_data)/len(combined):>19.1%} {len(weekday_data)/len(combined):>19.1%}")
summary_lines.append(f"{'Average Amount':<35} ${weekend_data['Amount'].mean():>19,.0f} ${weekday_data['Amount'].mean():>19,.0f}")
summary_lines.append(f"{'Total Amount':<35} ${weekend_data['Amount'].sum():>19,.0f} ${weekday_data['Amount'].sum():>19,.0f}")

# Best and worst days
summary_lines.append("\n" + "-" * 80)
summary_lines.append("JACKPOTS BY DAY OF WEEK")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Day':<15} {'Count':>10} {'Avg Amount':>15} {'Total Amount':>18}")
summary_lines.append("-" * 80)
for day in day_order:
    count = dow_counts[day]
    avg = dow_avg_amount[day]
    total_day = dow_total_amount[day]
    pct = (count / len(combined)) if len(combined) > 0 else 0
    summary_lines.append(f"{day:<15} {count:>10,} ({pct:>5.1%}) ${avg:>12,.0f} ${total_day:>15,.0f}")

best_day = dow_counts.idxmax()
worst_day = dow_counts.idxmin()
summary_lines.append(f"\nBest day:  {best_day} ({dow_counts[best_day]} jackpots)")
summary_lines.append(f"Worst day: {worst_day} ({dow_counts[worst_day]} jackpots)")

# Month analysis
summary_lines.append("\n" + "-" * 80)
summary_lines.append("JACKPOTS BY MONTH")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Month':<15} {'Count':>10} {'Avg Amount':>15}")
summary_lines.append("-" * 80)
for month in month_order:
    count = month_counts[month]
    avg = month_avg_amount[month]
    pct = (count / len(combined)) if len(combined) > 0 and count > 0 else 0
    summary_lines.append(f"{month:<15} {count:>10,} ({pct:>5.1%}) ${avg:>12,.0f}")

best_month = month_counts.idxmax()
worst_month = month_counts.idxmin()
summary_lines.append(f"\nBest month:  {best_month} ({month_counts[best_month]} jackpots)")
summary_lines.append(f"Worst month: {worst_month} ({month_counts[worst_month]} jackpots)")

# Week of month
summary_lines.append("\n" + "-" * 80)
summary_lines.append("JACKPOTS BY WEEK OF MONTH (Payday Effect?)")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Week':<20} {'Count':>10} {'Avg Amount':>15}")
summary_lines.append("-" * 80)
for week in week_order:
    count = week_counts[week]
    avg = week_avg_amount[week]
    pct = (count / len(combined)) if len(combined) > 0 else 0
    summary_lines.append(f"{week:<20} {count:>10,} ({pct:>5.1%}) ${avg:>12,.0f}")

summary_lines.append("\n" + "=" * 80)

# Print summary
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# ────────────────────────────────────────────────
# BAR CHART – Day of Week
# ────────────────────────────────────────────────

facecolor  = '#EAEAEA'
text1      = '#252525'
text2      = '#004C74'

# Colors: weekdays in blue, weekends in orange
colors = ['#457B9D', '#457B9D', '#457B9D', '#457B9D', '#457B9D', '#E76F51', '#E76F51']

fig, ax = plt.subplots(figsize=(14, 8), facecolor=facecolor)
ax.set_facecolor(facecolor)

# Create bar chart
x_pos = np.arange(len(day_order))
bars = ax.bar(x_pos, dow_counts.values, color=colors, edgecolor='black', linewidth=0.8)

# Add count labels on top of bars
for i, (day, count) in enumerate(zip(day_order, dow_counts.values)):
    if count > 0:
        ax.text(i, count, f"{int(count):,}", ha='center', va='bottom',
                fontsize=11, color=text2, fontweight='bold')

# Set x-axis labels
ax.set_xticks(x_pos)
ax.set_xticklabels(day_order, fontsize=12, color=text1, rotation=0)

plt.xlabel('Day of Week', fontsize=14, color=text1, fontweight='bold')
plt.ylabel('Number of Jackpots', fontsize=14, color=text1, fontweight='bold')
plt.title('New Jersey Land-Based Casino Jackpots by Day of Week',
          fontsize=16, color='#234234', pad=15, fontweight='bold')

# Add legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor='#457B9D', edgecolor='black', label='Weekday'),
                   Patch(facecolor='#E76F51', edgecolor='black', label='Weekend')]
ax.legend(handles=legend_elements, loc='upper right', frameon=True, fancybox=True, shadow=True)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors=text1)

plt.tight_layout()
plt.savefig(output_dir + fn_chart, facecolor=facecolor, dpi=150)
tprint(f"\nBar chart saved to: {output_dir}{fn_chart}")
plt.close()

tprint("\n" + "=" * 80)
tprint("PROCESSING COMPLETE!")
tprint("=" * 80)

# Save all output to file
with open(output_dir + fn_summary, 'w') as f:
    f.write('\n'.join(all_output))
tprint(f"\n✓ Full output saved to: {output_dir}{fn_summary}")
