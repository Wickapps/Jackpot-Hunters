"""
Nevada Win % Comparison - Las Vegas Strip vs Reno

Side-by-side comparison of slot machine win percentages between Las Vegas Strip
and Reno for one or more monthly Nevada Gaming Control Board reports.
Shows total slot Win% and per-denomination breakdown for both regions.

Lower Win% = More player-friendly = Better opportunities

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NV_win_pct_vegas_reno.py <pdf_file> [pdf_file2 ...] [--output-dir DIR]

Examples:
    python NV_win_pct_vegas_reno.py docs/NV_2025_01.pdf
    python NV_win_pct_vegas_reno.py docs/NV_2025_*.pdf
    python NV_win_pct_vegas_reno.py docs/NV_2025_01.pdf docs/NV_2025_06.pdf --output-dir output/
"""

# Nevada Gaming Control Board Monthly Reports:
# https://gaming.nv.gov/index.aspx?page=144

import tabula
import pandas as pd
import logging
import argparse
import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Optional OCR imports for scanned PDFs
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Suppress noisy warnings
logging.getLogger('tabula').setLevel(logging.ERROR)

MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']

REGIONS = ['Las Vegas Strip', 'Reno']

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
    description='Nevada Win %% Comparison - Las Vegas Strip vs Reno'
)
parser.add_argument('pdf_files', nargs='+', help='One or more NV monthly PDF files')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for reports (default: output/)')
parser.add_argument('--min-units', type=int, default=30,
                    help='Minimum gaming units for a denomination to be included (default: 30)')

args = parser.parse_args()

output_dir = args.output_dir
min_units = args.min_units

if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

os.makedirs(output_dir, exist_ok=True)

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

def find_location_table(tables, location_query):
    """Find the 'All Nonrestricted Locations' table for a given location."""
    for idx, table in enumerate(tables):
        if table.shape[0] < 15:
            continue
        header_text = str(table.iloc[0, 0])
        if location_query.lower() in header_text.lower() and 'All Nonrestricted' in header_text:
            return idx, table

    # Fallback without "All Nonrestricted"
    for idx, table in enumerate(tables):
        if table.shape[0] < 15:
            continue
        header_text = str(table.iloc[0, 0])
        if location_query.lower() in header_text.lower():
            return idx, table

    return None, None

def parse_slot_data(table, min_units=0):
    """Parse slot data from a table. Returns dict with per-denomination Win%
    and a 'Total' entry for the combined slot Win%.
    Returns {denom_name: (win_pct, units)}
    """
    data = {}
    slot_patterns = ['Cent', 'Dollar', 'Multi Denomination', 'Megabucks']
    in_slots = False

    for idx in range(len(table)):
        row = table.iloc[idx]
        row_text = str(row.iloc[0]).strip()

        if 'Slot Machines' in row_text or 'Slot Machine' in row_text:
            in_slots = True
            continue

        if not in_slots:
            continue

        if ('Total Gaming' in row_text or 'Race Book' in row_text or
            '***' in row_text or row_text == '' or row_text == 'nan'):
            break

        # Handle "Total" row
        is_total = row_text.startswith('Total ') or row_text == 'Total'

        if is_total:
            denom_name = 'Total Slots'
            numbers_text = row_text[5:].strip() if row_text.startswith('Total ') else ''
            numbers = numbers_text.split()
        else:
            # Skip non-slot rows
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

        # Parse numbers
        cleaned_numbers = []
        for num_str in numbers:
            num = clean_number(num_str)
            if num is not None:
                cleaned_numbers.append(num)

        win_pct = None

        if len(cleaned_numbers) >= 5:
            win_pct = cleaned_numbers[-1]
        else:
            if table.shape[1] > 1:
                col1_val = clean_number(row.iloc[1])
                if col1_val is not None and 0 < abs(col1_val) < 50:
                    win_pct = col1_val

        if win_pct is not None and abs(win_pct) < 50:
            units = int(cleaned_numbers[1]) if len(cleaned_numbers) >= 2 else 0
            # Apply min_units filter for denominations, but always include Total
            if is_total or units >= min_units:
                data[denom_name] = (win_pct, units)

    return data

