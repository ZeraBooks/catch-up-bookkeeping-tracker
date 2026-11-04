"""Read a catch-up tracker and say what is missing, what doesn't tie and what is next.

The tracker has one row per account per month (see catch-up-tracker.csv). The
first row for each account is the last month you trust. For every account the
script:

  - lists statement months that are missing, either marked "No" under
    Statement received or not in the file at all
  - checks the chain: each statement must open where the one before closed.
    When a month is missing, the gap between the two balances is that month's
    net change, which tells you what to look for
  - lists months where the books closing doesn't equal the printed closing
  - names the next month to work on, oldest first

Usage: python3 catch_up_status.py catch-up-tracker.csv [YYYY-MM]
The optional month is the last month that should be caught up (default: the
latest month in the file).
Python 3, standard library only.
"""
import csv
import sys
from decimal import Decimal


def d(cell):
    return Decimal(cell.strip().replace(",", "")) if cell and cell.strip() else None


def yes(cell):
    return (cell or "").strip().lower() == "yes"


def next_month(m):
    y, mo = int(m[:4]), int(m[5:7])
    return f"{y + (mo == 12)}-{(mo % 12) + 1:02d}"


def main(path, through=None):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    accounts = {}
    for r in rows:
        accounts.setdefault(r["Account"].strip(), {})[r["Month"].strip()] = r
    through = through or max(r["Month"].strip() for r in rows)
    clean = True
    done = todo = 0

    for name, months in accounts.items():
        trusted = min(months)
        print(f"{name}  (last month you trust: {trusted}, closing {d(months[trusted]['Printed closing']):,.2f})")
        missing, breaks, untied = [], [], []
        prev_close, gap = d(months[trusted]["Printed closing"]), []
        next_step = None
        m = next_month(trusted)
        while m <= through:
            r = months.get(m)
            if r is None or not yes(r["Statement received"]):
                missing.append(m)
                gap.append(m)
                todo += 1
                next_step = next_step or f"get the {m} statement from the bank"
                m = next_month(m)
                continue
            opening, closing = d(r["Printed opening"]), d(r["Printed closing"])
            if prev_close is not None and opening != prev_close:
                change = opening - prev_close
                if gap:
                    breaks.append(f"{m} opens at {opening:,.2f}, {gap[-1]} is missing: its net change is {change:+,.2f}")
                else:
                    breaks.append(f"{m} opens at {opening:,.2f} but the month before closed at {prev_close:,.2f} ({change:+,.2f}). Wrong statement, or a missing one")
            gap = []
            books = d(r["Books closing"])
            if books is not None and books != closing:
                untied.append(f"{m}: statement {closing:,.2f}, books {books:,.2f}, difference {closing - books:+,.2f}")
                next_step = next_step or f"find the {closing - books:+,.2f} difference in {m}"
            if yes(r["Reconciled"]) and books == closing:
                done += 1
            else:
                todo += 1
                if not yes(r["Imported"]):
                    next_step = next_step or f"record {m} and reconcile it"
                else:
                    next_step = next_step or f"reconcile {m}"
            prev_close = closing
            m = next_month(m)

        if missing:
            clean = False
            print("  Missing statements: " + ", ".join(missing))
        for b in breaks:
            clean = False
            print("  Chain: " + b)
        for u in untied:
            clean = False
            print("  Doesn't tie: " + u)
        print(f"  Next: {next_step or 'nothing, this account is current'}")
        print()

    behind = done + todo
    print(f"{behind} account-months to catch up through {through}: {done} reconciled, {todo} to go.")
    print("Every month ties and nothing is missing." if clean and todo == 0 else "Work the list above, oldest month first.")
    return clean and todo == 0


if __name__ == "__main__":
    a = sys.argv[1:] + [None] * 2
    main(a[0] or "catch-up-tracker.csv", a[1])
    sys.exit(0)
