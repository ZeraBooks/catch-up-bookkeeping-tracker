"""Write every file in samples/ from the monthly figures below.

Run from the repository root:  python3 scripts/generate_samples.py
Each statement's closing is its opening plus that month's net change, and each
opening is the previous closing, so every chain adds up by construction.
All businesses and figures are fictional. The output is deterministic.
"""
import csv
import json
import os
import shutil
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "samples")
COLUMNS = ["Account", "Month", "Statement received", "Printed opening", "Printed closing",
           "Imported", "Reconciled", "Books closing", "Notes"]


def months_from(start, n):
    y, m = int(start[:4]), int(start[5:7])
    out = []
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def account(name, trusted, closing, changes, missing=(), done=(), imported=(), books_off=None, note=""):
    """Rows for one account. changes = net change per month after the trusted month."""
    closing = Decimal(closing)
    rows = [[name, trusted, "Yes", "", f"{closing:.2f}", "Yes", "Yes", f"{closing:.2f}", note or "Last month you trust"]]
    months = months_from(trusted, len(changes) + 1)[1:]
    for m, ch in zip(months, changes):
        opening, closing = closing, closing + Decimal(ch)
        if m in missing:
            rows.append([name, m, "No", "", "", "No", "No", "", "Requested from the bank"])
            continue
        books = ""
        if m in done or m in imported:
            books = f"{closing:.2f}"
        if books_off and m == books_off[0]:
            books = f"{closing - Decimal(books_off[1]):.2f}"
        rows.append([name, m, "Yes", f"{opening:.2f}", f"{closing:.2f}",
                     "Yes" if (m in done or m in imported) else "No", "Yes" if m in done else "No", books, ""])
    return rows


def write(rel, rows):
    path = os.path.join(S, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(COLUMNS)
        w.writerows(rows)


def main():
    # 1. Halden Bike Repair: the README example, same file as the root tracker.
    os.makedirs(os.path.join(S, "valid"), exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "catch-up-tracker.csv"), os.path.join(S, "valid", "halden-bike-repair.csv"))

    # 2. Juniper Lane Florist: 11 months behind, two months in a row missing on checking,
    #    and August reconciled by a previous helper before July was done.
    juniper = account("Checking 3318", "2025-11", "18240.55",
                      ["1215.40", "-2904.12", "3387.06", "-1140.75", "2602.33", "-415.90",
                       "1978.44", "-3206.81", "2511.07", "-688.29", "1044.63"],
                      missing=("2026-03", "2026-04"), done=("2025-12", "2026-01", "2026-02", "2026-08"))
    juniper += account("Visa 7702", "2025-11", "4118.20",
                       ["-612.45", "877.30", "-1020.18", "455.62", "-301.07", "689.94",
                        "-244.51", "512.36", "-870.40", "330.15", "-198.02"],
                       done=("2025-12", "2026-01"), imported=("2026-02",),
                       note="Last month you trust. Card balances are amounts owed")
    write("valid/juniper-lane-florist.csv", juniper)

    # 3. Pinecrest Tutoring: caught up. Every month ties.
    write("valid/pinecrest-tutoring.csv",
          account("Checking 0571", "2026-06", "6402.18", ["812.40", "-1245.09", "1530.77"],
                  done=("2026-07", "2026-08", "2026-09")))

    # 4. Brook and Vale Cafe: the "trusted" month doesn't tie, so it's a cleanup first.
    brook = account("Checking 9044", "2026-03", "9870.12", ["-1302.55", "2210.08", "-640.31"])
    brook[0][6] = "No"
    brook[0][7] = "9412.12"
    brook[0][8] = "Owner thought March was right"
    write("valid/brook-and-vale-cafe.csv", brook)

    # Invalid trackers: each breaks one rule.
    base = account("Checking 1100", "2026-05", "5000.00", ["250.00", "-120.50", "310.25"], done=("2026-06",))
    expected = {}

    def bad(name, rows, rule, header=None):
        path = os.path.join(S, "invalid", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(header or COLUMNS)
            w.writerows(rows)
        expected[name] = rule

    bad("missing-books-closing-column.csv", [r[:7] + r[8:] for r in base], "CU-001",
        header=[c for c in COLUMNS if c != "Books closing"])
    r = [list(x) for x in base]
    r[2][1] = "Jul 2026"
    bad("month-not-yyyy-mm.csv", r, "CU-002")
    r = [list(x) for x in base] + [list(base[2])]
    bad("same-month-twice.csv", r, "CU-002")
    r = [list(x) for x in base]
    r[1][6] = "Y"
    bad("yes-no-typo.csv", r, "CU-003")
    r = [list(x) for x in base]
    r[2][3] = ""
    bad("received-without-opening.csv", r, "CU-004")
    r = [list(x) for x in base]
    r[1][4] = "$5,250.00"
    bad("dollar-sign-in-balance.csv", r, "CU-005")
    r = [list(x) for x in base]
    r[1][7] = "5205.00"
    bad("reconciled-but-not-tied.csv", r, "CU-006")
    with open(os.path.join(S, "invalid", "expected.json"), "w", encoding="utf-8") as fh:
        json.dump(expected, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("samples written")


if __name__ == "__main__":
    main()
