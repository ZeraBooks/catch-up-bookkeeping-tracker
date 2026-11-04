# Catch-up bookkeeping tracker

Catch-up bookkeeping fills in months that were never recorded. You start from
the last month whose closing balance you trust, gather every bank and card
statement since then, and work the months oldest first, reconciling each one
before the next. This repo has a month-by-month tracker for every account, a
script that lists missing statement months and months that don't tie, and a
catch-up checklist, with a fictional business nine months behind.

## Files

| File | What it is |
|---|---|
| `catch-up-tracker-template.csv` | A blank tracker. One row per account per month: statement received, printed opening and closing, imported, reconciled, books closing, notes. |
| `catch-up-tracker.csv` | The fictional example below, two days into its catch-up. |
| `catch_up_status.py` | Reads the tracker and lists missing statements, breaks in the balance chain, months that don't tie, and the next month to work on for each account. |
| `catch-up-checklist.md` | The order of work, what to gather, and when the catch-up is done. |

The script is Python 3, standard library only.

## How to use it

1. For each account, put the last month you trust as its first row, with its
   closing balance.
2. Add a row for every month since then as statements come in. Copy the
   opening and closing balances printed on the statement.
3. As you record and reconcile each month, mark Imported and Reconciled and
   fill in the closing balance your books show.
4. Run:

   ```
   python3 catch_up_status.py catch-up-tracker.csv
   ```

   Add a month (for example `2026-09`) to say how far the catch-up should go.
   Without it, the script uses the latest month in the file.
5. Work the "Next" line for each account, then run it again.

## The worked example

Halden Bike Repair is a fictional shop with a checking account, a savings
account and a Visa card. Its books were last right at December 31, 2025. In
October 2026 the owner sent nine months of statements, January to September.
Two days in, the tracker shows this for checking:

| Month | Printed opening | Printed closing | Status |
|---|---|---|---|
| December 2025 (last trusted) | | 22,418.60 | Starting point |
| January | 22,418.60 | 19,902.15 | Reconciled |
| February | 19,902.15 | 21,355.40 | Reconciled |
| March | 21,355.40 | 18,770.95 | Books show 18,686.95, 84.00 short |
| April | not sent | not sent | Missing |
| May | 20,114.30 | 23,006.80 | Not started |
| June | 23,006.80 | 21,447.12 | Not started |
| July | 21,447.12 | 24,980.55 | Not started |
| August | 24,980.55 | 22,615.09 | Not started |
| September | 22,615.09 | 25,302.44 | Not started |

What the script reports:

- **Checking:** April is missing. May opens at 20,114.30, which is 1,343.35
  above where March closed, so that is April's net change. March doesn't tie:
  the books are 84.00 below the statement, the size of one card fee entered
  twice. Fix March before anything else.
- **Savings:** every statement is in and January to March are reconciled.
  Next is April.
- **Visa:** July isn't in the file at all. August opens at 2,904.66 against
  June's 3,377.51, so July's net change is -472.85. January and February are
  reconciled; next is March.

In all, 27 account-months need to be caught up, 7 are reconciled and 20 are to
go. Both missing statements were requested from the bank the same day.

The business and figures are fictional.

## FAQ

### Where do you start when you are months behind?

At the most recent month whose closing balance in the books matches the bank.
If no month ties, the job is a cleanup, not a catch-up, because months that
were done wrong have to be fixed before new ones are added on top.

### Do I need receipts to catch up?

Not to start. Bank and card statements carry every transaction and the
balances that prove each month. Receipts and invoices answer category
questions, and the questions list tells you which ones matter.

### What deadlines does being behind put at risk?

For 2026, individual estimated tax is due April 15, June 15 and September 15,
2026 and January 15, 2027. Form 1099-NEC is due to contractors and the IRS by
January 31. Both need current books, and so does any lender or landlord asking
for a recent profit and loss.

## Learn more

Full guide: [Catch-up bookkeeping](https://www.zerabooks.com/catch-up-bookkeeping). Related: [ZeraBooks bookkeeping services](https://www.zerabooks.com/bookkeeping-services).

## License

The content and data in this repository are licensed under
[CC BY 4.0](LICENSE). Free to use and adapt with credit to ZeraBooks.
The code (`*.py`) is licensed under [MIT](LICENSE-CODE).

Maintained by [ZeraBooks](https://www.zerabooks.com).
