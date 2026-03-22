"""
Atlantic City Hold Percentage Analysis - Finding the Loosest Slots

Analyzes AC casino performance data to identify which casinos have the lowest
hold percentages (Win%) by denomination - helping hunters find the loosest machines.

Lower Win% = More player-friendly = "Looser" slots

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python AC_hold_percentage.py <input_pdf> [--output-dir DIR]
"""

# https://www.nj.gov/oag/ge/docs/Financials/AnnualSlotTableGameData/2023.pdf
# https://www.nj.gov/oag/ge/docs/Financials/AnnualSlotTableGameData/2024.pdf


import tabula
import pandas as pd
import logging
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import argparse
import os
from pypdf import PdfReader
import re

# Suppress noisy warnings
logging.getLogger('tabula').setLevel(logging.ERROR)

pd.set_option('display.max_rows', 20)
pd.set_option('display.max_columns', 15)
pd.set_option('display.width', 120)

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
parser = argparse.ArgumentParser(description='Analyze AC casino hold percentages to find loosest slots')
parser.add_argument('input_file', help='Path to input PDF file (AC annual data)')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for files (default: output/)')

args = parser.parse_args()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
input_path = args.input_file
output_dir = args.output_dir
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

# Get base filename
base_name = os.path.splitext(os.path.basename(input_path))[0]

# Generate output filenames
fn_input = os.path.basename(input_path)
fn_out = f"{base_name}_hold_analysis.xlsx"
fn_heatmap = f"{base_name}_hold_heatmap.png"
fn_rankings = f"{base_name}_hold_rankings.png"
fn_summary = f"{base_name}_hold_summary.txt"

tprint("=" * 80)
tprint("ATLANTIC CITY HOLD PERCENTAGE ANALYSIS - FINDING THE LOOSEST SLOTS")
tprint("=" * 80)
tprint(f"Input file: {input_path}")
tprint(f"Output directory: {output_dir}")
tprint(f"Output Excel: {output_dir}{fn_out}")
tprint(f"Output heatmap: {output_dir}{fn_heatmap}")
tprint(f"Output rankings: {output_dir}{fn_rankings}")
tprint(f"Output summary: {output_dir}{fn_summary}")
tprint("=" * 80 + "\n")

# ────────────────────────────────────────────────
# EXTRACT SLOT WIN DATA FROM PDF
# ────────────────────────────────────────────────
tprint("Extracting slot win data from PDF...\n")


def clean_numeric(val):
    """Clean numeric values from PDF extraction"""
    if pd.isna(val) or str(val).strip() in ['', '-', '- -', 'nan', 'NaN']:
        return np.nan
    val_str = str(val).strip().replace(',', '').replace(' ', '').replace('$', '')
    val_str = val_str.replace('(', '-').replace(')', '')
    try:
        return float(val_str)
    except:
        return np.nan


def normalize_denom(name):
    """Normalize denomination name from PDF header"""
    s = re.sub(r'\s*Slot\s+Machines?\s*$', '', name.strip(), flags=re.I).strip()
    if re.search(r'\.01', s):
        return '$0.01'
    if re.search(r'\.05', s):
        return '$0.05'
    if re.search(r'\.25', s):
        return '$0.25'
    if re.search(r'\.50', s):
        return '$0.50'
    if re.search(r'1\.00', s):
        return '$1.00'
    if re.search(r'5\.00', s):
        return '$5.00'
    if re.search(r'25\.00', s):
        return '$25.00'
    if re.search(r'\$?100', s):
        return '$100'
    if re.search(r'[Mm]ulti', s):
        return 'Multi-Denom'
    if re.search(r'[Oo]ther', s):
        return 'Other'
    if re.search(r'[Tt]otal', s):
        return 'Total Slots'
    return s


