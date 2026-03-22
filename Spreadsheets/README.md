# Session Tracking Spreadsheets

Three Excel spreadsheets for **logging and analyzing your own playing sessions** — as described in the book. No macros or special software required beyond Excel or a compatible spreadsheet application (Google Sheets, LibreOffice Calc).

---

## `Session-Entry-v2.xlsx`

The primary session tracker. Records up to 8 casino visits side-by-side, with spin-by-spin entry and automatic summary statistics calculated across the top.

### Summary rows (top section — auto-calculated)

| Field | Description |
| --- | --- |
| **Investment** | Total credits put in for the session (e.g. $100) |
| **Per Play** | Bet size per spin in credits |
| **Start Credits** | Starting credit balance |
| **Final Credits** | Credit balance at end of session |
| **ROI** | Return on investment (Final / Investment) |
| **Profit** | Net profit or loss in credits |
| **Plays** | Total number of spins played |
| **Hits** | Number of winning spins |
| **Hit Rate** | Hits / Plays — fraction of spins that paid |
| **Avg Hit Multiplier** | Average win size expressed as a multiplier of the base bet |

A **Total** column on the right aggregates all visits automatically.

### Spin-by-spin data (lower section — manual entry)

For each spin, enter one row:

| Column | Description |
| --- | --- |
| **Play #** | Spin number within the session |
| **Credits** | Credit balance after that spin |
| **Hit** | Win amount (multiplier) if the spin was a winner — leave blank for losses |

### How to use

1. Set **Investment**, **Per Play**, and **Start Credits** in the summary rows for each visit column
2. After each spin, add a row with the play number, new credit balance, and hit multiplier (if any)
3. The summary statistics update automatically as you enter data
4. Move to the next visit column when you start a new casino session

---

## `Hit-Multiplier-v1.xlsx`

A spin-by-spin hit frequency log for capturing **hit multiplier patterns** across multiple sessions over time. Designed for long-term tracking — the running Total Spins counter never resets, letting you build up a dataset across many visits.

### Columns

| Column | Description |
| --- | --- |
| **Total Spins** | Running spin count across all sessions combined |
| **Session Spins** | Spin number within the current session (resets each visit) |
| **Session** | Session number — increment this when starting a new visit |
| **Credits** | Credit balance after that spin |
| **Hit Multiplier** | Win amount as a multiplier of the base bet — enter `0` for no win |

### How to use

1. Start a new row for every spin
2. Increment the **Session** number each time you begin a new casino visit — **Session Spins** resets to 1, but **Total Spins** keeps counting
3. Enter `0` in **Hit Multiplier** for non-winning spins and the actual multiplier (e.g. `9`, `38`) for wins
4. Over time the dataset reveals how frequently wins occur and what the typical win size looks like relative to the base bet

---

## `Stepper-Graph-Example-v2.xlsx`

A single-session credit balance chart used to visualize the **stepper pattern** — the characteristic step-down-then-jump credit curve the book uses to identify machine behavior. Includes an embedded chart that updates automatically as you enter data.

### Columns

| Column | Description |
| --- | --- |
| **Play #** | Spin number within the session |
| **Credits** | Credit balance after that spin |
| **Hits** | Win amount (multiplier) for winning spins — leave blank for losses |

### How to use

1. Enter your starting credit balance in the first row (Play # blank, Credits = starting balance)
2. Add one row per spin — credit balance after each spin, and the hit multiplier for any win
3. The embedded chart updates in real time, plotting the credit balance as a continuous line with wins marked as points
4. The resulting graph shows the stepper pattern described in the book — a steady step-down between hits with upward jumps on wins

This spreadsheet is intended as a single-session tool. Start fresh (clear the data rows) at the beginning of each new session you want to chart.
