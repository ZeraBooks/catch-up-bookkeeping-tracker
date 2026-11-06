# Catch-up tracker spec, v1.1.0

A catch-up tracker is one CSV with one row per account per month. This spec defines the columns, what each status means, and the rules `cli/catch_up_check.py` applies. The JSON Schema for one row is `schema/catch-up-tracker.schema.json`. Rule IDs are in `rules/tracker-rules.csv`.

## File

- UTF-8, comma separated, one header row.
- Header exactly: `Account,Month,Statement received,Printed opening,Printed closing,Imported,Reconciled,Books closing,Notes` (CU-001).
- Rows with every cell blank are ignored, so the blank template can keep empty rows.

## Columns

| Column | Format | Meaning |
|---|---|---|
| Account | text | Account name with the last four digits. Same spelling on every row |
| Month | `YYYY-MM` | Statement month (CU-002). One row per account per month (CU-002) |
| Statement received | `Yes`, `No` or blank (CU-003) | Yes once the PDF statement is in hand |
| Printed opening | plain number or blank (CU-005) | Opening balance printed on the statement |
| Printed closing | plain number or blank (CU-005) | Closing balance printed on the statement |
| Imported | `Yes`, `No` or blank | Yes once the month's transactions are recorded |
| Reconciled | `Yes`, `No` or blank | Yes only when the month ties (CU-006) |
| Books closing | plain number or blank | Closing balance the books show |
| Notes | text | Free text |

Plain number means digits, an optional minus sign and up to two decimals: `20114.30`. No `$`, no thousands comma.

For credit cards, record the balances as printed: the amount owed. The chain works the same way.

## The month you trust

The earliest row for each account is its starting point: the last month whose books closing matches the bank. It needs Statement received = Yes and a printed closing (CU-004). Its printed opening can be blank.

If its books closing doesn't equal its printed closing, the starting point isn't trustworthy (CU-010). Pick an earlier month that ties, or treat the account as a cleanup first.

## Status of an account-month

Every month after the month you trust, through the catch-up month (`--through`, default the latest month in the file), is one account-month. Each one is in exactly one state:

| State | When |
|---|---|
| Missing | No row, or Statement received is not Yes (CU-008) |
| Received | Statement in hand, Imported is not Yes |
| Imported | Imported is Yes, Reconciled is not Yes |
| Doesn't tie | Books closing is filled in and differs from printed closing (CU-009) |
| Reconciled | Reconciled is Yes and books closing equals printed closing |

Reconciled counts as done. Every other state counts as to go. Percent done is reconciled / account-months, rounded to a whole number.

A row marked Reconciled that isn't Imported, or whose books closing differs from its printed closing, is a file error (CU-006), not a state.

## The balance chain (CU-007)

For consecutive received statements, opening(month) must equal closing(previous month).

When one or more months are missing between two received statements A and B:

```
net change of the missing months = opening(B) - closing(A)
```

Each missing statement, when it arrives, must open where the one before it closed, and the last one must close at opening(B). Missing months at the end of the window have no B yet, so their net change is unknown.

When no month is missing and opening(B) still differs from closing(A), the statement is wrong, mistyped, or covers different dates.

## Order of work (CU-011)

Months are reconciled oldest first. A month marked Reconciled while an earlier month in the same account is still open (missing, not reconciled, or not tied) is counted as done but gets a warning. Its opening balance depends on the earlier months, so it has to be checked again when they are done.

## Next step per account

The checker names one next step per account: the first problem it meets walking the months oldest first. If the month you trust doesn't tie, that comes before anything else. Otherwise, in the earliest month that has a problem:

| Problem in that month | Next step |
|---|---|
| Statement missing | Get it from the bank |
| Opening breaks the chain with nothing missing | Check the statement's opening balance |
| Books closing differs from printed closing | Find the difference |
| Imported, not reconciled | Reconcile it |
| Not imported | Record it and reconcile it |

## Statement request list

`--requests FILE` writes one row per run of missing months:

| Column | Meaning |
|---|---|
| Account | |
| Missing months | `2026-04`, or `2026-03 to 2026-04` for a run |
| Should open at | Closing of the last statement before the gap |
| Should close at | Opening of the first statement after the gap, or "unknown" at the end |
| Net change | The difference, which the missing statements must add up to |
| Ask the bank for | Ready-to-send line |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | The file has no errors. Findings may remain |
| 1 | The file has errors, or `--strict` and the catch-up isn't finished |
| 2 | The file can't be read |

## Versioning

Semantic versioning. A new optional column or a new finding is a minor version. A change that makes old valid files fail is a major version. See `CHANGELOG.md`.