def parse_table(table):
    """Parse a PDF table to extract casino/denomination/Win% data"""
    results = []

    # Find the row containing "Win %" labels
    win_pct_row_idx = None
    for idx in range(min(5, len(table))):
        row_vals = [str(v).strip() for v in table.iloc[idx]]
        if any(v in ['Win %', 'Win%'] for v in row_vals):
            win_pct_row_idx = idx
            break

    if win_pct_row_idx is None:
        return results

    # Find Win% column indices
    win_pct_cols = []
    for col_idx in range(table.shape[1]):
        val = str(table.iloc[win_pct_row_idx, col_idx]).strip()
        if val in ['Win %', 'Win%']:
            win_pct_cols.append(col_idx)

    if not win_pct_cols:
        return results

    # Find denomination names from header rows above the Win% label row
    denom_entries = []
    for idx in range(win_pct_row_idx):
        for col_idx in range(table.shape[1]):
            val = str(table.iloc[idx, col_idx]).strip()
            if val == 'nan' or len(val) < 3:
                continue
            # Must look like a denomination header
            if 'Slot' in val or 'denominational' in val:
                denom_entries.append((col_idx, normalize_denom(val)))

    # Sort by column position and deduplicate
    denom_entries.sort(key=lambda x: x[0])
    seen = set()
    unique_denoms = []
    for pos, name in denom_entries:
        if name not in seen:
            seen.add(name)
            unique_denoms.append((pos, name))

    # Match denominations to Win% columns (both sorted left-to-right)
    n = min(len(unique_denoms), len(win_pct_cols))
    if n == 0:
        return results
    if len(unique_denoms) != len(win_pct_cols):
        tprint(f"  Warning: {len(unique_denoms)} denominations vs {len(win_pct_cols)} Win% columns, using {n}")
    pairs = list(zip([d[1] for d in unique_denoms[:n]], win_pct_cols[:n]))

    # Find casino data rows (skip headers, totals, blanks)
    skip_names = {'nan', 'NaN', '', 'Casino', 'Totals', 'Total'}

    for row_idx in range(win_pct_row_idx + 1, len(table)):
        raw_name = str(table.iloc[row_idx, 0]).strip()
        if raw_name in skip_names or len(raw_name) < 3:
            continue
        if raw_name.startswith('$'):
            continue

        casino = raw_name
        for denom_name, win_col in pairs:
            val_str = str(table.iloc[row_idx, win_col]).strip()
            if val_str in ['-', '- -', '', 'nan']:
                continue
            val = clean_numeric(table.iloc[row_idx, win_col])
            if pd.notna(val):
                results.append({
                    'Casino': casino,
                    'Denomination': denom_name,
                    'Win_Pct': val
                })

    return results


# Try lattice mode first (works well for 2022/2023 PDFs)
tprint("Trying lattice extraction...")
try:
    tables = tabula.read_pdf(
        input_path, pages='1', lattice=True,
        pandas_options={'header': None}, multiple_tables=True,
        java_options=["-Xmx4g"], silent=True
    )
except Exception as e:
    tprint(f"Lattice extraction failed: {e}")
    tables = []

usable = [t for t in tables if t.shape[0] > 3 and t.shape[1] > 5]
tprint(f"Lattice mode: {len(tables)} tables, {len(usable)} usable")

# If lattice didn't yield enough tables, try stream mode (needed for 2024 PDF)
if len(usable) < 2:
    tprint("Trying stream extraction...")
    try:
        stream_tables = tabula.read_pdf(
            input_path, pages='1', stream=True,
            pandas_options={'header': None}, multiple_tables=True,
            java_options=["-Xmx4g"], silent=True
        )
    except Exception as e:
        tprint(f"Stream extraction failed: {e}")
        stream_tables = []

    stream_usable = [t for t in stream_tables if t.shape[0] > 3 and t.shape[1] > 5]
    tprint(f"Stream mode: {len(stream_tables)} tables, {len(stream_usable)} usable")

    if len(stream_usable) > len(usable):
        usable = stream_usable

if not usable:
    tprint("ERROR: No usable tables found in PDF")
    exit(1)

# Parse all usable tables
all_slot_data = []
for i, table in enumerate(usable):
    tprint(f"\nParsing table {i+1} (shape: {table.shape})...")
    parsed = parse_table(table)
    tprint(f"  Extracted {len(parsed)} data points")
    all_slot_data.extend(parsed)

if not all_slot_data:
    tprint("ERROR: No data could be parsed from the PDF tables")
    exit(1)

tprint(f"\nTotal: {len(all_slot_data)} casino-denomination data points extracted")

df = pd.DataFrame(all_slot_data)
df['Win'] = 0
df['Handle'] = 0

