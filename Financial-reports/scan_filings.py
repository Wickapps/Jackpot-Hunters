#!/usr/bin/env python3
"""Offline scanner: search downloaded SEC filings for jackpot-related disclosures."""

import argparse, re, sys
from pathlib import Path
from bs4 import BeautifulSoup

# Built-in search phrases (case-insensitive)
KEYWORDS = [
  "progressive jackpot liability",
  "progressive jackpot",
  "jackpot liability",
  "accrued jackpot",
  "accrued progressive",
  "progressive liability",
  "jackpot win",
  "large payout",
  "significant payout",
  "hold percentage",
  "gaming win",
  "slot revenue",
]

# Regex for dollar amounts: $1.2 million, $1,234,567, $12.3 billion, etc.
DOLLAR_RE = re.compile(
  r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|thousand))?',
  re.IGNORECASE
)

CONTEXT_CHARS = 300  # characters of context around each match

def extract_text(filepath):
  """Read a filing file and return plain text via BeautifulSoup."""
  with open(filepath, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()
  soup = BeautifulSoup(raw, "lxml")
  # Remove script/style tags
  for tag in soup(["script", "style"]):
    tag.decompose()
  text = soup.get_text(separator=" ", strip=True)
  # Collapse whitespace
  text = re.sub(r'\s+', ' ', text)
  return text

def find_matches(text, keywords):
  """Search text for keyword phrases. Return list of (keyword, start, context, dollars)."""
  lower = text.lower()
  results = []
  seen_positions = set()
  for kw in keywords:
    start = 0
    while True:
      idx = lower.find(kw.lower(), start)
      if idx == -1:
        break
      # Skip if we already reported a match within 100 chars of this position
      bucket = idx // 100
      if bucket in seen_positions:
        start = idx + len(kw)
        continue
      seen_positions.add(bucket)
      # Extract context window
      ctx_start = max(0, idx - CONTEXT_CHARS // 2)
      ctx_end = min(len(text), idx + len(kw) + CONTEXT_CHARS // 2)
      context = text[ctx_start:ctx_end]
      if ctx_start > 0:
        context = "..." + context
      if ctx_end < len(text):
        context = context + "..."
      # Find dollar amounts in the context window
      dollars = DOLLAR_RE.findall(context)
      results.append((kw, idx, context, dollars))
      start = idx + len(kw)
  return results

def parse_filing_path(filepath):
  """Extract ticker, form type, and accession from the directory structure.
  Expected: .../sec-edgar-filings/TICKER/FORM/ACCESSION/full-submission.txt"""
  parts = filepath.parts
  try:
    idx = parts.index("sec-edgar-filings")
    ticker = parts[idx + 1] if idx + 1 < len(parts) else "?"
    form = parts[idx + 2] if idx + 2 < len(parts) else "?"
    accession = parts[idx + 3] if idx + 3 < len(parts) else "?"
    return ticker, form, accession
  except (ValueError, IndexError):
    return "?", "?", filepath.stem

def scan_directory(base_dir, keywords):
  """Walk directory tree, find filing files, scan each one."""
  base = Path(base_dir)
  if not base.exists():
    print(f"ERROR: Directory not found: {base}", file=sys.stderr)
    sys.exit(1)

  # Find all full-submission.txt files, plus any .htm/.html files
  filing_files = sorted(base.rglob("full-submission.txt"))
  if not filing_files:
    # Fallback: look for any HTML files
    filing_files = sorted(base.rglob("*.htm")) + sorted(base.rglob("*.html"))
  if not filing_files:
    print(f"No filing files found in {base}", file=sys.stderr)
    sys.exit(1)

  total_filings = 0
  total_matches = 0
  operator_stats = {}

  for fp in filing_files:
    ticker, form, accession = parse_filing_path(fp)
    print(f"\n{'='*60}")
    print(f"  {ticker} | {form} | {accession}")
    print(f"  {fp}")
    print(f"{'='*60}")

    try:
      text = extract_text(fp)
    except Exception as e:
      print(f"  ERROR reading file: {e}", file=sys.stderr)
      continue

    total_filings += 1
    matches = find_matches(text, keywords)

    if not matches:
      print("  (no keyword matches)")
      continue

    total_matches += len(matches)
    key = ticker
    if key not in operator_stats:
      operator_stats[key] = {"filings": 0, "matches": 0, "dollars": []}
    operator_stats[key]["filings"] += 1
    operator_stats[key]["matches"] += len(matches)

    for kw, pos, context, dollars in matches:
      print(f"\n  [{kw}]")
      # Word-wrap the context for readability
      wrapped = wrap_text(context, indent=4, width=76)
      print(wrapped)
      if dollars:
        operator_stats[key]["dollars"].extend(dollars)
        print(f"    Amounts found: {', '.join(dollars)}")

  # Summary
  print(f"\n{'━'*60}")
  print(f"  SUMMARY")
  print(f"{'━'*60}")
  print(f"  Filings scanned: {total_filings}")
  print(f"  Total matches:   {total_matches}")
  if operator_stats:
    print()
    for op, stats in sorted(operator_stats.items()):
      print(f"  {op}: {stats['filings']} filing(s), {stats['matches']} match(es)")
      if stats["dollars"]:
        unique = sorted(set(stats["dollars"]))
        print(f"    Dollar amounts: {', '.join(unique[:10])}")
        if len(unique) > 10:
          print(f"    ... and {len(unique)-10} more")
  print(f"{'━'*60}")

def wrap_text(text, indent=4, width=76):
  """Simple word-wrap with indent."""
  prefix = " " * indent
  words = text.split()
  lines = []
  current = prefix + '"'
  for word in words:
    if len(current) + len(word) + 1 > width:
      lines.append(current)
      current = prefix + word
    else:
      current += " " + word if current.strip() else prefix + word
  current += '"'
  lines.append(current)
  return "\n".join(lines)

def main():
  default_dir = str(Path(__file__).parent / "sec-edgar-filings")

  ap = argparse.ArgumentParser(
    description="Scan downloaded SEC filings for jackpot-related disclosures"
  )
  ap.add_argument("--dir", default=default_dir,
                   help=f"Directory containing downloaded filings (default: {default_dir})")
  ap.add_argument("--keywords", nargs="+", default=[],
                   help="Additional keywords to search for (added to built-in list)")
  ap.add_argument("--list-keywords", action="store_true",
                   help="Print the built-in keyword list and exit")
  args = ap.parse_args()

  if args.list_keywords:
    print("Built-in search keywords:")
    for kw in KEYWORDS:
      print(f"  - {kw}")
    sys.exit(0)

  keywords = KEYWORDS + args.keywords
  print(f"Scanning: {args.dir}")
  print(f"Keywords: {len(keywords)} phrases")
  scan_directory(args.dir, keywords)

if __name__ == "__main__":
  main()