def ocr_extract_region_data(pdf_path, location_query, min_units=0):
    """OCR fallback for scanned PDFs. Extracts slot data for a region.
    Returns {denom_name: (win_pct, units)} or empty dict.
    """
    if not OCR_AVAILABLE:
        return {}

    slot_patterns = ['Cent', 'Dollar', 'Multi Denomination', 'Megabucks']

    images = convert_from_path(pdf_path, dpi=400)
    for img in images:
        text = pytesseract.image_to_string(img, config='--psm 6 -c preserve_interword_spaces=1')

        if location_query.lower() not in text.lower():
            continue
        if 'All Nonrestricted' not in text:
            continue

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

            if 'Total Gaming' in stripped or 'Race Book' in stripped:
                if data:
                    break
                continue

            # Handle Total row
            is_total = stripped.startswith('Total ') or stripped == 'Total'

            if is_total:
                denom_name = 'Total Slots'
                numbers_text = stripped[5:].strip() if stripped.startswith('Total ') else ''
            elif any(pattern in stripped for pattern in slot_patterns):
                denom_match = re.match(
                    r'^([\d]+\s+Cent|[\d]+\s+Dollar|[\d]+\s+Dollars|Multi\s+Denomination|Megabucks|Other)\s+',
                    stripped
                )
                if not denom_match:
                    continue
                denom_name = denom_match.group(1)
                numbers_text = stripped[len(denom_name):]
            else:
                continue

            all_numbers = re.findall(r'[\d,]+\.?\d*', numbers_text)
            cleaned = []
            for n in all_numbers:
                val = clean_number(n)
                if val is not None:
                    cleaned.append(val)

            if len(cleaned) >= 5:
                units = int(cleaned[1])
                if not is_total and units < min_units:
                    continue
                win_pct = cleaned[4]
                if 0 < win_pct < 50:
                    data[denom_name] = (win_pct, units)
                elif win_pct >= 50:
                    corrected = win_pct / 100.0
                    if 0 < corrected < 50:
                        data[denom_name] = (corrected, units)

        if data:
            return data

    return {}

def extract_month_year(pdf_path):
    """Try to extract month/year from filename like NV_2025_01.pdf"""
    basename = os.path.basename(pdf_path)
    match = re.search(r'NV_(\d{4})_(\d{2})', basename)
    if match:
        year = match.group(1)
        month_num = int(match.group(2))
        if 1 <= month_num <= 12:
            return f"{MONTH_NAMES[month_num-1]} {year}"
    return basename

