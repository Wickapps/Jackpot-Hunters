"""
Nevada Win % by Location - Annual Trend Analysis

Iterates through 12 months of Nevada Gaming Control Board monthly PDF reports
for a given year and location, extracting slot machine win percentages by
denomination. Outputs a text summary and a line chart showing monthly trends.

Lower Win% = More player-friendly = Better opportunities

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NV_win_pct_location_annual.py <year> <location> [--input-dir DIR] [--output-dir DIR]

Examples:
    python NV_win_pct_location_annual.py 2025 "Las Vegas Strip"
    python NV_win_pct_location_annual.py 2025 "Reno" --input-dir docs/ --output-dir output/
    python NV_win_pct_location_annual.py 2025 "Statewide"

Valid locations (partial match supported):
    Statewide, Las Vegas Strip, Downtown Las Vegas, North Las Vegas,
    Laughlin, Boulder, Mesquite, Reno, Sparks, Lake Tahoe, Carson Valley,
    Elko, Wendover, and more
"""

# Nevada Gaming Control Board Monthly Reports:
# https://gaming.nv.gov/index.aspx?page=144

import tabula
import pandas as pd
import logging
import matplotlib.pyplot as plt
import numpy as np
import argparse
import os
import re
from datetime import datetime

# Optional OCR imports for scanned PDFs
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Suppress noisy warnings
logging.getLogger('tabula').setLevel(logging.ERROR)

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

MONTH_FULL = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']

# ────────────────────────────────────────────────
# OUTPUT CAPTURE
# ────────────────────────────────────────────────
all_output = []

def tprint(*args, **kwargs):
    """Print to console and capture output"""
    msg = ' '.join(str(arg) for arg in args)
    print(msg, **kwargs)
    all_output.append(msg)

# ────────────────────────────────────────────────
# COMMAND LINE ARGUMENTS
# ────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description='Nevada Win %% by Location - Annual Trend Analysis for Jackpot Hunters'
)
parser.add_argument('year', help='Year to analyze (e.g. 2025)')
parser.add_argument('location', help='Location to analyze (e.g. "Las Vegas Strip", "Reno", "Statewide")')
parser.add_argument('--input-dir', default='docs/',
                    help='Directory containing NV monthly PDFs (default: docs/)')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for reports (default: output/)')
parser.add_argument('--min-units', type=int, default=30,
                    help='Minimum gaming units for a denomination to be included (default: 30)')

args = parser.parse_args()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
year = args.year
location = args.location
input_dir = args.input_dir
output_dir = args.output_dir
min_units = args.min_units

if input_dir and not input_dir.endswith('/'):
    input_dir += '/'
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

os.makedirs(output_dir, exist_ok=True)

# Clean location for filenames (replace spaces with underscores)
location_clean = re.sub(r'[^a-zA-Z0-9]+', '_', location).strip('_')
fn_chart = f"NV_{year}_{location_clean}_win_pct.png"
fn_summary = f"NV_{year}_{location_clean}_win_pct.txt"

