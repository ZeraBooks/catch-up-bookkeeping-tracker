#!/usr/bin/env python3
"""Check a catch-up bookkeeping tracker and say exactly what is left to do.

    python3 cli/catch_up_check.py tracker.csv
    python3 cli/catch_up_check.py tracker.csv --through 2026-09
    python3 cli/catch_up_check.py tracker.csv --requests statement-requests.csv
    python3 cli/catch_up_check.py tracker.csv --json

Two kinds of output, both with rule IDs from rules/tracker-rules.csv:

  errors    the tracker itself is wrong (bad month, a typo in a Yes/No cell,
            a month marked Reconciled that doesn't tie). Fix the file.
  findings  work still to do (a missing statement, a month that doesn't tie,
            a gap in the balance chain). Do the work.
  warnings  months done out of order.

Exit code 0 when the file has no errors (findings may remain; add --strict to
fail on them too), 1 when it has errors, 2 when it can't be read.

Python 3.8+, standard library only.
Part of https://github.com/ZeraBooks/catch-up-bookkeeping-tracker
(ZeraBooks, https://www.zerabooks.com/catch-up-bookkeeping).
"""
import argparse
import csv
import json
import re
import sys
from decimal import Decimal

COLUMNS = ["Account", "Month", "Statement received", "Printed opening", "Printed closing",
           "Imported", "Reconciled", "Books closing", "Notes"]
MONTH_RE = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")
AMOUNT_RE = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]{1,2})?$")
YES_NO = {"yes", "no", ""}


class Issue:
    def __init__(self, rule, severity, where, message):
        self.rule, self.severity, self.where, self.message = rule, severity, where, message

    def as_dict(self):
        return {"rule": self.rule, "severity": self.severity, "where": self.where, "message": self.message}

    def __str__(self):
        return f"{self.severity.upper():8} {self.rule} {self.where}: {self.message}"


class ReadError(Exception):
    pass


def next_month(m):
    y, mo = int(m[:4]), int(m[5:7])
    return f"{y + (mo == 12)}-{(mo % 12) + 1:02d}"


def months_between(a, b):
    """Months after a, up to and including b."""
    out, m = [], next_month(a)
    while m <= b:
        out.append(m)
        m = next_month(m)
    return out


def yes(cell):
    return (cell or "").strip().lower() == "yes"