# ────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────
tprint("=" * 80)
tprint("NEVADA WIN % COMPARISON - LAS VEGAS STRIP vs RENO")
tprint("=" * 80)
tprint(f"PDF files: {len(args.pdf_files)}")
tprint(f"Min units filter: {min_units}")
tprint(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
tprint("=" * 80 + "\n")

# ────────────────────────────────────────────────
# PROCESS EACH PDF
# ────────────────────────────────────────────────

# Sort input files by name for consistent ordering
pdf_files = sorted(args.pdf_files)

# Chart data collection (populated during main loop)
chart_months = []       # month labels in order
chart_vegas = []        # Vegas Total Slot Win% per month
chart_reno = []         # Reno Total Slot Win% per month
chart_denom_data = []   # per-file [{region: {denom: (win_pct, units)}}]

# Denomination display order
denom_order = ['1 Cent', '5 Cent', '25 Cent', '1 Dollar', '5 Dollars',
               '25 Dollars', '100 Dollars', 'Multi Denomination', 'Megabucks']

for pdf_file in pdf_files:
    if not os.path.exists(pdf_file):
        tprint(f"✗ File not found: {pdf_file}\n")
        continue

    month_label = extract_month_year(pdf_file)
    tprint(f"Processing: {os.path.basename(pdf_file)} ({month_label})")
    tprint("-" * 80)

    # Extract tables with tabula
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
        tprint(f"  ✗ Error reading PDF: {e}\n")
        continue

    # Extract data for each region
    region_data = {}  # {region: {denom: (win_pct, units)}}

    for region in REGIONS:
        loc_idx, loc_table = find_location_table(tables, region)

        if loc_table is not None:
            data = parse_slot_data(loc_table, min_units=min_units)
            if data:
                region_data[region] = data
                continue

        # OCR fallback
        if OCR_AVAILABLE:
            tprint(f"  {region}: ⚠ Tabula failed, trying OCR...")
            data = ocr_extract_region_data(pdf_file, region, min_units=min_units)
            if data:
                region_data[region] = data
                continue

        tprint(f"  {region}: ✗ Data not found")

    if len(region_data) < 2:
        tprint(f"  ✗ Could not extract data for both regions\n")
        continue

    # ── Build comparison table ──

    # Collect all denominations present in either region
    all_denoms = set()
    for data in region_data.values():
        all_denoms.update(k for k in data.keys() if k != 'Total Slots')

    sorted_denoms = [d for d in denom_order if d in all_denoms]
    sorted_denoms += sorted(d for d in all_denoms if d not in denom_order)

    # Print the comparison
    tprint(f"\n{'':>22} {'Las Vegas Strip':>18} {'Reno':>18} {'Delta':>10}")
    tprint(f"{'':>22} {'Win%':>10} {'Units':>7} {'Win%':>10} {'Units':>7} {'(LV-Reno)':>10}")
    tprint("-" * 80)

    # Total Slots first
    vegas_total = region_data.get('Las Vegas Strip', {}).get('Total Slots')
    reno_total = region_data.get('Reno', {}).get('Total Slots')

    if vegas_total and reno_total:
        delta = vegas_total[0] - reno_total[0]
        sign = '+' if delta > 0 else ''
        tprint(f"  {'TOTAL SLOTS':<20} {vegas_total[0]:>9.2f}% {vegas_total[1]:>6,} {reno_total[0]:>9.2f}% {reno_total[1]:>6,} {sign}{delta:>8.2f}%")
    tprint("-" * 80)

    # Per denomination
    for denom in sorted_denoms:
        vegas = region_data.get('Las Vegas Strip', {}).get(denom)
        reno = region_data.get('Reno', {}).get(denom)

        short = denom.replace(' Denomination', '')
        v_pct = f"{vegas[0]:>9.2f}%" if vegas else f"{'---':>10}"
        v_units = f"{vegas[1]:>6,}" if vegas else f"{'---':>7}"
        r_pct = f"{reno[0]:>9.2f}%" if reno else f"{'---':>10}"
        r_units = f"{reno[1]:>6,}" if reno else f"{'---':>7}"

        if vegas and reno:
            delta = vegas[0] - reno[0]
            sign = '+' if delta > 0 else ''
            d_str = f"{sign}{delta:>8.2f}%"
        else:
            d_str = f"{'---':>10}"

        tprint(f"  {short:<20} {v_pct} {v_units} {r_pct} {r_units} {d_str}")

    # Summary
    tprint("")
    if vegas_total and reno_total:
        delta = vegas_total[0] - reno_total[0]
        if delta > 0:
            tprint(f"  → Reno slots are LOOSER by {abs(delta):.2f}% (lower win = better for players)")
        elif delta < 0:
            tprint(f"  → Las Vegas Strip slots are LOOSER by {abs(delta):.2f}% (lower win = better for players)")
        else:
            tprint(f"  → Both regions have identical total slot Win%")

        tprint(f"  → Las Vegas Strip: {vegas_total[1]:,} total slot units")
        tprint(f"  → Reno: {reno_total[1]:,} total slot units")

    tprint("")

    # Collect chart data
    chart_months.append(month_label)
    chart_vegas.append(vegas_total[0] if vegas_total else None)
    chart_reno.append(reno_total[0] if reno_total else None)
    chart_denom_data.append(region_data)

# ────────────────────────────────────────────────
# MULTI-MONTH SUMMARY (if more than one file)
# ────────────────────────────────────────────────
if len(pdf_files) > 1:
    tprint("=" * 80)
    tprint("MULTI-MONTH SUMMARY")
    tprint("=" * 80)

    # Re-process to collect totals per month
    # (we already printed per-file, now aggregate)
    vegas_totals = []
    reno_totals = []

    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            continue

        month_label = extract_month_year(pdf_file)

        try:
            tables = tabula.read_pdf(
                pdf_file, pages='all', multiple_tables=True, stream=True,
                guess=True, pandas_options={'header': None},
                java_options=["-Xmx4g"], silent=True
            )
            tables = [t for t in tables if t.shape[0] > 10 and t.shape[1] >= 3]
        except:
            continue

        month_results = {}
        for region in REGIONS:
            loc_idx, loc_table = find_location_table(tables, region)
            if loc_table is not None:
                data = parse_slot_data(loc_table, min_units=min_units)
                if data and 'Total Slots' in data:
                    month_results[region] = data['Total Slots']
                    continue
            if OCR_AVAILABLE:
                data = ocr_extract_region_data(pdf_file, region, min_units=min_units)
                if data and 'Total Slots' in data:
                    month_results[region] = data['Total Slots']

        if 'Las Vegas Strip' in month_results:
            vegas_totals.append((month_label, month_results['Las Vegas Strip'][0]))
        if 'Reno' in month_results:
            reno_totals.append((month_label, month_results['Reno'][0]))

    tprint(f"\n{'Month':<20} {'Las Vegas Strip':>16} {'Reno':>16} {'Delta (LV-Reno)':>16}")
    tprint("-" * 70)

    vegas_dict = {m: v for m, v in vegas_totals}
    reno_dict = {m: v for m, v in reno_totals}
    all_months = list(dict.fromkeys([m for m, _ in vegas_totals] + [m for m, _ in reno_totals]))

    vegas_vals = []
    reno_vals = []

    for month in all_months:
        v = vegas_dict.get(month)
        r = reno_dict.get(month)
        v_str = f"{v:>15.2f}%" if v else f"{'---':>16}"
        r_str = f"{r:>15.2f}%" if r else f"{'---':>16}"

        if v is not None and r is not None:
            delta = v - r
            sign = '+' if delta > 0 else ''
            d_str = f"{sign}{delta:>14.2f}%"
            vegas_vals.append(v)
            reno_vals.append(r)
        else:
            d_str = f"{'---':>16}"

        tprint(f"{month:<20} {v_str} {r_str} {d_str}")

    if vegas_vals and reno_vals:
        avg_v = sum(vegas_vals) / len(vegas_vals)
        avg_r = sum(reno_vals) / len(reno_vals)
        avg_delta = avg_v - avg_r
        sign = '+' if avg_delta > 0 else ''
        tprint("-" * 70)
        tprint(f"{'Average':<20} {avg_v:>15.2f}% {avg_r:>15.2f}% {sign}{avg_delta:>14.2f}%")

        tprint(f"\n✓ Over {len(vegas_vals)} months, ", end='')
        if avg_delta > 0:
            tprint(f"Reno slots are LOOSER by an average of {abs(avg_delta):.2f}%")
        elif avg_delta < 0:
            tprint(f"Las Vegas Strip slots are LOOSER by an average of {abs(avg_delta):.2f}%")
        else:
            tprint(f"both regions have identical average Win%")

    tprint("")

# ────────────────────────────────────────────────
# GENERATE CHART
# ────────────────────────────────────────────────
fn_chart = "NV_win_pct_vegas_vs_reno.png"

facecolor = '#EAEAEA'
text_color = '#252525'

# Filter to months where both regions have data
valid_months = []
valid_vegas = []
valid_reno = []
for i, month in enumerate(chart_months):
    if chart_vegas[i] is not None and chart_reno[i] is not None:
        valid_months.append(month)
        valid_vegas.append(chart_vegas[i])
        valid_reno.append(chart_reno[i])

if len(valid_months) >= 2:
    # ── Multi-month line chart ──
    tprint("\nGenerating Vegas vs Reno trend chart...")

    fig, ax = plt.subplots(figsize=(14, 8), facecolor=facecolor)
    ax.set_facecolor(facecolor)

    x = np.arange(len(valid_months))

    ax.plot(x, valid_vegas, marker='o', markersize=7, linewidth=2.5,
            color='#d62728', label='Las Vegas Strip', zorder=3)
    ax.plot(x, valid_reno, marker='s', markersize=7, linewidth=2.5,
            color='#1f77b4', label='Reno', zorder=3)

    # Shade the delta between the two lines
    ax.fill_between(x, valid_vegas, valid_reno, alpha=0.12, color='#999999')

    # Short month labels for x-axis
    short_months = []
    for m in valid_months:
        parts = m.split()
        short_months.append(parts[0][:3] if len(parts) >= 1 else m)

    ax.set_xticks(x)
    ax.set_xticklabels(short_months, fontsize=11, color=text_color)
    ax.set_ylabel('Total Slot Win %', fontsize=13, color=text_color,
                   fontweight='bold', fontstyle='italic')
    ax.set_xlabel('')

    ax.set_title('Las Vegas Strip vs Reno - Total Slot Win %',
                 fontsize=16, color=text_color, fontweight='bold', pad=15)

    # Grid
    ax.grid(True, axis='both', alpha=0.4, linewidth=0.8, color='#CCCCCC')
    ax.set_axisbelow(True)

    # Y-axis range with padding
    all_vals = valid_vegas + valid_reno
    y_min = min(all_vals)
    y_max = max(all_vals)
    padding = (y_max - y_min) * 0.2
    ax.set_ylim(y_min - padding, y_max + padding)

    # Legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9, edgecolor='#999999')

    # Info box: average delta
    avg_v = sum(valid_vegas) / len(valid_vegas)
    avg_r = sum(valid_reno) / len(valid_reno)
    avg_delta = avg_v - avg_r
    if avg_delta > 0:
        looser = "Reno"
    elif avg_delta < 0:
        looser = "Las Vegas Strip"
    else:
        looser = "Tied"

    info_lines = [
        f"Avg LV Strip: {avg_v:.2f}%",
        f"Avg Reno: {avg_r:.2f}%",
        f"Avg Delta: {avg_delta:+.2f}%",
        f"Looser: {looser}",
        f"Months: {len(valid_months)}",
    ]
    info_text = "\n".join(info_lines)
    ax.text(0.01, 0.02, info_text, transform=ax.transAxes,
            fontsize=9, fontfamily='monospace', color=text_color,
            verticalalignment='bottom',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                      edgecolor='#999999', alpha=0.9))

    # Annotate each point with delta
    for i in range(len(valid_months)):
        delta = valid_vegas[i] - valid_reno[i]
        mid_y = (valid_vegas[i] + valid_reno[i]) / 2
        ax.annotate(f'{delta:+.1f}%', xy=(i, mid_y),
                    fontsize=8, color='#666666', ha='center',
                    fontweight='bold')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(colors=text_color, labelsize=10)

    plt.tight_layout()
    plt.savefig(output_dir + fn_chart, facecolor=facecolor, dpi=150, bbox_inches='tight')
    tprint(f"✓ Chart saved to: {output_dir}{fn_chart}")
    plt.close()

