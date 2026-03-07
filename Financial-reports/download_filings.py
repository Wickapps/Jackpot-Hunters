#!/usr/bin/env python3
"""Download SEC 10-Q and 10-K filings for casino operators via EDGAR."""

import argparse, sys
from pathlib import Path
from sec_edgar_downloader import Downloader

# Pre-configured casino operators: ticker -> (CIK, display name)
OPERATORS = {
  "MGM":  ("0000789570", "MGM Resorts International"),
  "CZR":  ("0001061211", "Caesars Entertainment"),
  "PENN": ("0000921738", "Penn Entertainment"),
}

FORMS = ["10-Q", "10-K"]
DEFAULT_AFTER = "2023-01-01"

def download(operators, after, download_dir):
  dl = Downloader("JackpotHunter", "jackpothunter@example.com", download_dir)
  total = 0
  for ticker in operators:
    cik, name = OPERATORS[ticker]
    print(f"\n{'='*50}")
    print(f"  {name} ({ticker} / CIK {cik})")
    print(f"{'='*50}")
    for form in FORMS:
      try:
        count = dl.get(form, ticker, after=after)
        total += count
        print(f"  {form}: {count} filing(s) downloaded")
      except Exception as e:
        print(f"  {form}: ERROR - {e}", file=sys.stderr)
  return total

def main():
  ap = argparse.ArgumentParser(description="Download SEC filings for casino operators")
  ap.add_argument("--operators", nargs="+", default=list(OPERATORS.keys()),
                   choices=list(OPERATORS.keys()),
                   help="Operator tickers to download (default: all)")
  ap.add_argument("--after", default=DEFAULT_AFTER,
                   help=f"Download filings after this date YYYY-MM-DD (default: {DEFAULT_AFTER})")
  ap.add_argument("--dir", default=str(Path(__file__).parent),
                   help="Download directory (default: scripts/)")
  args = ap.parse_args()

  print(f"Downloading filings after {args.after}")
  print(f"Operators: {', '.join(args.operators)}")
  print(f"Save to: {args.dir}")

  total = download(args.operators, args.after, args.dir)
  print(f"\n{'─'*50}")
  print(f"Done. {total} total filing(s) downloaded.")

if __name__ == "__main__":
  main()