# ────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────
tprint("=" * 80)
tprint("NEVADA WIN % BY LOCATION - ANNUAL TREND ANALYSIS")
tprint("=" * 80)
tprint(f"Year: {year}")
tprint(f"Location: {location}")
tprint(f"Input directory: {input_dir}")
tprint(f"Output chart: {output_dir}{fn_chart}")
tprint(f"Output summary: {output_dir}{fn_summary}")
tprint(f"Min units filter: {min_units}")
tprint(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
tprint("=" * 80 + "\n")

# ────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ────────────────────────────────────────────────

def clean_number(val):
    """Clean and convert numeric values from PDF tables.
    Handles accounting-style negatives: (0.03) -> -0.03
    """
    if pd.isna(val):
        return None
    val_str = str(val).strip().replace(',', '').replace('$', '').replace('%', '')
    # Detect accounting-style negative: (123.45) -> -123.45
    is_negative = bool(re.match(r'^\(.*\)$', val_str))
    val_str = re.sub(r'[^\d.-]', '', val_str)
    try:
        result = float(val_str)
        if is_negative:
            result = -abs(result)
        return result
    except:
        return None

def find_location_table(tables, location_query):
    """Find the table matching a location query string"""
    # Try to match "All Nonrestricted Locations" tables for the given area
    for idx, table in enumerate(tables):
        if table.shape[0] < 15:
            continue
        header_text = str(table.iloc[0, 0])

        # Match logic: location query should appear in header, prefer "All Nonrestricted"
        if location_query.lower() in header_text.lower() and 'All Nonrestricted' in header_text:
            return idx, table

    # Fallback: match without "All Nonrestricted" requirement
    for idx, table in enumerate(tables):
        if table.shape[0] < 15:
            continue
        header_text = str(table.iloc[0, 0])
        if location_query.lower() in header_text.lower():
            return idx, table

    return None, None

def parse_current_month_slots(table, min_units=0):
    """Parse current month slot win percentages from a table.

    Handles two PDF extraction patterns:
      Pattern A (col 0 has everything): "1 Cent 282 34,730 176,664 (23.72) 10.12"
        -> 5 numbers in col 0, last is Win%
      Pattern B (win% in col 1): col 0 = "1 Cent 37 8,757 55,411 (29.62)", col 1 = "10.97"
        -> 4 numbers in col 0 (last is Change, NOT Win%), Win% is in col 1
    """
    data = {}
    slot_patterns = ['Cent', 'Dollar', 'Multi Denomination', 'Megabucks']

    # Find the "Slot Machines" section
    slot_section_start = None
    for idx in range(len(table)):
        row_text = str(table.iloc[idx, 0])
        if 'Slot Machines' in row_text or 'Slot Machine' in row_text:
            slot_section_start = idx + 1
            break

    if slot_section_start is None:
        return data

    # Parse slot rows
    for idx in range(slot_section_start, len(table)):
        row = table.iloc[idx]
        row_text = str(row.iloc[0]).strip()

        if ('Total Gaming' in row_text or 'Race Book' in row_text or
            '***' in row_text or row_text == '' or row_text == 'nan'):
            break

        if row_text.startswith('Total ') or row_text == 'Total':
            continue

        is_slot_row = any(pattern in row_text for pattern in slot_patterns)
        if not is_slot_row:
            continue

        # Extract denomination name
        denom_match = re.match(
            r'^([\d]+\s+Cent|[\d]+\s+Dollar|[\d]+\s+Dollars|Multi\s+Denomination|Megabucks|Other)\s+',
            row_text
        )

        if denom_match:
            denom_name = denom_match.group(1)
            numbers_text = row_text[len(denom_name):].strip()
            numbers = numbers_text.split()
        else:
            parts = row_text.split()
            denom_name = ""
            numbers = []
            for i, part in enumerate(parts):
                if re.search(r'^\(?\d', part):
                    denom_name = " ".join(parts[:i])
                    numbers = parts[i:]
                    break
            if not denom_name or len(denom_name) < 2:
                continue

        # Parse numbers from col 0: Locations, Units, WinAmount, [Change], [WinPercent]
        cleaned_numbers = []
        for num_str in numbers:
            num = clean_number(num_str)
            if num is not None:
                cleaned_numbers.append(num)

        win_pct = None

        if len(cleaned_numbers) >= 5:
            # Pattern A: all 5 values in col 0, last is Win%
            win_pct = cleaned_numbers[-1]
        else:
            # Pattern B: Win% is in column 1 (separate column)
            if table.shape[1] > 1:
                col1_val = clean_number(row.iloc[1])
                if col1_val is not None and 0 < abs(col1_val) < 50:
                    win_pct = col1_val

        if win_pct is not None and abs(win_pct) < 50:
            # Check units (2nd number) against minimum threshold
            units = int(cleaned_numbers[1]) if len(cleaned_numbers) >= 2 else 0
            if units >= min_units:
                data[denom_name] = (win_pct, units)

    return data

def ocr_extract_location_slots(pdf_path, location_query, min_units=0):
    """OCR fallback for scanned PDFs that tabula can't read.
    Returns (slot_data_dict, matched_header) or (None, None) on failure.
    """
    if not OCR_AVAILABLE:
        return None, None

    slot_patterns = ['Cent', 'Dollar', 'Multi Denomination', 'Megabucks']

    images = convert_from_path(pdf_path, dpi=400)
    for img in images:
        text = pytesseract.image_to_string(img, config='--psm 6 -c preserve_interword_spaces=1')

        # Check if this page has the location AND is "All Nonrestricted"
        if location_query.lower() not in text.lower():
            continue
        if 'All Nonrestricted' not in text:
            continue

        # Extract the matched header line
        matched_header = None
        for line in text.split('\n'):
            if location_query.lower() in line.lower() and 'All Nonrestricted' in line:
                matched_header = line.strip()
                break

        # Find the "Slot Machines" section and parse it
        lines = text.split('\n')
        in_slots = False
        data = {}

        for line in lines:
            stripped = line.strip()

            if 'Slot Machine' in stripped:
                in_slots = True
                continue

            if not in_slots:
                continue

            if 'Total Gaming' in stripped or stripped == '':
                if data:  # Stop once we have data and hit a boundary
                    break
                continue

            if stripped.startswith('Total ') or stripped == 'Total':
                continue

            # Check if this is a slot denomination line
            if not any(pattern in stripped for pattern in slot_patterns):
                continue

            # Extract denomination name using the same regex
            denom_match = re.match(
                r'^([\d]+\s+Cent|[\d]+\s+Dollar|[\d]+\s+Dollars|Multi\s+Denomination|Megabucks|Other)\s+',
                stripped
            )

            if not denom_match:
                continue

            denom_name = denom_match.group(1)
            numbers_text = stripped[len(denom_name):]

            # Extract ALL numbers from the line (covers all 3 time periods)
            all_numbers = re.findall(r'[\d,]+\.?\d*', numbers_text)
            cleaned = []
            for n in all_numbers:
                val = clean_number(n)
                if val is not None:
                    cleaned.append(val)

            # Current month is first 5 values: Locs, Units, WinAmt, Change, WinPct
            # Win% is the 5th number (index 4)
            if len(cleaned) >= 5:
                # Check units (2nd number) against minimum threshold
                units = int(cleaned[1]) if len(cleaned) >= 2 else 0
                if units < min_units:
                    continue
                win_pct = cleaned[4]
                if 0 < win_pct < 50:
                    data[denom_name] = (win_pct, units)
                elif win_pct >= 50:
                    # OCR may have missed a decimal point (e.g., "543" instead of "5.43")
                    corrected = win_pct / 100.0
                    if 0 < corrected < 50:
                        data[denom_name] = (corrected, units)

        if data:
            return data, matched_header

    return None, None

# ────────────────────────────────────────────────
# PROCESS ALL 12 MONTHS
# ────────────────────────────────────────────────
tprint("Processing monthly PDF files...\n")

monthly_data = {}   # {month_num: {denom: win_pct}}
monthly_units = {}  # {month_num: {denom: units}}
months_found = []
months_missing = []
location_header = None  # Store the full matched header for display

for month_num in range(1, 13):
    pdf_file = f"{input_dir}NV_{year}_{month_num:02d}.pdf"

    if not os.path.exists(pdf_file):
        tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✗ File not found: {pdf_file}")
        months_missing.append(month_num)
        continue

    try:
        tables = tabula.read_pdf(
            pdf_file,
            pages='all',
            multiple_tables=True,
            stream=True,
            guess=True,
            pandas_options={'header': None},
            java_options=["-Xmx4g"],
            silent=True
        )
        # Filter out tiny tables
        tables = [t for t in tables if t.shape[0] > 10 and t.shape[1] >= 3]
    except Exception as e:
        tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✗ Error reading PDF: {e}")
        months_missing.append(month_num)
        continue

    # Find the matching location table
    loc_idx, loc_table = find_location_table(tables, location)

    if loc_table is not None:
        # Store the matched header for display (first time only)
        if location_header is None:
            location_header = str(loc_table.iloc[0, 0])

        # Parse current month slot data
        slot_data = parse_current_month_slots(loc_table, min_units=min_units)

        if slot_data:
            monthly_data[month_num] = {d: v[0] for d, v in slot_data.items()}
            monthly_units[month_num] = {d: v[1] for d, v in slot_data.items()}
            months_found.append(month_num)
            tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✓ {len(slot_data)} denominations extracted")
            continue

    # Tabula failed - try OCR fallback for scanned PDFs
    if OCR_AVAILABLE:
        tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ⚠ Tabula failed, trying OCR fallback...")
        ocr_data, ocr_header = ocr_extract_location_slots(pdf_file, location, min_units=min_units)
        if ocr_data:
            monthly_data[month_num] = {d: v[0] for d, v in ocr_data.items()}
            monthly_units[month_num] = {d: v[1] for d, v in ocr_data.items()}
            months_found.append(month_num)
            if location_header is None and ocr_header:
                location_header = ocr_header
            tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✓ {len(ocr_data)} denominations extracted (via OCR)")
            continue

    tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✗ Location '{location}' not found in {os.path.basename(pdf_file)}")
    months_missing.append(month_num)

tprint(f"\n✓ Successfully processed {len(months_found)} of 12 months")
if months_missing:
    tprint(f"✗ Missing months: {', '.join(MONTH_NAMES[m-1] for m in months_missing)}")

if not monthly_data:
    tprint("\n✗ No data extracted. Check location name and input files.")
    exit(1)

# ────────────────────────────────────────────────
# BUILD ANNUAL DATA TABLE
# ────────────────────────────────────────────────
tprint("\nBuilding annual trend data...\n")

# Collect all denomination names across all months
all_denoms = set()
for month_data in monthly_data.values():
    all_denoms.update(month_data.keys())

# Sort denominations in a logical order
denom_order = ['1 Cent', '5 Cent', '25 Cent', '1 Dollar', '5 Dollars',
               '25 Dollars', '100 Dollars', 'Multi Denomination', 'Megabucks']

# Sort: known denoms first in order, then any extras alphabetically
sorted_denoms = [d for d in denom_order if d in all_denoms]
sorted_denoms += sorted(d for d in all_denoms if d not in denom_order)

# Build the data table
annual_df = pd.DataFrame(index=range(1, 13), columns=sorted_denoms)
annual_df.index.name = 'Month'

for month_num, month_data in monthly_data.items():
    for denom, win_pct in month_data.items():
        annual_df.loc[month_num, denom] = win_pct

# Convert to numeric
annual_df = annual_df.apply(pd.to_numeric, errors='coerce')

# ────────────────────────────────────────────────
# TEXT SUMMARY
# ────────────────────────────────────────────────

summary_lines = []

summary_lines.append("=" * 80)
summary_lines.append(f"{year} {location} Win % - Annual Trend Analysis")
summary_lines.append("=" * 80)
summary_lines.append(f"\nLocation: {location_header or location}")
summary_lines.append(f"Year: {year}")
summary_lines.append(f"Months Analyzed: {len(months_found)} of 12")
summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Monthly Win % Table
summary_lines.append("\n" + "=" * 80)
summary_lines.append("MONTHLY WIN % BY DENOMINATION")
summary_lines.append("=" * 80)

# Header row
header = f"{'Month':<6}"
for denom in sorted_denoms:
    # Short labels for the text table
    short = denom.replace(' Denomination', '').replace('Dollars', '$').replace('Dollar', '$').replace('Cent', 'c')
    header += f" {short:>9}"
summary_lines.append(header)
summary_lines.append("-" * len(header))

# Data rows
for month_num in range(1, 13):
    row_str = f"{MONTH_NAMES[month_num-1]:<6}"
    for denom in sorted_denoms:
        val = annual_df.loc[month_num, denom]
        if pd.notna(val):
            row_str += f" {val:>8.2f}%"
        else:
            row_str += f" {'---':>9}"
    summary_lines.append(row_str)

# Annual averages
summary_lines.append("-" * len(header))
avg_row = f"{'Avg':<6}"
for denom in sorted_denoms:
    avg = annual_df[denom].mean()
    if pd.notna(avg):
        avg_row += f" {avg:>8.2f}%"
    else:
        avg_row += f" {'---':>9}"
summary_lines.append(avg_row)

# Best/Worst analysis
summary_lines.append("\n" + "=" * 80)
summary_lines.append("JACKPOT HUNTER'S ANALYSIS")
summary_lines.append("=" * 80)

summary_lines.append(f"\n{'Denomination':<25} {'Avg Win%':>10} {'Best Month':>15} {'Worst Month':>15} {'Spread':>10}")
summary_lines.append("-" * 80)

for denom in sorted_denoms:
    col = annual_df[denom].dropna()
    if len(col) == 0:
        continue

    avg = col.mean()
    best_month = col.idxmin()
    worst_month = col.idxmax()
    best_val = col.min()
    worst_val = col.max()
    spread = worst_val - best_val

    best_str = f"{MONTH_NAMES[best_month-1]} ({best_val:.2f}%)"
    worst_str = f"{MONTH_NAMES[worst_month-1]} ({worst_val:.2f}%)"

    summary_lines.append(f"{denom:<25} {avg:>9.2f}% {best_str:>15} {worst_str:>15} {spread:>9.2f}%")

# Key takeaways
summary_lines.append("\n" + "=" * 80)
summary_lines.append("KEY TAKEAWAYS")
summary_lines.append("=" * 80)

# Find overall loosest denomination
avgs = {d: annual_df[d].mean() for d in sorted_denoms if pd.notna(annual_df[d].mean())}
if avgs:
    loosest = min(avgs, key=avgs.get)
    tightest = max(avgs, key=avgs.get)
    summary_lines.append(f"\n✓ LOOSEST denomination: {loosest} (avg {avgs[loosest]:.2f}% win)")
    summary_lines.append(f"✗ TIGHTEST denomination: {tightest} (avg {avgs[tightest]:.2f}% win)")

    # Find most volatile denomination (biggest spread)
    spreads = {}
    for denom in sorted_denoms:
        col = annual_df[denom].dropna()
        if len(col) >= 2:
            spreads[denom] = col.max() - col.min()
    if spreads:
        most_volatile = max(spreads, key=spreads.get)
        most_stable = min(spreads, key=spreads.get)
        summary_lines.append(f"\n✓ MOST STABLE: {most_stable} (spread: {spreads[most_stable]:.2f}%)")
        summary_lines.append(f"✗ MOST VOLATILE: {most_volatile} (spread: {spreads[most_volatile]:.2f}%)")

    summary_lines.append(f"\n✓ TIP: Lower win % = better for players. Focus on {loosest} for best odds.")
    summary_lines.append(f"✓ TIP: {most_stable} offers the most predictable returns." if spreads else "")

summary_lines.append("\n" + "=" * 80)
summary_lines.append("END OF REPORT")
summary_lines.append("=" * 80)

# Print and capture the summary
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# ────────────────────────────────────────────────
# LINE CHART
# ────────────────────────────────────────────────
tprint("\nGenerating annual trend chart...")

facecolor = '#EAEAEA'
text_color = '#252525'

# Color palette for denominations (matching example chart style)
denom_colors = {
    '1 Cent':              '#1f77b4',  # Blue
    '5 Cent':              '#2ca02c',  # Green
    '25 Cent':             '#ff7f0e',  # Orange
    '1 Dollar':            '#bcbd22',  # Yellow-green
    '5 Dollars':           '#8c564b',  # Brown
    '25 Dollars':          '#17becf',  # Cyan
    '100 Dollars':         '#393b79',  # Dark blue
    'Multi Denomination':  '#d62728',  # Red
    'Megabucks':           '#9467bd',  # Purple
}

fig, ax = plt.subplots(figsize=(14, 8), facecolor=facecolor)
ax.set_facecolor(facecolor)

# Plot each denomination as a line
for denom in sorted_denoms:
    col = annual_df[denom]
    valid = col.dropna()

    if len(valid) < 2:
        continue

    color = denom_colors.get(denom, '#333333')

    # Short label for legend
    label = denom.replace(' Denomination', '')

    ax.plot(valid.index, valid.values,
            marker='o', markersize=5, linewidth=2.0,
            color=color, label=label, zorder=3)

# Formatting
ax.set_xticks(range(1, 13))
ax.set_xticklabels(MONTH_NAMES, fontsize=11, color=text_color)
ax.set_ylabel('Win %', fontsize=13, color=text_color, fontweight='bold', fontstyle='italic')
ax.set_xlabel('')

ax.set_title(f'{year} {location} Win %',
             fontsize=16, color=text_color, fontweight='bold', pad=15)

# Grid
ax.grid(True, axis='both', alpha=0.4, linewidth=0.8, color='#CCCCCC')
ax.set_axisbelow(True)

# Y-axis range: auto with some padding
y_min = annual_df.min().min()
y_max = annual_df.max().max()
if pd.notna(y_min) and pd.notna(y_max):
    padding = (y_max - y_min) * 0.1
    ax.set_ylim(y_min - padding, y_max + padding)

# Legend
ax.legend(loc='upper right', fontsize=9, framealpha=0.9, edgecolor='#999999')

# Units info text box (avg units per denomination across months)
avg_units = {}
for denom in sorted_denoms:
    denom_units = [monthly_units[m][denom] for m in monthly_units if denom in monthly_units[m]]
    if denom_units:
        avg_units[denom] = int(sum(denom_units) / len(denom_units))

if avg_units:
    units_lines = ["Avg Units/Month"]
    for denom in sorted_denoms:
        if denom in avg_units:
            short = denom.replace(' Denomination', '').replace('Dollars', '$').replace('Dollar', '$').replace('Cent', '\u00a2')
            units_lines.append(f"  {short}: {avg_units[denom]:,}")
    units_text = "\n".join(units_lines)
    ax.text(0.01, 0.02, units_text, transform=ax.transAxes,
            fontsize=9, fontfamily='monospace', color=text_color,
            verticalalignment='bottom',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                      edgecolor='#999999', alpha=0.9))

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors=text_color, labelsize=10)

plt.tight_layout()
plt.savefig(output_dir + fn_chart, facecolor=facecolor, dpi=150, bbox_inches='tight')
tprint(f"✓ Chart saved to: {output_dir}{fn_chart}")
plt.close()

# ────────────────────────────────────────────────
# SAVE TEXT SUMMARY
# ────────────────────────────────────────────────
with open(output_dir + fn_summary, 'w') as f:
    f.write('\n'.join(all_output))

tprint(f"\n{'=' * 80}")
tprint("PROCESSING COMPLETE!")
tprint("=" * 80)
tprint(f"✓ Chart: {output_dir}{fn_chart}")
tprint(f"✓ Summary: {output_dir}{fn_summary}")
tprint(f"✓ Months processed: {len(months_found)}/12")
tprint(f"✓ Denominations tracked: {len(sorted_denoms)}")
tprint("=" * 80)