def load(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames or []
            rows = list(reader)
    except (OSError, UnicodeDecodeError) as exc:
        raise ReadError(f"can't read {path}: {exc}")
    return header, rows


def validate(header, rows):
    """CU-001 to CU-006: is the tracker itself well formed? Returns issues and parsed accounts."""
    issues = []
    if header != COLUMNS:
        missing = [c for c in COLUMNS if c not in header]
        extra = [c for c in header if c not in COLUMNS]
        detail = (f"missing {', '.join(missing)}" if missing else "") + ("; " if missing and extra else "") + \
                 (f"unexpected {', '.join(extra)}" if extra else "")
        issues.append(Issue("CU-001", "error", "header", f"columns must be exactly: {', '.join(COLUMNS)}" +
                            (f" ({detail})" if detail else " (wrong order)")))
        return issues, {}
    accounts = {}
    for i, r in enumerate(rows, start=2):
        where = f"line {i}"
        if not any((v or "").strip() for v in r.values()):
            continue  # blank template rows
        acct, month = r["Account"].strip(), r["Month"].strip()
        if not acct:
            issues.append(Issue("CU-002", "error", where, "Account is blank"))
            continue
        if not MONTH_RE.match(month):
            issues.append(Issue("CU-002", "error", where, f"Month '{month}' must be YYYY-MM, like 2026-04"))
            continue
        if month in accounts.get(acct, {}):
            issues.append(Issue("CU-002", "error", where, f"{acct} {month} appears twice"))
            continue
        bad = [c for c in ("Statement received", "Imported", "Reconciled") if r[c].strip().lower() not in YES_NO]
        for c in bad:
            issues.append(Issue("CU-003", "error", where, f"{c} is '{r[c]}'; use Yes, No or leave it blank"))
        amounts = {}
        for c in ("Printed opening", "Printed closing", "Books closing"):
            v = r[c].strip()
            if v and not AMOUNT_RE.match(v):
                issues.append(Issue("CU-005", "error", where, f"{c} '{v}' is not a plain number like 20114.30"))
                amounts[c] = None
            else:
                amounts[c] = Decimal(v) if v else None
        first = acct not in accounts
        if yes(r["Statement received"]):
            need = ["Printed closing"] if first else ["Printed opening", "Printed closing"]
            for c in need:
                if r[c].strip() == "":
                    issues.append(Issue("CU-004", "error", where, f"the statement is marked received but {c} is blank"))
        if first and not yes(r["Statement received"]):
            issues.append(Issue("CU-004", "error", where, "the first row for an account is the last month you trust; it needs its statement and closing balance"))
        if yes(r["Reconciled"]):
            if not yes(r["Imported"]):
                issues.append(Issue("CU-006", "error", where, "marked Reconciled but not Imported"))
            elif amounts["Books closing"] is not None and amounts["Printed closing"] is not None \
                    and amounts["Books closing"] != amounts["Printed closing"]:
                issues.append(Issue("CU-006", "error", where,
                                    f"marked Reconciled, but books {amounts['Books closing']} don't equal the statement's {amounts['Printed closing']}"))
        accounts.setdefault(acct, {})[month] = {"row": r, "line": i, **amounts}
    return issues, accounts


def status(accounts, through=None):
    """CU-007 to CU-011: what is missing, what doesn't tie, and what to do next."""
    findings = []
    report = {}
    all_months = [m for a in accounts.values() for m in a]
    through = through or (max(all_months) if all_months else None)
    totals = {"account_months": 0, "reconciled": 0, "to_go": 0, "missing": 0}
    for name, months in accounts.items():
        trusted = min(months)
        t = months[trusted]
        acc = {"trusted_month": trusted, "trusted_closing": str(t["Printed closing"]), "missing": [], "gaps": [],
               "untied": [], "out_of_order": [], "reconciled": 0, "to_go": 0, "next": None, "cleanup": False}
        if t["Books closing"] is not None and t["Printed closing"] is not None and t["Books closing"] != t["Printed closing"]:
            diff = t["Printed closing"] - t["Books closing"]
            acc["cleanup"] = True
            findings.append(Issue("CU-010", "finding", f"{name} {trusted}",
                                  f"the month you trust doesn't tie: books {t['Books closing']}, statement {t['Printed closing']} "
                                  f"(books {abs(diff)} {'below' if diff > 0 else 'above'} the bank). Pick an earlier month that ties, "
                                  "or treat this account as a cleanup first"))
            acc["next"] = f"find a month that ties before {trusted}, or clean up {trusted}"
        prev_close, prev_month, gap = t["Printed closing"], trusted, []
        first_open = None  # earliest month not yet reconciled
        for m in months_between(trusted, through):
            r = months.get(m)
            totals["account_months"] += 1
            if r is None or not yes(r["row"]["Statement received"]):
                gap.append(m)
                acc["missing"].append(m)
                acc["to_go"] += 1
                totals["missing"] += 1
                first_open = first_open or m
                acc["next"] = acc["next"] or f"get the {m} statement from the bank"
                continue
            opening, closing = r["Printed opening"], r["Printed closing"]
            if prev_close is not None and opening is not None and opening != prev_close:
                change = opening - prev_close
                if gap:
                    acc["gaps"].append({"months": list(gap), "closing_before": str(prev_close), "opening_after": str(opening),
                                        "net_change": str(change)})
                    label = gap[0] if len(gap) == 1 else f"{gap[0]} to {gap[-1]}"
                    findings.append(Issue("CU-007", "finding", f"{name} {m}",
                                          f"opens at {opening}, {change:+} from {prev_month}'s closing {prev_close}. "
                                          f"That is the net change of the missing {label}"))
                else:
                    findings.append(Issue("CU-007", "finding", f"{name} {m}",
                                          f"opens at {opening} but {prev_month} closed at {prev_close} ({change:+}) with no month missing. "
                                          "Wrong statement, a mistyped balance, or a statement that covers different dates"))
                    acc["next"] = acc["next"] or f"check the {m} statement's opening balance"
            elif gap and prev_close is not None and opening == prev_close:
                acc["gaps"].append({"months": list(gap), "closing_before": str(prev_close), "opening_after": str(opening),
                                    "net_change": "0.00"})
            gap = []
            books = r["Books closing"]
            if books is not None and closing is not None and books != closing:
                acc["untied"].append({"month": m, "statement": str(closing), "books": str(books), "difference": str(closing - books)})
                findings.append(Issue("CU-009", "finding", f"{name} {m}",
                                      f"books close at {books}, the statement at {closing}: find the {closing - books:+} before the next month"))
                acc["next"] = acc["next"] or f"find the {closing - books:+} difference in {m}"
            done = yes(r["row"]["Reconciled"]) and books == closing
            if done:
                acc["reconciled"] += 1
                if first_open:
                    acc["out_of_order"].append(m)
                    findings.append(Issue("CU-011", "warning", f"{name} {m}",
                                          f"reconciled while {first_open} is still open. Check {m} again once the months before it are done"))
            else:
                acc["to_go"] += 1
                first_open = first_open or m
                if yes(r["row"]["Imported"]):
                    acc["next"] = acc["next"] or f"reconcile {m}"
                else:
                    acc["next"] = acc["next"] or f"record {m} and reconcile it"
            prev_close, prev_month = closing, m
        for m in acc["missing"]:
            findings.append(Issue("CU-008", "finding", f"{name} {m}", "statement missing; request it from the bank now"))
        if gap:  # missing months at the end, nothing after them to measure the change
            acc["gaps"].append({"months": list(gap), "closing_before": str(prev_close), "opening_after": None, "net_change": None})
        acc["next"] = acc["next"] or "nothing, this account is current"
        totals["reconciled"] += acc["reconciled"]
        totals["to_go"] += acc["to_go"]
        report[name] = acc
    pct = (Decimal(totals["reconciled"]) * 100 / totals["account_months"]).quantize(Decimal("1")) if totals["account_months"] else Decimal(100)
    totals["percent_done"] = int(pct)
    totals["through"] = through
    totals["caught_up"] = totals["to_go"] == 0 and not any(a["cleanup"] for a in report.values())
    return findings, report, totals


def write_requests(path, report):
    """One row per run of missing months: what to ask the bank for, and what it should show."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["Account", "Missing months", "Should open at", "Should close at", "Net change", "Ask the bank for"])
        for name, acc in report.items():
            for g in acc["gaps"]:
                months = g["months"]
                label = months[0] if len(months) == 1 else f"{months[0]} to {months[-1]}"
                ask = f"{name}: PDF statement{'s' if len(months) > 1 else ''} for {label}"
                w.writerow([name, label, g["closing_before"], g["opening_after"] or "unknown until the next statement arrives",
                            g["net_change"] or "", ask])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a catch-up bookkeeping tracker.")
    ap.add_argument("tracker")
    ap.add_argument("--through", help="last month that should be caught up, YYYY-MM (default: latest month in the file)")
    ap.add_argument("--requests", metavar="CSV", help="write the statement request list to this file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any work is left, not only on file errors")
    args = ap.parse_args(argv)
    if args.through and not MONTH_RE.match(args.through):
        print("ERROR    --through must be YYYY-MM", file=sys.stderr)
        return 2
    try:
        header, rows = load(args.tracker)
    except ReadError as exc:
        print(f"ERROR    {exc}", file=sys.stderr)
        return 2
    errors, accounts = validate(header, rows)
    findings, report, totals = ([], {}, {}) if errors else status(accounts, args.through)
    if args.requests and report:
        write_requests(args.requests, report)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": [e.as_dict() for e in errors],
                          "findings": [f.as_dict() for f in findings], "accounts": report, "totals": totals}, indent=2))
    else:
        for e in errors:
            print(e)
        if errors:
            print("Fix the tracker file first; nothing else was checked.")
        for name, acc in report.items():
            print(f"\n{name}  (last month you trust: {acc['trusted_month']}, closing {Decimal(acc['trusted_closing']):,.2f})")
            for f in findings:
                if f.where.startswith(name + " "):
                    print(f"  {f}")
            print(f"  Next: {acc['next']}")
        if report:
            print(f"\n{totals['account_months']} account-months through {totals['through']}: "
                  f"{totals['reconciled']} reconciled, {totals['to_go']} to go ({totals['percent_done']}% done), "
                  f"{totals['missing']} statement{'s' if totals['missing'] != 1 else ''} missing.")
            print("Caught up." if totals["caught_up"] else "Work the Next lines, oldest month first, then run this again.")
        if args.requests and report:
            print(f"Statement requests written to {args.requests}")
    if errors:
        return 1
    if args.strict and not totals.get("caught_up"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
