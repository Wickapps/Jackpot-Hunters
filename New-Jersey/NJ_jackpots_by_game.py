"""
NJ Jackpot Analysis by Game Title - "What Game to Play"

Processes New Jersey slot machine jackpot PDF data and creates analysis
by game title showing which specific machines hit most frequently (land-based only).

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NJ_jackpots_by_game.py <input_pdf> [--top-n N] [--output-dir DIR]
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
parser = argparse.ArgumentParser(description='Process NJ slot machine jackpot PDF data by game title (land-based only)')
parser.add_argument('input_file', help='Path to input PDF file')
parser.add_argument('--top-n', type=int, default=30,
                    help='Number of top games to display (default: 30)')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for files (default: output/)')

args = parser.parse_args()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

# Parse input filename and generate output filenames
input_path = args.input_file
TOP_N_GAMES = args.top_n
output_dir = args.output_dir
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

# Get base filename
base_name = os.path.splitext(os.path.basename(input_path))[0]

# Generate output filenames based on input
fn_input = os.path.basename(input_path)
fn_out = f"{base_name}_by_game.xlsx"
fn_chart = f"{base_name}_by_game.png"
fn_summary = f"{base_name}_by_game_summary.txt"

tprint("=" * 60)
tprint("NJ JACKPOT ANALYSIS BY GAME - WHAT TO PLAY")
tprint("=" * 60)
tprint(f"Input file: {input_path}")
tprint(f"Output directory: {output_dir}")
tprint(f"Output Excel: {output_dir}{fn_out}")
tprint(f"Output chart: {output_dir}{fn_chart}")
tprint(f"Output summary: {output_dir}{fn_summary}")
tprint(f"Top N games to display: {TOP_N_GAMES}")
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
# GAME ANALYSIS
# ────────────────────────────────────────────────

# Get game counts
game_counts = combined['Description'].value_counts().head(TOP_N_GAMES)
top_game_names = game_counts.index.tolist()

# Calculate stats for top games
game_stats = []
for game in top_game_names:
    game_data = combined[combined['Description'] == game]
    stats = {
        'Game': game,
        'Count': len(game_data),
        'Total_Amount': game_data['Amount'].sum(),
        'Avg_Amount': game_data['Amount'].mean(),
        'Median_Amount': game_data['Amount'].median(),
        'Max_Amount': game_data['Amount'].max(),
        'Manufacturer': game_data['Manufacturer'].mode()[0] if len(game_data['Manufacturer'].mode()) > 0 else 'Unknown'
    }
    game_stats.append(stats)

stats_df = pd.DataFrame(game_stats)

# Get manufacturer breakdown
manufacturer_counts = combined['Manufacturer'].value_counts()

# ────────────────────────────────────────────────
# BASIC INFO
# ────────────────────────────────────────────────
tprint(f"\nTable Rows={len(combined)}, Columns={len(combined.columns)}")

# Save cleaned data with game stats
combined.to_excel(output_dir + fn_out, index=False)
tprint(f"Saved Excel to: {output_dir}{fn_out}")

# ────────────────────────────────────────────────
# SUMMARY STATS
# ────────────────────────────────────────────────
summary_lines = []

summary_lines.append("=" * 80)
summary_lines.append("NEW JERSEY JACKPOT ANALYSIS - WHAT GAME TO PLAY (LAND-BASED)")
summary_lines.append("=" * 80)
summary_lines.append(f"\nInput file: {fn_input}")
summary_lines.append("\n" + "-" * 80)
summary_lines.append("BASIC STATISTICS")
summary_lines.append("-" * 80)
summary_lines.append(f"Total land-based jackpots: {len(combined)}")

over_1m = (combined['Amount'] > 1_000_000).sum()
summary_lines.append(f"Jackpots > $1M:            {over_1m} ({over_1m/len(combined):.2%})")

total = combined['Amount'].sum()
summary_lines.append(f"Total amount:              ${total:,.2f}")
summary_lines.append(f"Average jackpot:           ${total/len(combined):,.2f}")

summary_lines.append(f"\nTotal unique games:        {combined['Description'].nunique()}")
summary_lines.append(f"Total manufacturers:       {combined['Manufacturer'].nunique()}")

# Top manufacturers
summary_lines.append("\n" + "-" * 80)
summary_lines.append("TOP 10 MANUFACTURERS")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Manufacturer':<35} {'Count':>10} {'Percentage':>12}")
summary_lines.append("-" * 80)
for mfr, count in manufacturer_counts.head(10).items():
    pct = count / len(combined)
    summary_lines.append(f"{mfr:<35} {count:>10,} {pct:>11.1%}")

# Top games with detailed stats
summary_lines.append("\n" + "-" * 80)
summary_lines.append(f"TOP {TOP_N_GAMES} GAMES BY JACKPOT COUNT")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Rank':<5} {'Game':<40} {'Count':>8} {'Avg $':>12} {'Manufacturer':<20}")
summary_lines.append("-" * 80)

for i, row in stats_df.iterrows():
    game_name = row['Game'][:38] if len(row['Game']) > 38 else row['Game']
    mfr = row['Manufacturer'][:18] if len(str(row['Manufacturer'])) > 18 else row['Manufacturer']
    summary_lines.append(
        f"{i+1:<5} {game_name:<40} {row['Count']:>8,} "
        f"${row['Avg_Amount']:>11,.0f} {mfr:<20}"
    )

# Game diversity analysis
summary_lines.append("\n" + "-" * 80)
summary_lines.append("GAME DIVERSITY ANALYSIS")
summary_lines.append("-" * 80)

top_10_pct = game_counts.head(10).sum() / len(combined)
top_20_pct = game_counts.head(20).sum() / len(combined)
top_30_pct = game_counts.head(30).sum() / len(combined)

summary_lines.append(f"Top 10 games account for:  {top_10_pct:>5.1%} of jackpots")
summary_lines.append(f"Top 20 games account for:  {top_20_pct:>5.1%} of jackpots")
summary_lines.append(f"Top 30 games account for:  {top_30_pct:>5.1%} of jackpots")

summary_lines.append("\n" + "=" * 80)

# Print summary
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# ────────────────────────────────────────────────
# BAR CHART – Top Games
# ────────────────────────────────────────────────

facecolor  = '#EAEAEA'
bar_color  = '#2A9D8F'  # Teal color for games
text1      = '#252525'
text2      = '#004C74'

fig, ax = plt.subplots(figsize=(14, 10), facecolor=facecolor)
ax.set_facecolor(facecolor)

# Create horizontal bar chart (better for long game names)
y_pos = np.arange(len(top_game_names))
bars = ax.barh(y_pos, game_counts.values, color=bar_color, edgecolor='black', linewidth=0.5)

# Add count labels at end of bars
for i, (game, count) in enumerate(zip(top_game_names, game_counts.values)):
    if count > 0:
        ax.text(count, i, f" {int(count):,}", ha='left', va='center',
                fontsize=9, color=text2, fontweight='bold')

# Truncate long game names for display
display_names = [name[:35] + '...' if len(name) > 35 else name for name in top_game_names]

# Set y-axis labels
ax.set_yticks(y_pos)
ax.set_yticklabels(display_names, fontsize=9, color=text1)

# Invert y-axis so #1 is at top
ax.invert_yaxis()

plt.xlabel('Number of Jackpots', fontsize=12, color=text1, fontweight='bold')
plt.ylabel('Game Title', fontsize=12, color=text1, fontweight='bold')
plt.title(f'New Jersey Land-Based Casino Jackpots - Top {TOP_N_GAMES} Games',
          fontsize=14, color='#234234', pad=15, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors=text1)

plt.tight_layout()
plt.savefig(output_dir + fn_chart, facecolor=facecolor, dpi=150, bbox_inches='tight')
tprint(f"\nBar chart saved to: {output_dir}{fn_chart}")
plt.close()

tprint("\n" + "=" * 80)
tprint("PROCESSING COMPLETE!")
tprint("=" * 80)

# Save all output to file
with open(output_dir + fn_summary, 'w') as f:
    f.write('\n'.join(all_output))
tprint(f"\n✓ Full output saved to: {output_dir}{fn_summary}")