tprint(f"Analyzed {len(df)} casino-denomination combinations")
tprint(f"Casinos: {df['Casino'].nunique()}")
tprint(f"Denominations: {df['Denomination'].nunique()}")

# ────────────────────────────────────────────────
# ANALYSIS: IDENTIFY LOOSEST CASINOS
# ────────────────────────────────────────────────

summary_lines = []

summary_lines.append("=" * 80)
summary_lines.append("ATLANTIC CITY HOLD PERCENTAGE ANALYSIS - LOOSE SLOT FINDER")
summary_lines.append("=" * 80)
summary_lines.append(f"\nInput file: {fn_input}")
summary_lines.append("\nLower Win% = Better for Players = 'Looser' Slots")
summary_lines.append("\n" + "-" * 80)
summary_lines.append("OVERALL CASINO RANKINGS (Average Win% Across All Denominations)")
summary_lines.append("-" * 80)

# Calculate average Win% by casino
casino_avg = df.groupby('Casino')['Win_Pct'].mean().sort_values()

summary_lines.append(f"{'Rank':<6} {'Casino':<25} {'Avg Win%':>10} {'Rating':<15}")
summary_lines.append("-" * 80)

for rank, (casino, avg_win_pct) in enumerate(casino_avg.items(), 1):
    # Rating based on Win%
    if avg_win_pct < 9.0:
        rating = "★★★ Loosest"
    elif avg_win_pct < 9.5:
        rating = "★★ Very Good"
    elif avg_win_pct < 10.0:
        rating = "★ Good"
    else:
        rating = "Average"

    summary_lines.append(f"{rank:<6} {casino:<25} {avg_win_pct:>9.2f}% {rating:<15}")

# Best/worst by denomination
summary_lines.append("\n" + "-" * 80)
summary_lines.append("LOOSEST CASINO BY DENOMINATION")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Denomination':<15} {'Loosest Casino':<25} {'Win%':>10}")
summary_lines.append("-" * 80)

# Get unique denominations (excluding Total Slots for this table)
analysis_denoms = [d for d in df['Denomination'].unique() if d != 'Total Slots']

for denom in analysis_denoms:
    denom_data = df[df['Denomination'] == denom].sort_values('Win_Pct')
    if len(denom_data) > 0:
        best = denom_data.iloc[0]
        summary_lines.append(f"{denom:<15} {best['Casino']:<25} {best['Win_Pct']:>9.2f}%")

summary_lines.append("\n" + "-" * 80)
summary_lines.append("TIGHTEST CASINO BY DENOMINATION")
summary_lines.append("-" * 80)
summary_lines.append(f"{'Denomination':<15} {'Tightest Casino':<25} {'Win%':>10}")
summary_lines.append("-" * 80)

for denom in analysis_denoms:
    denom_data = df[df['Denomination'] == denom].sort_values('Win_Pct', ascending=False)
    if len(denom_data) > 0:
        worst = denom_data.iloc[0]
        summary_lines.append(f"{denom:<15} {worst['Casino']:<25} {worst['Win_Pct']:>9.2f}%")

summary_lines.append("\n" + "=" * 80)
summary_lines.append("KEY INSIGHTS FOR JACKPOT HUNTERS")
summary_lines.append("=" * 80)
summary_lines.append("\n✓ Focus on casinos with Win% below 9.5% for best odds")
summary_lines.append("✓ Lower denominations typically have higher hold percentages")
summary_lines.append("✓ Win% variations between casinos can be significant")
summary_lines.append("✓ Check the heatmap to see patterns across denominations")
summary_lines.append("\n" + "=" * 80)

# Print summary
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# Save Excel with detailed data
df.to_excel(output_dir + fn_out, index=False)
tprint(f"\n✓ Detailed data saved to: {output_dir}{fn_out}")

# ────────────────────────────────────────────────
# VISUALIZATION 1: HEATMAP
# ────────────────────────────────────────────────

facecolor = '#EAEAEA'
text1 = '#252525'

# Filter out Total Slots for visualization (it's an aggregate)
df_viz = df[df['Denomination'] != 'Total Slots'].copy()

# Create pivot table for heatmap
pivot_df = df_viz.pivot(index='Casino', columns='Denomination', values='Win_Pct')

fig, ax = plt.subplots(figsize=(12, 8), facecolor=facecolor)