elif len(valid_months) == 1:
    # ── Single-month grouped bar chart ──
    tprint("\nGenerating Vegas vs Reno comparison chart...")

    # Get per-denomination data from the single file
    single_data = chart_denom_data[0] if chart_denom_data else {}
    vegas_data = single_data.get('Las Vegas Strip', {})
    reno_data = single_data.get('Reno', {})

    # Collect denominations present in both
    common_denoms = [d for d in denom_order if d in vegas_data and d in reno_data]
    common_denoms.append('Total Slots')

    if common_denoms:
        fig, ax = plt.subplots(figsize=(14, 8), facecolor=facecolor)
        ax.set_facecolor(facecolor)

        x = np.arange(len(common_denoms))
        width = 0.35

        vegas_vals = [vegas_data[d][0] for d in common_denoms]
        reno_vals = [reno_data[d][0] for d in common_denoms]

        bars1 = ax.bar(x - width/2, vegas_vals, width, label='Las Vegas Strip',
                       color='#d62728', alpha=0.85, zorder=3)
        bars2 = ax.bar(x + width/2, reno_vals, width, label='Reno',
                       color='#1f77b4', alpha=0.85, zorder=3)

        # Value labels on bars
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                    f'{height:.2f}%', ha='center', va='bottom',
                    fontsize=8, color='#d62728', fontweight='bold')
        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                    f'{height:.2f}%', ha='center', va='bottom',
                    fontsize=8, color='#1f77b4', fontweight='bold')

        short_labels = [d.replace(' Denomination', '').replace(' Dollars', ' Dollar')
                        for d in common_denoms]
        short_labels = ['TOTAL' if d == 'Total Slots' else d for d in short_labels]

        ax.set_xticks(x)
        ax.set_xticklabels(short_labels, fontsize=10, color=text_color, rotation=30, ha='right')
        ax.set_ylabel('Win %', fontsize=13, color=text_color,
                       fontweight='bold', fontstyle='italic')

        ax.set_title(f'Las Vegas Strip vs Reno - {valid_months[0]}',
                     fontsize=16, color=text_color, fontweight='bold', pad=15)

        ax.grid(True, axis='y', alpha=0.4, linewidth=0.8, color='#CCCCCC')
        ax.set_axisbelow(True)
        ax.legend(loc='upper right', fontsize=11, framealpha=0.9, edgecolor='#999999')

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(colors=text_color, labelsize=10)

        plt.tight_layout()
        plt.savefig(output_dir + fn_chart, facecolor=facecolor, dpi=150, bbox_inches='tight')
        tprint(f"✓ Chart saved to: {output_dir}{fn_chart}")
        plt.close()
else:
    tprint("\n⚠ Not enough data for chart generation")

# ────────────────────────────────────────────────
# SAVE TEXT SUMMARY
# ────────────────────────────────────────────────
fn_summary = "NV_win_pct_vegas_vs_reno.txt"
with open(output_dir + fn_summary, 'w') as f:
    f.write('\n'.join(all_output))

tprint("=" * 80)
tprint("PROCESSING COMPLETE!")
tprint("=" * 80)
tprint(f"✓ Summary saved to: {output_dir}{fn_summary}")
tprint(f"✓ Chart saved to: {output_dir}{fn_chart}")
tprint(f"✓ Files processed: {len(pdf_files)}")
tprint("=" * 80)
