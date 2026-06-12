"""
Nevada Gaming Monthly Overview - Jackpot Hunter's Intelligence Report

Parses Nevada Gaming Control Board monthly PDF reports to extract and summarize
key gaming metrics useful for slot hunters and advantage players.

Lower Win% = More player-friendly = Better opportunities

Copyright (c) 2025 Mark Wickham
License: MIT
Released with: The Jackpot Hunters Guide to Slot Machines - A Data-Driven Field Manual

Usage:
    python NV_overview.py <input_pdf> [--output-dir DIR]

Example:
    python NV_overview.py docs/NV_2025_01.pdf
    python NV_overview.py docs/NV_2025_01.pdf --output-dir reports/
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

# Suppress noisy warnings
logging.getLogger('tabula').setLevel(logging.ERROR)

pd.set_option('display.max_rows', 50)
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 150)

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
    description='Generate Nevada Gaming Monthly Overview for Jackpot Hunters'
)
parser.add_argument('input_file', help='Path to Nevada Gaming monthly PDF file')
parser.add_argument('--output-dir', default='output/',
                    help='Output directory for reports (default: output/)')

args = parser.parse_args()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
input_path = args.input_file
output_dir = args.output_dir
if output_dir and not output_dir.endswith('/'):
    output_dir += '/'

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Get base filename and generate output filename
base_name = os.path.splitext(os.path.basename(input_path))[0]
fn_summary = f"{base_name}_overview.txt"

# ────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────
tprint("=" * 80)
tprint("NEVADA GAMING MONTHLY OVERVIEW - JACKPOT HUNTER'S INTELLIGENCE REPORT")
tprint("=" * 80)
tprint(f"Input file: {input_path}")
tprint(f"Output directory: {output_dir}")
tprint(f"Report file: {output_dir}{fn_summary}")
tprint(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
tprint("=" * 80 + "\n")

# ────────────────────────────────────────────────
# EXTRACT ALL TABLES FROM PDF
# ────────────────────────────────────────────────
tprint("Extracting gaming data from Nevada monthly report...\n")

try:
    # Use stream mode which handles Nevada PDFs better
    tables = tabula.read_pdf(
        input_path,
        pages='all',
        multiple_tables=True,
        stream=True,
        guess=True,
        pandas_options={'header': None},
        java_options=["-Xmx4g"],
        silent=True
    )
    # Filter out tiny tables (likely parsing artifacts)
    tables = [t for t in tables if t.shape[0] > 10 and t.shape[1] >= 3]
    tprint(f"✓ Extracted {len(tables)} tables from PDF\n")
except Exception as e:
    tprint(f"✗ Error extracting tables: {e}")
    exit(1)

if not tables:
    tprint("✗ No tables found in PDF")
    exit(1)

# ────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ────────────────────────────────────────────────

def clean_number(val):
    """Clean and convert numeric values from PDF tables"""
    if pd.isna(val):
        return None
    val_str = str(val).strip().replace(',', '').replace('$', '').replace('%', '')
    val_str = re.sub(r'[^\d.-]', '', val_str)
    try:
        return float(val_str)
    except:
        return None

def extract_month_year(tables):
    """Extract month and year from table headers"""
    # Check first 10 tables for date information
    for table in tables[:10]:
        if len(table) == 0:
            continue
        # Check all cells in first few rows
        for row_idx in range(min(5, len(table))):
            for col_idx in range(min(5, table.shape[1])):
                cell_text = str(table.iloc[row_idx, col_idx])
                # Look for patterns like "January-2025" or "January 2025"
                match = re.search(
                    r'(January|February|March|April|May|June|July|August|September|October|November|December)[-\s]*(\d{4})',
                    cell_text
                )
                if match:
                    return match.group(1), match.group(2)
    return None, None

def find_statewide_table(tables):
    """Find the main statewide all locations table"""
    for idx, table in enumerate(tables):
        # Check if table has reasonable size (need at least 25 rows for full gaming data)
        if table.shape[0] < 25:
            continue

        # Check the first column header (stream mode puts everything in col 0)
        header_text = str(table.iloc[0, 0])
        if 'Statewide' in header_text and 'All Nonrestricted' in header_text:
            return idx, table
    return None, None

def parse_gaming_table_multi_period(table):
    """Parse gaming table and extract all three time periods.

    Observed NGCB stream-mode layout (8 columns) for the statewide table:
      Col 0: Current month - "1 Cent 286 27,059 119,456 (25.39)"
             (denomination, # locations, # units, win amount, % change)
      Col 1: NaN
      Col 2: Current-month Win %   -> "8.71"
      Col 3: 3-Month # locations   -> "288"
      Col 4: 3-Month data          -> "27,624 369,111 (23.71) 8.88"
             (# units, win amount, % change, win %)
      Col 5: NaN
      Col 6: 12-Month # locations  -> "294"
      Col 7: 12-Month data         -> "29,433 1,585,702 (26.35) 8.87"

    IMPORTANT: the win % for each period lives in its own column - it is NOT the
    last number in the col-0 description. That trailing parenthesised value is the
    month-over-month % CHANGE. Earlier versions of this parser mistook it for the
    win %, reporting (e.g.) 25.39% for 1-cent slots instead of the true 8.71%.
    """
    ncols = table.shape[1]
    slot_patterns = ['Cent', 'Dollar', 'Multi Denomination', 'Megabucks']

    def find_slot_start(name_col):
        for idx in range(len(table)):
            if 'Slot Machine' in str(table.iloc[idx, name_col]):
                return idx + 1
        return None

    def split_denom(row_text):
        """Split a col-0 description into (denom_name, [number strings])."""
        denom_match = re.match(
            r'^([\d]+\s+Cent|[\d]+\s+Dollar|[\d]+\s+Dollars|Multi\s+Denomination|Megabucks|Other)\s+',
            row_text
        )
        if denom_match:
            denom_name = denom_match.group(1)
            return denom_name, row_text[len(denom_name):].strip().split()
        parts = row_text.split()
        for i, part in enumerate(parts):
            if re.search(r'^\(?\d', part):
                return (" ".join(parts[:i]) or "Other"), parts[i:]
        return "Other", []

    def to_nums(values):
        nums = []
        for v in values:
            n = clean_number(v)
            if n is not None:
                nums.append(abs(n))
        return nums

    def parse_period(name_col, win_col=None, loc_col=None, data_col=None):
        """Parse slot data for one time period.

        Current month: loc/units lead col 0, win % read from win_col.
        3/12-month:    loc read from loc_col, units + win % from data_col.
        """
        data = []
        start = find_slot_start(name_col)
        if start is None:
            return pd.DataFrame()

        for idx in range(start, len(table)):
            row = table.iloc[idx]
            row_text = str(row.iloc[name_col]).strip()

            if ('Total Gaming' in row_text or 'Race Book' in row_text or
                    '***' in row_text or row_text in ('', 'nan')):
                break
            if row_text.startswith('Total ') or row_text == 'Total':
                continue
            if not any(pattern in row_text for pattern in slot_patterns):
                continue

            denom_name, col0_numbers = split_denom(row_text)

            locations = units = win_pct = None
            if loc_col is not None and data_col is not None:
                # 3-month / 12-month: locations in own column, data column holds
                # [units, win amount, % change, win %]
                locations = clean_number(row.iloc[loc_col])
                if locations is not None:
                    locations = abs(locations)
                data_text = str(row.iloc[data_col]).strip()
                data_nums = to_nums(data_text.split()) if data_text != 'nan' else []
                if data_nums:
                    units = data_nums[0]
                    win_pct = data_nums[-1]
            else:
                # Current month: [# loc, # units, win amount, % change] in col 0,
                # win % in win_col
                col0_nums = to_nums(col0_numbers)
                if len(col0_nums) >= 2:
                    locations, units = col0_nums[0], col0_nums[1]
                elif col0_nums:
                    units = col0_nums[0]
                if win_col is not None:
                    win_pct = clean_number(row.iloc[win_col])
                elif col0_nums:
                    win_pct = col0_nums[-1]

            if win_pct is not None and 0 < win_pct < 50:
                data.append({
                    'Unit': denom_name,
                    'Locations': locations,
                    'Units': units,
                    'Win_Pct': win_pct
                })

        return pd.DataFrame(data)

    current_month = parse_period(0, win_col=2) if ncols > 2 else parse_period(0)
    three_month = parse_period(0, loc_col=3, data_col=4) if ncols > 4 else pd.DataFrame()
    twelve_month = parse_period(0, loc_col=6, data_col=7) if ncols > 7 else pd.DataFrame()

    return current_month, three_month, twelve_month

# ────────────────────────────────────────────────
# PARSE MONTHLY DATA
# ────────────────────────────────────────────────

month, year = extract_month_year(tables)
if month and year:
    tprint(f"Report Period: {month} {year}\n")
else:
    tprint("Report Period: Unable to determine from PDF\n")

# Find and parse statewide data
statewide_idx, statewide_table = find_statewide_table(tables)

if statewide_table is not None:
    tprint(f"Found statewide summary at table index {statewide_idx}")
    tprint(f"Table shape: {statewide_table.shape}\n")

# ────────────────────────────────────────────────
# BUILD COMPREHENSIVE SUMMARY
# ────────────────────────────────────────────────

summary_lines = []

summary_lines.append("=" * 80)
summary_lines.append("NEVADA GAMING MONTHLY OVERVIEW - JACKPOT HUNTER'S INTELLIGENCE")
summary_lines.append("=" * 80)
summary_lines.append(f"\nReport Period: {month} {year}" if month else "\nReport Period: Unknown")
summary_lines.append(f"Source: {os.path.basename(input_path)}")
summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

summary_lines.append("\n" + "=" * 80)
summary_lines.append("EXECUTIVE SUMMARY")
summary_lines.append("=" * 80)
summary_lines.append(f"\n✓ Total Tables Extracted: {len(tables)}")
summary_lines.append(f"✓ Data Covers: Statewide and regional gaming performance")
summary_lines.append(f"✓ Analysis Focus: Slot machine win percentages and player value")

# Extract key statewide metrics
summary_lines.append("\n" + "-" * 80)
summary_lines.append("STATEWIDE PERFORMANCE SNAPSHOT")
summary_lines.append("-" * 80)

if statewide_table is not None:
    # Try to extract total licensees
    for idx in range(min(5, len(statewide_table))):
        row_text = str(statewide_table.iloc[idx, 0])
        if 'Licensees' in row_text or 'Number of Reporting' in row_text:
            licensee_match = re.search(r'(\d+)', row_text)
            if licensee_match:
                summary_lines.append(f"Number of Reporting Locations: {licensee_match.group(1)}")

    # Parse game unit data for all three time periods
    current_month, three_month, twelve_month = parse_gaming_table_multi_period(statewide_table)

    def format_slot_table(data, period_name):
        """Helper to format a slot machine summary table"""
        lines = []
        if not data.empty:
            lines.append(f"\n{'=' * 80}")
            lines.append(f"SLOT MACHINE WIN PERCENTAGES - {period_name}")
            lines.append("=" * 80)

            # Show summary stats
            units_data = data[data['Units'].notna()]
            if not units_data.empty:
                total_units = units_data['Units'].sum()
                lines.append(f"Total Units: {int(total_units):,} | Categories: {len(data)}")

            lines.append(f"\n{'Game Type':<30} {'Locs':>6} {'Units':>8} {'Win %':>10} {'Rating':<20}")
            lines.append("-" * 80)

            # Sort by win percentage (lowest = best for players)
            data_sorted = data[data['Win_Pct'].notna()].sort_values('Win_Pct')

            for _, row in data_sorted.iterrows():
                unit = row['Unit'][:28]
                win_pct = row['Win_Pct']
                units = row['Units'] if pd.notna(row['Units']) else 0
                locs = row['Locations'] if pd.notna(row['Locations']) else 0

                # Rating system for jackpot hunters
                if win_pct < 5.0:
                    rating = "⭐⭐⭐ Excellent"
                elif win_pct < 7.0:
                    rating = "⭐⭐ Very Good"
                elif win_pct < 10.0:
                    rating = "⭐ Good"
                else:
                    rating = "Average"

                locs_str = f"{int(locs)}" if locs > 0 else "-"
                units_str = f"{int(units):,}" if units > 0 else "-"
                lines.append(f"{unit:<30} {locs_str:>6} {units_str:>8} {win_pct:>9.2f}% {rating:<20}")
        else:
            lines.append(f"\n⚠ Unable to parse {period_name} data")

        return lines

    # Add all three period summaries
    if not current_month.empty:
        summary_lines.extend(format_slot_table(current_month, "CURRENT MONTH"))

    if not three_month.empty:
        summary_lines.extend(format_slot_table(three_month, "THREE MONTH AVERAGE"))

    if not twelve_month.empty:
        summary_lines.extend(format_slot_table(twelve_month, "TWELVE MONTH AVERAGE"))

    if current_month.empty and three_month.empty and twelve_month.empty:
        summary_lines.append("\n⚠ Unable to parse gaming data from statewide table")
        summary_lines.append("  Raw table structure may need manual review")
else:
    summary_lines.append("\n⚠ Statewide summary table not found")

# ────────────────────────────────────────────────
# REGIONAL ANALYSIS
# ────────────────────────────────────────────────

summary_lines.append("\n" + "=" * 80)
summary_lines.append("REGIONAL BREAKDOWN")
summary_lines.append("=" * 80)

# Extract region names from tables
regions_found = []
for idx, table in enumerate(tables[1:20]):  # Check first 20 tables
    for col in table.columns:
        header = str(table[col].iloc[0] if len(table) > 0 else '')
        # Look for area names
        if 'Area' in header or 'Las Vegas' in header or 'Reno' in header or 'Lake Tahoe' in header:
            region_name = header.split('-')[0].strip() if '-' in header else header.strip()
            if region_name and region_name not in regions_found and len(region_name) < 50:
                regions_found.append(region_name)

if regions_found:
    summary_lines.append(f"\nRegions Covered in Report: {len(regions_found)}")
    for region in regions_found[:15]:  # Show first 15 regions
        summary_lines.append(f"  • {region}")
else:
    summary_lines.append("\nRegional data breakdown available in detailed tables")

# ────────────────────────────────────────────────
# KEY INSIGHTS FOR JACKPOT HUNTERS
# ────────────────────────────────────────────────

summary_lines.append("\n" + "=" * 80)
summary_lines.append("KEY INSIGHTS FOR JACKPOT HUNTERS")
summary_lines.append("=" * 80)

summary_lines.append("\n✓ WHAT TO LOOK FOR:")
summary_lines.append("  • Lower win % = Better player odds = More favorable conditions")
summary_lines.append("  • Win % below 8% indicates player-friendly slots")
summary_lines.append("  • Compare current month to 12-month average for trends")
summary_lines.append("  • Higher denomination games often have lower hold percentages")

summary_lines.append("\n✓ ANALYSIS METHODOLOGY:")
summary_lines.append("  • Data source: Nevada Gaming Control Board official reports")
summary_lines.append("  • Win % = (Casino Win / Total Coin In) × 100")
summary_lines.append("  • Lower percentage = higher player return")
summary_lines.append("  • Focus on game types with consistent low win rates")

summary_lines.append("\n✓ NEXT STEPS:")
summary_lines.append("  • Use drill-down scripts to analyze specific regions")
summary_lines.append("  • Compare month-over-month trends")
summary_lines.append("  • Identify locations with declining win percentages")
summary_lines.append("  • Cross-reference with progressive jackpot data")

summary_lines.append("\n" + "=" * 80)
summary_lines.append("TABLE INVENTORY")
summary_lines.append("=" * 80)
summary_lines.append(f"\nTotal tables extracted: {len(tables)}")
summary_lines.append("\nTable Summary:")
for idx, table in enumerate(tables):  # Show all tables
    table_name = "Unknown"
    if len(table) > 0:
        first_col = str(table.iloc[0, 0])[:60]
        table_name = first_col if first_col != 'nan' else f"Table {idx+1}"
    summary_lines.append(f"  {idx+1:3d}. {table_name:<60} Shape: {table.shape}")

summary_lines.append("\n" + "=" * 80)
summary_lines.append("END OF OVERVIEW REPORT")
summary_lines.append("=" * 80)

# ────────────────────────────────────────────────
# OUTPUT RESULTS
# ────────────────────────────────────────────────

# Print to console
summary_text = "\n".join(summary_lines)
tprint("\n" + summary_text)

# Save to file
with open(output_dir + fn_summary, 'w') as f:
    f.write('\n'.join(all_output))

tprint(f"\n{'=' * 80}")
tprint("PROCESSING COMPLETE!")
tprint("=" * 80)
tprint(f"✓ Overview report saved to: {output_dir}{fn_summary}")
tprint(f"✓ Total tables processed: {len(tables)}")
tprint(f"✓ Ready for drill-down analysis")
tprint("=" * 80)