# Create heatmap with custom colormap (green = low Win% = good for players)
cmap = sns.diverging_palette(145, 10, s=80, l=55, as_cmap=True)  # Green to red

sns.heatmap(pivot_df, annot=True, fmt='.2f', cmap=cmap, center=10.0,
            cbar_kws={'label': 'Win % (Lower = Looser)'},
            linewidths=0.5, linecolor='white', ax=ax)

plt.title('Atlantic City Casino Hold Percentages by Denomination\n(Green = Looser / Red = Tighter)',
          fontsize=14, color=text1, fontweight='bold', pad=15)
plt.xlabel('Denomination', fontsize=12, color=text1, fontweight='bold')
plt.ylabel('Casino', fontsize=12, color=text1, fontweight='bold')

ax.tick_params(colors=text1)
plt.tight_layout()
plt.savefig(output_dir + fn_heatmap, facecolor=facecolor, dpi=150, bbox_inches='tight')
tprint(f"✓ Heatmap saved to: {output_dir}{fn_heatmap}")
plt.close()

# ────────────────────────────────────────────────
# VISUALIZATION 2: CASINO RANKINGS BAR CHART
# ────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(12, 8), facecolor=facecolor)
ax.set_facecolor(facecolor)

# Sort casinos by average Win% (ascending - lowest first)
casino_avg_sorted = casino_avg.sort_values()

# Create horizontal bar chart
y_pos = np.arange(len(casino_avg_sorted))

# Color bars by rating (green = loose, red = tight)
colors = []
for win_pct in casino_avg_sorted.values:
    if win_pct < 9.0:
        colors.append('#2A9D8F')  # Teal/green - loosest
    elif win_pct < 9.5:
        colors.append('#52B788')  # Light green - very good
    elif win_pct < 10.0:
        colors.append('#F4A261')  # Orange - good
    else:
        colors.append('#E76F51')  # Red - average/tight

bars = ax.barh(y_pos, casino_avg_sorted.values, color=colors, edgecolor='black', linewidth=0.8)

# Add Win% labels
for i, (casino, win_pct) in enumerate(casino_avg_sorted.items()):
    ax.text(win_pct, i, f"  {win_pct:.2f}%", ha='left', va='center',
            fontsize=10, color=text1, fontweight='bold')

# Set y-axis labels
ax.set_yticks(y_pos)
ax.set_yticklabels(casino_avg_sorted.index, fontsize=11, color=text1)

# Invert y-axis so lowest Win% is at top
ax.invert_yaxis()

plt.xlabel('Average Win % Across All Denominations', fontsize=12, color=text1, fontweight='bold')
plt.ylabel('Casino', fontsize=12, color=text1, fontweight='bold')
plt.title('Atlantic City Casinos Ranked by Hold Percentage\n(Lower = Better for Players)',
          fontsize=14, color=text1, pad=15, fontweight='bold')

# Add legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#2A9D8F', edgecolor='black', label='★★★ Loosest (<9.0%)'),
    Patch(facecolor='#52B788', edgecolor='black', label='★★ Very Good (9.0-9.5%)'),
    Patch(facecolor='#F4A261', edgecolor='black', label='★ Good (9.5-10.0%)'),
    Patch(facecolor='#E76F51', edgecolor='black', label='Average (>10.0%)')
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors=text1)

plt.tight_layout()
plt.savefig(output_dir + fn_rankings, facecolor=facecolor, dpi=150, bbox_inches='tight')
tprint(f"✓ Rankings chart saved to: {output_dir}{fn_rankings}")
plt.close()

# ────────────────────────────────────────────────
# SAVE SUMMARY
# ────────────────────────────────────────────────

tprint("\n" + "=" * 80)
tprint("PROCESSING COMPLETE!")
tprint("=" * 80)

# Save all output to file
with open(output_dir + fn_summary, 'w') as f:
    f.write('\n'.join(all_output))
tprint(f"\n✓ Full output saved to: {output_dir}{fn_summary}")

tprint("\n" + "=" * 80)
tprint("DATA EXTRACTION COMPLETE")
tprint(f"Analyzed {df['Casino'].nunique()} casinos across {df['Denomination'].nunique()} denomination categories")
tprint("=" * 80)
