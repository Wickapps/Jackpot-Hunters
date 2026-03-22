"""
Nevada Win % by Casino Size - Annual Trend Analysis

Compares total slot machine win percentages across casino revenue size tiers
for a given Nevada region. Answers the question: does casino size affect
how tight or loose the slots are?

Lower Win% = More player-friendly = Better opportunities

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NV_casino_size.py <year> <location> [--input-dir DIR] [--output-dir DIR]

Examples:
    python NV_casino_size.py 2025 "Las Vegas Strip"
    python NV_casino_size.py 2025 "Reno" --input-dir docs/ --output-dir output/
    python NV_casino_size.py 2025 "Downtown Las Vegas"

Revenue size tiers vary by region. The script auto-discovers which tiers
are available. Las Vegas Strip has the most granular breakdown:
    $12M-$36M, $36M-$72M, $72M+
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
    description='Nevada Win %% by Casino Size - Annual Trend Analysis for Jackpot Hunters'
)
parser.add_argument('year', help='Year to analyze (e.g. 2025)')
parser.add_argument('location', help='Location to analyze (e.g. "Las Vegas Strip", "Reno")')
parser.add_argument('--input-dir', default='docs/',
                    help='Directory containing NV monthly PDFs (default: docs/)')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for reports (default: output/)')

args = parser.parse_args()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
year = args.year
location = args.location
input_dir = args.input_dir
output_dir = args.output_dir

if input_dir and not input_dir.endswith('/'):
    input_dir += '/'
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

os.makedirs(output_dir, exist_ok=True)

# Clean location for filenames
location_clean = re.sub(r'[^a-zA-Z0-9]+', '_', location).strip('_')
fn_chart = f"NV_{year}_{location_clean}_casino_size.png"
fn_summary = f"NV_{year}_{location_clean}_casino_size.txt"

# ────────────────────────────────────────────────
# REVENUE TIER MAPPING
# ────────────────────────────────────────────────
# Maps full PDF header suffixes to short display labels
TIER_MAP = {
    'All Nonrestricted Locations':                   'All Sizes',
    '$1,000,000 and Over Revenue Range':             '$1M+',
    '$12,000,000 to $36,000,000 Revenue Range':      '$12M-$36M',
    '$36,000,000 to $72,000,000 Revenue Range':      '$36M-$72M',
    '$72,000,000 and Over Revenue Range':            '$72M+',
    '$36,000,000 and Over Revenue Range':            '$36M+',
    '$12,000,000 and Over Revenue Range':            '$12M+',
}

# Tiers to skip (nearly identical to "All Sizes" for most regions)
SKIP_TIERS = {'$1M+'}

# Display order for tiers (smallest to largest)
TIER_ORDER = ['All Sizes', '$12M-$36M', '$36M-$72M', '$72M+',
              '$36M+', '$12M+']

# ────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────
tprint("=" * 80)
tprint("NEVADA WIN % BY CASINO SIZE - ANNUAL TREND ANALYSIS")
tprint("=" * 80)
tprint(f"Year: {year}")
tprint(f"Location: {location}")
tprint(f"Input directory: {input_dir}")
tprint(f"Output chart: {output_dir}{fn_chart}")
tprint(f"Output summary: {output_dir}{fn_summary}")
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
    is_negative = bool(re.match(r'^\(.*\)$', val_str))
    val_str = re.sub(r'[^\d.-]', '', val_str)
    try:
        result = float(val_str)
        if is_negative:
            result = -abs(result)
        return result
    except:
        return None

def classify_tier(header_text):
    """Extract the revenue tier label from a table header string.
    Returns (tier_label, location_prefix) or (None, None) if not a revenue tier table.
    """
    for suffix, label in TIER_MAP.items():
        if suffix in header_text:
            prefix = header_text.split(' - ')[0].strip() if ' - ' in header_text else header_text
            return label, prefix
    return None, None

def find_location_tier_tables(tables, location_query):
    """Find all tables for a location, grouped by revenue tier.
    Returns {tier_label: (table_index, table_df)}
    """
    result = {}
    for idx, table in enumerate(tables):
        if table.shape[0] < 10:
            continue
        header_text = str(table.iloc[0, 0])
        if location_query.lower() not in header_text.lower():
            continue

        tier_label, prefix = classify_tier(header_text)
        if tier_label is None or tier_label in SKIP_TIERS:
            continue

        result[tier_label] = (idx, table)

    return result

def parse_total_slot_winpct(table):
    """Extract the Total Slot Machines win% and units from a table.
    Returns (win_pct, units) or None if not found.

    Looks for the "Total" row inside the Slot Machines section.
    Uses the same Pattern A/B logic as the denomination parser.
    """
    in_slots = False

    for idx in range(len(table)):
        row = table.iloc[idx]
        row_text = str(row.iloc[0]).strip()

        if 'Slot Machines' in row_text or 'Slot Machine' in row_text:
            in_slots = True
            continue

        if not in_slots:
            continue

        # Stop if we've left the slot section
        if ('Race Book' in row_text or 'Total Gaming' in row_text or
            '***' in row_text):
            break

        # Look for the Total row
        if not (row_text.startswith('Total ') or row_text == 'Total'):
            continue

        # Parse numbers from the Total row
        # Remove the "Total" prefix
        numbers_text = row_text[5:].strip() if row_text.startswith('Total ') else ''
        numbers = numbers_text.split()

        cleaned_numbers = []
        for num_str in numbers:
            num = clean_number(num_str)
            if num is not None:
                cleaned_numbers.append(num)

        win_pct = None
        units = 0

        if len(cleaned_numbers) >= 5:
            # Pattern A: Locs, Units, WinAmt, Change, WinPct
            win_pct = cleaned_numbers[-1]
            units = int(cleaned_numbers[1])
        elif len(cleaned_numbers) >= 2:
            # Pattern B: fewer numbers in col 0, check col 1
            if table.shape[1] > 1:
                col1_val = clean_number(row.iloc[1])
                if col1_val is not None and abs(col1_val) < 50:
                    win_pct = col1_val
                    units = int(cleaned_numbers[1]) if len(cleaned_numbers) >= 2 else 0

        if win_pct is not None and abs(win_pct) < 50:
            return (win_pct, units)

    return None

def ocr_extract_tier_data(pdf_path, location_query):
    """OCR fallback for scanned PDFs. Extracts Total Slot Win% for all
    revenue tiers found for the given location.
    Returns {tier_label: (win_pct, units)} or empty dict.
    """
    if not OCR_AVAILABLE:
        return {}

    images = convert_from_path(pdf_path, dpi=400)
    results = {}

    for img in images:
        text = pytesseract.image_to_string(img, config='--psm 6 -c preserve_interword_spaces=1')

        if location_query.lower() not in text.lower():
            continue

        # Determine which tier this page represents
        tier_label = None
        for suffix, label in TIER_MAP.items():
            if suffix in text and label not in SKIP_TIERS:
                tier_label = label
                break

        if tier_label is None:
            continue

        # Already found this tier
        if tier_label in results:
            continue

        # Find Total Slots row in OCR text
        lines = text.split('\n')
        in_slots = False

        for line in lines:
            stripped = line.strip()

            if 'Slot Machine' in stripped:
                in_slots = True
                continue

            if not in_slots:
                continue

            if 'Race Book' in stripped or 'Total Gaming' in stripped:
                break

            if not (stripped.startswith('Total ') or stripped == 'Total'):
                continue

            # Parse the Total row
            numbers_text = stripped[5:].strip() if stripped.startswith('Total ') else ''
            all_numbers = re.findall(r'[\d,]+\.?\d*', numbers_text)
            cleaned = []
            for n in all_numbers:
                val = clean_number(n)
                if val is not None:
                    cleaned.append(val)

            # First 5 values: Locs, Units, WinAmt, Change, WinPct
            if len(cleaned) >= 5:
                win_pct = cleaned[4]
                units = int(cleaned[1])
                if 0 < win_pct < 50:
                    results[tier_label] = (win_pct, units)
                elif win_pct >= 50:
                    corrected = win_pct / 100.0
                    if 0 < corrected < 50:
                        results[tier_label] = (corrected, units)
            break  # Only one Total row per page

    return results

# ────────────────────────────────────────────────
# PROCESS ALL 12 MONTHS
# ────────────────────────────────────────────────
tprint("Processing monthly PDF files...\n")

monthly_data = {}   # {month_num: {tier_label: win_pct}}
monthly_units = {}  # {month_num: {tier_label: units}}
months_found = []
months_missing = []
all_tiers = set()
location_header = None

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
        tables = [t for t in tables if t.shape[0] > 10 and t.shape[1] >= 3]
    except Exception as e:
        tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✗ Error reading PDF: {e}")
        months_missing.append(month_num)
        continue

    # Find all tier tables for this location
    tier_tables = find_location_tier_tables(tables, location)

    if tier_tables:
        month_winpcts = {}
        month_unit_counts = {}

        if location_header is None:
            # Use first table's header to get the location prefix
            first_table = list(tier_tables.values())[0][1]
            header = str(first_table.iloc[0, 0])
            location_header = header.split(' - ')[0].strip() if ' - ' in header else header

        for tier_label, (tidx, tbl) in tier_tables.items():
            result = parse_total_slot_winpct(tbl)
            if result is not None:
                win_pct, units = result
                month_winpcts[tier_label] = win_pct
                month_unit_counts[tier_label] = units
                all_tiers.add(tier_label)

        if month_winpcts:
            monthly_data[month_num] = month_winpcts
            monthly_units[month_num] = month_unit_counts
            months_found.append(month_num)
            tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✓ {len(month_winpcts)} casino size tiers extracted")
            continue

    # Tabula failed — try OCR fallback
    if OCR_AVAILABLE:
        tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ⚠ Tabula failed, trying OCR fallback...")
        ocr_results = ocr_extract_tier_data(pdf_file, location)
        if ocr_results:
            month_winpcts = {t: v[0] for t, v in ocr_results.items()}
            month_unit_counts = {t: v[1] for t, v in ocr_results.items()}
            monthly_data[month_num] = month_winpcts
            monthly_units[month_num] = month_unit_counts
            months_found.append(month_num)
            all_tiers.update(month_winpcts.keys())
            tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✓ {len(month_winpcts)} casino size tiers extracted (via OCR)")
            continue

    tprint(f"  {MONTH_NAMES[month_num-1]:>3}: ✗ Location '{location}' not found in {os.path.basename(pdf_file)}")
    months_missing.append(month_num)

tprint(f"\n✓ Successfully processed {len(months_found)} of 12 months")
if months_missing:
    tprint(f"✗ Missing months: {', '.join(MONTH_NAMES[m-1] for m in months_missing)}")
tprint(f"✓ Casino size tiers found: {', '.join(sorted(all_tiers))}")

if not monthly_data:
    tprint("\n✗ No data extracted. Check location name and input files.")
    exit(1)

# ────────────────────────────────────────────────
# BUILD ANNUAL DATA TABLE
# ────────────────────────────────────────────────
tprint("\nBuilding annual trend data...\n")

# Sort tiers in logical order
sorted_tiers = [t for t in TIER_ORDER if t in all_tiers]
sorted_tiers += sorted(t for t in all_tiers if t not in TIER_ORDER)

# Build the data table
annual_df = pd.DataFrame(index=range(1, 13), columns=sorted_tiers)
annual_df.index.name = 'Month'

for month_num, month_data in monthly_data.items():
    for tier, win_pct in month_data.items():
        annual_df.loc[month_num, tier] = win_pct

annual_df = annual_df.apply(pd.to_numeric, errors='coerce')

# ────────────────────────────────────────────────
# TEXT SUMMARY
# ────────────────────────────────────────────────

summary_lines = []

summary_lines.append("=" * 80)
summary_lines.append(f"{year} {location} Win % by Casino Size")
summary_lines.append("=" * 80)
summary_lines.append(f"\nLocation: {location_header or location}")
summary_lines.append(f"Year: {year}")
summary_lines.append(f"Months Analyzed: {len(months_found)} of 12")
summary_lines.append(f"Casino Size Tiers: {len(sorted_tiers)}")
summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Monthly Win % Table
summary_lines.append("\n" + "=" * 80)
summary_lines.append("MONTHLY TOTAL SLOT WIN % BY CASINO SIZE")
summary_lines.append("=" * 80)

header = f"{'Month':<6}"
for tier in sorted_tiers:
    header += f" {tier:>12}"
summary_lines.append(header)
summary_lines.append("-" * len(header))

for month_num in range(1, 13):
    row_str = f"{MONTH_NAMES[month_num-1]:<6}"
    for tier in sorted_tiers:
        val = annual_df.loc[month_num, tier]
        if pd.notna(val):
            row_str += f" {val:>11.2f}%"
        else:
            row_str += f" {'---':>12}"
    summary_lines.append(row_str)

# Annual averages
summary_lines.append("-" * len(header))
avg_row = f"{'Avg':<6}"
for tier in sorted_tiers:
    avg = annual_df[tier].mean()
    if pd.notna(avg):
        avg_row += f" {avg:>11.2f}%"
    else:
        avg_row += f" {'---':>12}"
summary_lines.append(avg_row)

# Casino size comparison
summary_lines.append("\n" + "=" * 80)
summary_lines.append("CASINO SIZE COMPARISON")
summary_lines.append("=" * 80)

summary_lines.append(f"\n{'Casino Size':<15} {'Avg Win%':>10} {'Best Month':>15} {'Worst Month':>15} {'Spread':>10}")
summary_lines.append("-" * 70)

for tier in sorted_tiers:
    col = annual_df[tier].dropna()
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

    summary_lines.append(f"{tier:<15} {avg:>9.2f}% {best_str:>15} {worst_str:>15} {spread:>9.2f}%")

# Key takeaways
summary_lines.append("\n" + "=" * 80)
summary_lines.append("JACKPOT HUNTER'S TAKEAWAYS")
summary_lines.append("=" * 80)

avgs = {t: annual_df[t].mean() for t in sorted_tiers if pd.notna(annual_df[t].mean())}
if avgs:
    loosest = min(avgs, key=avgs.get)
    tightest = max(avgs, key=avgs.get)
    delta = avgs[tightest] - avgs[loosest]

    summary_lines.append(f"\n✓ LOOSEST casino size: {loosest} (avg {avgs[loosest]:.2f}% win)")
    summary_lines.append(f"✗ TIGHTEST casino size: {tightest} (avg {avgs[tightest]:.2f}% win)")
    summary_lines.append(f"\n  Delta between loosest and tightest: {delta:.2f}%")

    if delta < 0.5:
        summary_lines.append("  → Casino size has MINIMAL impact on slot Win% in this region.")
    elif delta < 1.5:
        summary_lines.append("  → Casino size has a MODERATE impact on slot Win% in this region.")
    else:
        summary_lines.append("  → Casino size has a SIGNIFICANT impact on slot Win% in this region.")
        summary_lines.append(f"  → TIP: For better odds, target {loosest} casinos in {location}.")

    # Avg units for context
    summary_lines.append(f"\n  Average Units by Casino Size:")
    for tier in sorted_tiers:
        tier_units = [monthly_units[m][tier] for m in monthly_units if tier in monthly_units[m]]
        if tier_units:
            avg_u = int(sum(tier_units) / len(tier_units))
            summary_lines.append(f"    {tier}: {avg_u:,} machines")

summary_lines.append("\n" + "=" * 80)
summary_lines.append("END OF REPORT")
summary_lines.append("=" * 80)

# Print and capture
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# ────────────────────────────────────────────────
# LINE CHART
# ────────────────────────────────────────────────
tprint("\nGenerating casino size trend chart...")

facecolor = '#EAEAEA'
text_color = '#252525'

# Color palette for tiers
tier_colors = {
    'All Sizes':   '#252525',  # Dark gray (baseline)
    '$12M-$36M':   '#2ca02c',  # Green
    '$36M-$72M':   '#ff7f0e',  # Orange
    '$72M+':       '#1f77b4',  # Blue
    '$36M+':       '#d62728',  # Red
    '$12M+':       '#9467bd',  # Purple
}

fig, ax = plt.subplots(figsize=(14, 8), facecolor=facecolor)
ax.set_facecolor(facecolor)

for tier in sorted_tiers:
    col = annual_df[tier]
    valid = col.dropna()

    if len(valid) < 2:
        continue

    color = tier_colors.get(tier, '#333333')

    ax.plot(valid.index, valid.values,
            marker='o', markersize=6, linewidth=2.5,
            color=color, label=tier, zorder=3)

# Formatting
ax.set_xticks(range(1, 13))
ax.set_xticklabels(MONTH_NAMES, fontsize=11, color=text_color)
ax.set_ylabel('Total Slot Win %', fontsize=13, color=text_color, fontweight='bold', fontstyle='italic')
ax.set_xlabel('')

ax.set_title(f'{year} {location} - Win % by Casino Size',
             fontsize=16, color=text_color, fontweight='bold', pad=15)

# Grid
ax.grid(True, axis='both', alpha=0.4, linewidth=0.8, color='#CCCCCC')
ax.set_axisbelow(True)

# Y-axis range with padding
y_min = annual_df.min().min()
y_max = annual_df.max().max()
if pd.notna(y_min) and pd.notna(y_max):
    padding = (y_max - y_min) * 0.15
    ax.set_ylim(y_min - padding, y_max + padding)

# Legend
ax.legend(loc='upper right', fontsize=10, framealpha=0.9, edgecolor='#999999')

# Units info box
avg_units_map = {}
for tier in sorted_tiers:
    tier_units = [monthly_units[m][tier] for m in monthly_units if tier in monthly_units[m]]
    if tier_units:
        avg_units_map[tier] = int(sum(tier_units) / len(tier_units))

if avg_units_map:
    units_lines = ["Avg Units/Month"]
    for tier in sorted_tiers:
        if tier in avg_units_map:
            units_lines.append(f"  {tier}: {avg_units_map[tier]:,}")
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
tprint(f"✓ Casino size tiers: {len(sorted_tiers)}")
tprint("=" * 80)
