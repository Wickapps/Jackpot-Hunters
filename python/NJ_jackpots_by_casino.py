"""
NJ Jackpot Analysis by Casino - "Where to Hunt"

Processes New Jersey slot machine jackpot PDF data and creates analysis
by casino showing which venues pay out most frequently.

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NJ_jackpots_by_casino.py <input_pdf> [--top-n N] [--output-dir DIR]
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
parser = argparse.ArgumentParser(description='Process NJ slot machine jackpot PDF data by casino')
parser.add_argument('input_file', help='Path to input PDF file')
parser.add_argument('--top-n', type=int, default=15,
                    help='Number of top casinos to display separately (default: 15)')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for files (default: output/)')

args = parser.parse_args()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

# Parse input filename and generate output filenames
input_path = args.input_file
TOP_N_CASINOS = args.top_n
output_dir = args.output_dir
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

# Get base filename
base_name = os.path.splitext(os.path.basename(input_path))[0]

# Generate output filenames based on input
fn_input = os.path.basename(input_path)
fn_out = f"{base_name}_by_casino.xlsx"
fn_chart = f"{base_name}_by_casino.png"
fn_summary = f"{base_name}_by_casino_summary.txt"

tprint("=" * 60)
tprint("NJ JACKPOT ANALYSIS BY CASINO - WHERE TO HUNT")
tprint("=" * 60)
tprint(f"Input file: {input_path}")
tprint(f"Output directory: {output_dir}")
tprint(f"Output Excel: {output_dir}{fn_out}")
tprint(f"Output chart: {output_dir}{fn_chart}")
tprint(f"Output summary: {output_dir}{fn_summary}")
tprint(f"Top N casinos to display: {TOP_N_CASINOS}")
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
# FIX SPLIT CASINO NAMES
# ────────────────────────────────────────────────
# Sometimes tabula splits long casino names across columns
# Detect when Casino is suspiciously short and Amount doesn't look numeric

def looks_like_amount(v):
    """Check if a value looks like a monetary amount"""
    if pd.isna(v):
        return False
    v_str = str(v).strip()
    # Ignore "nan" string
    if v_str.lower() == 'nan':
        return False
    # Check if it starts with $ or is numeric
    if v_str.startswith('$'):
        return True
    # Try to convert to float - if successful, it's likely an amount
    try:
        float(v_str.replace(',', ''))
        return True
    except ValueError:
        return False

tprint("\nFixing split casino names...")
rows_fixed = 0
for idx, row in combined.iterrows():
    casino = str(row['Casino']).strip()
    amount = row['Amount']
    amount_str = str(amount).strip() if pd.notna(amount) else ''

    # Detect truncated casino names by multiple patterns:
    # 1. Very short names (1-3 chars) - but not "nan"
    # 2. Ends with incomplete domain (.CO instead of .COM)
    # 3. Ends with incomplete words (FANDUE, SUNCASIN, ONLINECASINO without .COM)
    # 4. Single letter followed by .COM

    is_truncated = False

    if casino.lower() == 'nan':
        # Skip entries that are just "nan" - these are data errors
        continue
    elif len(casino) <= 2 and casino != 'M':
        is_truncated = True
    elif casino == 'M' and not looks_like_amount(amount):
        is_truncated = True
    elif casino.endswith('.CO') and not casino.endswith('.COM'):
        is_truncated = True
    elif casino.endswith('FANDUE') or casino.endswith('SPORTSBOOK.FANDUE'):
        is_truncated = True
    elif casino.endswith('CASINO') and not casino.endswith('CASINO.COM') and not ' ' in casino:
        is_truncated = True
    elif casino.endswith('ONLINECASINO') and not casino.endswith('.COM'):
        is_truncated = True
    elif casino.endswith('SUNCASIN'):
        is_truncated = True
    elif len(casino) == 5 and casino.endswith('.COM'):
        # Single letter + .COM like "L.COM" or "O.COM"
        is_truncated = True

    if is_truncated and not looks_like_amount(amount):
        # Only merge if amount doesn't look numeric
        if amount_str.lower() != 'nan':  # Don't append "nan" strings
            # Merge Casino and Amount columns
            combined.at[idx, 'Casino'] = f"{casino}{amount_str}"
            # Shift remaining columns left
            combined.at[idx, 'Amount'] = row['Denomination']
            combined.at[idx, 'Denomination'] = row['Manufacturer']
            combined.at[idx, 'Manufacturer'] = row['Description']
            combined.at[idx, 'Description'] = np.nan
            rows_fixed += 1

tprint(f"Fixed {rows_fixed} rows with split casino names")

# Remove rows with obviously invalid casino names that couldn't be fixed
before_filter = len(combined)
combined = combined[
    ~(combined['Casino'].str.lower().str.contains('nan', na=False)) &  # Contains "nan"
    ~(combined['Casino'].str.len() < 3) &  # Too short
    ~(combined['Casino'].str.match(r'^[^A-Z0-9]+$', na=False))  # Only punctuation
]
rows_removed = before_filter - len(combined)
if rows_removed > 0:
    tprint(f"Removed {rows_removed} rows with invalid casino names")

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
# ONLINE FLAG
# ────────────────────────────────────────────────
combined['Online'] = combined['Casino'].str.contains(r'\.com', case=False, na=False).astype(int)

# ────────────────────────────────────────────────
# CASINO ANALYSIS
# ────────────────────────────────────────────────

# Get casino counts
casino_counts = combined['Casino'].value_counts()

# Separate online and land-based
online_casinos = combined[combined['Online'] == 1]['Casino'].value_counts()
land_casinos = combined[combined['Online'] == 0]['Casino'].value_counts()

# Get top N casinos for visualization
top_casinos = casino_counts.head(TOP_N_CASINOS)
top_casino_names = top_casinos.index.tolist()

# Calculate stats for top casinos
casino_stats = []
for casino in top_casino_names:
    casino_data = combined[combined['Casino'] == casino]
    stats = {
        'Casino': casino,
        'Count': len(casino_data),
        'Total_Amount': casino_data['Amount'].sum(),
        'Avg_Amount': casino_data['Amount'].mean(),
        'Median_Amount': casino_data['Amount'].median(),
        'Max_Amount': casino_data['Amount'].max(),
        'Online': casino_data['Online'].iloc[0] if len(casino_data) > 0 else 0
    }
    casino_stats.append(stats)

stats_df = pd.DataFrame(casino_stats)

# Filter out casinos with NaN averages (bad data from truncated names)
stats_df = stats_df[stats_df['Avg_Amount'].notna()]

# Fix known truncation patterns in casino names
def fix_casino_name(name):
    """Fix common truncation patterns in casino names"""
    # Fix incomplete .CO -> .COM
    if name.endswith('.CO') and not name.endswith('.COM'):
        name = name + 'M'
    # Fix FANDUE -> FANDUEL
    if 'FANDUE' in name and 'FANDUEL' not in name:
        name = name.replace('FANDUE', 'FANDUEL')
    # Fix missing .COM at end
    if name.startswith('WWW.') and not name.endswith('.COM') and not name.endswith('.BET'):
        if name.endswith('CASINO') or name.endswith('SUNCASIN'):
            name = name + '.COM'
    # Fix SUNCASIN -> SUNCASINO
    if 'SUNCASIN' in name:
        name = name.replace('SUNCASIN', 'SUNCASINO')
    return name

stats_df['Casino'] = stats_df['Casino'].apply(fix_casino_name)

# Now consolidate duplicates that may have been created by fixing names
consolidated_stats = []
for casino in stats_df['Casino'].unique():
    casino_rows = stats_df[stats_df['Casino'] == casino]
    if len(casino_rows) > 1:
        # Merge duplicate entries
        merged = {
            'Casino': casino,
            'Count': casino_rows['Count'].sum(),
            'Total_Amount': casino_rows['Total_Amount'].sum(),
            'Avg_Amount': casino_rows['Total_Amount'].sum() / casino_rows['Count'].sum(),
            'Median_Amount': casino_rows['Median_Amount'].median(),
            'Max_Amount': casino_rows['Max_Amount'].max(),
            'Online': casino_rows['Online'].iloc[0]
        }
        consolidated_stats.append(merged)
    else:
        consolidated_stats.append(casino_rows.iloc[0].to_dict())

stats_df = pd.DataFrame(consolidated_stats)
stats_df = stats_df.sort_values('Count', ascending=False).head(TOP_N_CASINOS)
stats_df = stats_df.reset_index(drop=True)
top_casino_names = stats_df['Casino'].tolist()

# Recalculate top_casinos counts to match the filtered list
top_casinos = pd.Series([stats_df.loc[i, 'Count'] for i in range(len(stats_df))],
                        index=top_casino_names)

# ────────────────────────────────────────────────
# BASIC INFO
# ────────────────────────────────────────────────
tprint(f"\nTable Rows={len(combined)}, Columns={len(combined.columns)}")

# Save cleaned data with casino stats
combined.to_excel(output_dir + fn_out, index=False)
tprint(f"Saved Excel to: {output_dir}{fn_out}")

# ────────────────────────────────────────────────
# SUMMARY STATS
# ────────────────────────────────────────────────
summary_lines = []

summary_lines.append("=" * 80)
summary_lines.append("NEW JERSEY JACKPOT ANALYSIS - WHERE TO HUNT")
summary_lines.append("=" * 80)
summary_lines.append(f"\nInput file: {fn_input}")
summary_lines.append(f"Top N casinos displayed: {TOP_N_CASINOS}")
summary_lines.append("\n" + "-" * 80)
summary_lines.append("BASIC STATISTICS")
summary_lines.append("-" * 80)
summary_lines.append(f"Start date:       {combined['Date'].min()}")
summary_lines.append(f"End date:         {combined['Date'].max()}")
summary_lines.append(f"Total jackpots:   {len(combined)}")

over_1m = (combined['Amount'] > 1_000_000).sum()
summary_lines.append(f"Jackpots > $1M:   {over_1m} ({over_1m/len(combined):.2%})")

total = combined['Amount'].sum()
summary_lines.append(f"Total amount:     ${total:,.2f}")
summary_lines.append(f"Average:          ${total/len(combined):,.2f}")

online_count = combined['Online'].sum()
land_count = len(combined) - online_count
summary_lines.append(f"\nOnline jackpots:  {online_count} ({online_count/len(combined):.2%})")
summary_lines.append(f"Land-based:       {land_count} ({land_count/len(combined):.2%})")

summary_lines.append(f"\nTotal unique casinos: {combined['Casino'].nunique()}")
summary_lines.append(f"Online casinos:       {len(online_casinos)}")
summary_lines.append(f"Land-based casinos:   {len(land_casinos)}")

# Top casinos with detailed stats
summary_lines.append("\n" + "-" * 80)
summary_lines.append(f"TOP {TOP_N_CASINOS} CASINOS BY JACKPOT COUNT")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Rank':<5} {'Casino':<35} {'Count':>7} {'Avg $':>12} {'Total $':>15}")
summary_lines.append("-" * 80)

for i, row in stats_df.iterrows():
    casino_name = row['Casino'][:33]  # Truncate long names
    online_flag = " 🌐" if row['Online'] == 1 else ""
    summary_lines.append(
        f"{i+1:<5} {casino_name:<35} {row['Count']:>7,} "
        f"${row['Avg_Amount']:>11,.0f} ${row['Total_Amount']:>14,.0f}{online_flag}"
    )

# Top manufacturers at these casinos
summary_lines.append("\n" + "-" * 80)
summary_lines.append("TOP 10 MANUFACTURERS (ALL CASINOS)")
summary_lines.append("-" * 80)
top_mfr = combined['Manufacturer'].value_counts().head(10)
for mfr, count in top_mfr.items():
    summary_lines.append(f"{mfr:40s} {count:5,d}")

# Top games - online
summary_lines.append("\n" + "-" * 80)
summary_lines.append("TOP 10 GAMES (ONLINE CASINOS)")
summary_lines.append("-" * 80)
top_online = combined[combined['Online']==1]['Description'].value_counts().head(10)
for game, count in top_online.items():
    summary_lines.append(f"{game:50s} {count:5,d}")

# Top games - land-based
summary_lines.append("\n" + "-" * 80)
summary_lines.append("TOP 10 GAMES (LAND-BASED CASINOS)")
summary_lines.append("-" * 80)
top_land = combined[combined['Online']==0]['Description'].value_counts().head(10)
for game, count in top_land.items():
    summary_lines.append(f"{game:50s} {count:5,d}")

# Online vs Land-based comparison
summary_lines.append("\n" + "-" * 80)
summary_lines.append("ONLINE VS LAND-BASED COMPARISON")
summary_lines.append("-" * 80)
online_data = combined[combined['Online'] == 1]
land_data = combined[combined['Online'] == 0]

summary_lines.append(f"{'Metric':<30} {'Online':>15} {'Land-Based':>15}")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Total Jackpots':<30} {len(online_data):>15,} {len(land_data):>15,}")
summary_lines.append(f"{'Total Amount':<30} ${online_data['Amount'].sum():>14,.0f} ${land_data['Amount'].sum():>14,.0f}")
summary_lines.append(f"{'Average Amount':<30} ${online_data['Amount'].mean():>14,.0f} ${land_data['Amount'].mean():>14,.0f}")
summary_lines.append(f"{'Median Amount':<30} ${online_data['Amount'].median():>14,.0f} ${land_data['Amount'].median():>14,.0f}")
summary_lines.append(f"{'Max Jackpot':<30} ${online_data['Amount'].max():>14,.0f} ${land_data['Amount'].max():>14,.0f}")

summary_lines.append("\n" + "=" * 80)

# Print summary
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# ────────────────────────────────────────────────
# BAR CHART – Casino Jackpot Counts
# ────────────────────────────────────────────────

facecolor  = '#EAEAEA'
text1      = '#252525'
text2      = '#004C74'

# Colors for online vs land-based
color_online = '#E63946'  # Red for online
color_land = '#457B9D'    # Blue for land-based

fig, ax = plt.subplots(figsize=(16, 9), facecolor=facecolor)
ax.set_facecolor(facecolor)

# Create bar chart with colors based on online/land-based
x_pos = np.arange(len(top_casino_names))
colors = [color_online if stats_df.iloc[i]['Online'] == 1 else color_land
          for i in range(len(top_casino_names))]

bars = ax.bar(x_pos, top_casinos.values, color=colors, edgecolor='black', linewidth=0.8)

# Add count labels on top of bars
for i, (casino, count) in enumerate(zip(top_casino_names, top_casinos.values)):
    ax.text(i, count, f"{int(count):,}", ha='center', va='bottom',
            fontsize=9, color=text2, fontweight='bold')

# Set x-axis labels (truncate long casino names)
truncated_names = [name[:25] + '...' if len(name) > 25 else name for name in top_casino_names]
ax.set_xticks(x_pos)
ax.set_xticklabels(truncated_names, fontsize=10, color=text1, rotation=45, ha='right')

plt.xlabel('Casino', fontsize=13, color=text1, fontweight='bold')
plt.ylabel('Number of Jackpots', fontsize=13, color=text1, fontweight='bold')
plt.title(f'New Jersey Jackpots by Casino - Top {TOP_N_CASINOS}',
          fontsize=16, color='#234234', pad=15, fontweight='bold')

# Add legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=color_online, edgecolor='black', label='Online'),
                   Patch(facecolor=color_land, edgecolor='black', label='Land-Based')]
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
