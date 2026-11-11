# Catch-up bookkeeping tracker

Catch-up bookkeeping fills in months that were never recorded. You start from the last month whose closing balance you trust, gather every bank and card statement since then, and work the months oldest first, reconciling each one before the next. [ZeraBooks](https://www.zerabooks.com/catch-up-bookkeeping) does catch-up for you, quoted once after a free call. This repo is the tracker to run it yourself, with a checker that says what's missing and what to do next.

What's here:

- A one-row-per-account-per-month tracker layout, as a spec and a JSON Schema ([`SPEC.md`](SPEC.md), [`schema/`](schema/))
- Eleven rules with IDs. Some are file errors, some are work still to do, and one flags work done out of order ([`rules/tracker-rules.csv`](rules/tracker-rules.csv))
- A checker that validates the tracker, lists missing statements with the net change each gap must hold, flags months that don't tie, and writes a statement request list ([`cli/catch_up_check.py`](cli/catch_up_check.py))
- Four fictional businesses at different stages, and seven trackers that fail on purpose ([`samples/`](samples/))
- The blank template, the checklist and the original `catch_up_status.py`, unchanged

Python 3.8+, standard library only. Download everything from the [latest release](https://github.com/ZeraBooks/catch-up-bookkeeping-tracker/releases/latest).

## How do I know what's missing when I'm months behind?

Line up every statement's printed balances. Each statement must open where the one before it closed. When a statement is missing, the next one opens at a different number, and the difference is the net change of everything you don't have yet. That tells you how much activity to expect before the statement even arrives.

```bash
python3 cli/catch_up_check.py samples/valid/juniper-lane-florist.csv --requests statement-requests.csv
```

```
Checking 3318  (last month you trust: 2025-11, closing 18,240.55)
  FINDING  CU-007 Checking 3318 2026-05: opens at 21400.47, +1461.58 from 2026-02's closing 19938.89. That is the net change of the missing 2026-03 to 2026-04
  WARNING  CU-011 Checking 3318 2026-08: reconciled while 2026-03 is still open. Check 2026-08 again once the months before it are done
  FINDING  CU-008 Checking 3318 2026-03: statement missing; request it from the bank now
  FINDING  CU-008 Checking 3318 2026-04: statement missing; request it from the bank now
  Next: get the 2026-03 statement from the bank

Visa 7702  (last month you trust: 2025-11, closing 4,118.20)
  Next: reconcile 2026-02

22 account-months through 2026-10: 6 reconciled, 16 to go (27% done), 2 statements missing.
```

## Example 1: two missing months in a row, and a month done too early

Juniper Lane Florist is a fictional flower shop with a checking account and a Visa card. Its books were last right at November 30, 2025. A year later, the owner hands over everything through October 2026. Checking around the gap looks like this:

| Month | Printed opening | Printed closing | Status |
|---|---|---|---|
| February 2026 | 16,551.83 | 19,938.89 | Reconciled |
| March 2026 | not sent | not sent | Missing |
| April 2026 | not sent | not sent | Missing |
| May 2026 | 21,400.47 | 20,984.57 | Not started |

May opens 21,400.47 - 19,938.89 = 1,461.58 above where February closed. That 1,461.58 is March and April together. When both statements arrive, they have to land on it: March's net change plus April's net change must equal 1,461.58. In this sample they are -1,140.75 and +2,602.33, and -1,140.75 + 2,602.33 = 1,461.58. If they don't add up, a third statement or a page is still missing.

The request list the checker writes:

| Account | Missing months | Should open at | Should close at | Net change |
|---|---|---|---|---|
| Checking 3318 | 2026-03 to 2026-04 | 19,938.89 | 21,400.47 | 1,461.58 |

Send the bank that row and you can check what comes back in a minute.

The other problem: a previous helper reconciled August 2026 before March was done. August ties today, but its opening balance rests on March and April. If either one turns up a transaction that was booked in the wrong month, August changes too. The checker counts August as reconciled and warns (CU-011) so it gets checked again once the months before it are done.

Totals: 11 months x 2 accounts = 22 account-months. Reconciled: checking December, January, February and August, card December and January, so 6. That leaves 16 to go, and 6 / 22 = 27% done.

## Example 2: the month you trust doesn't tie

Brook and Vale Cafe is a fictional cafe. The owner says March 2026 was the last good month. The tracker disagrees:

| Month | Printed closing | Books closing | Difference |
|---|---|---|---|
| March 2026 | 9,870.12 | 9,412.12 | 458.00 |

9,870.12 - 9,412.12 = 458.00. The books are 458.00 below the bank in the month everyone assumed was clean. Adding April on top would carry that 458.00 forward into every later month. The checker reports CU-010: pick an earlier month that ties, or clean up March first. That's the difference between a catch-up (months never done) and a cleanup (months done wrong).

## Example 3: the original nine-month backlog

Halden Bike Repair has a checking account, a savings account and a Visa card. Its books were last right at December 31, 2025. In October 2026 the owner sent January to September. Two days in, checking looks like this:

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

April is missing. May opens at 20,114.30, which is 1,343.35 above where March closed, so that is April's net change. March doesn't tie: the books are 84.00 below the statement. Fix March before anything else. On the card, July isn't in the file at all. August opens at 2,904.66 against June's 3,377.51, so July's net change is -472.85. In all, 27 account-months need catching up: 7 are reconciled and 20 are to go.

Pinecrest Tutoring, the fourth sample, is caught up: three months, all reconciled, nothing missing. Run it with `--strict` and it exits 0.

## The tracker

One row per account per month. The first row for each account is the last month you trust.

| Column | What goes in it |
|---|---|
| Account | Name and last four digits, spelled the same on every row |
| Month | `YYYY-MM` |
| Statement received | Yes once the PDF is in hand |
| Printed opening, Printed closing | Copied from the statement. For cards, the amount owed |
| Imported | Yes once the month is recorded |
| Reconciled | Yes only when books closing equals printed closing |
| Books closing | What the books show at month end |
| Notes | Anything |

Download PDF statements, not the activity CSV. The CSV usually has no opening or closing balance, and those balances are what prove a month is complete. The full layout and every rule are in [`SPEC.md`](SPEC.md).

## Run the checker

```bash
python3 cli/catch_up_check.py my-tracker.csv                    # status for every account
python3 cli/catch_up_check.py my-tracker.csv --through 2026-09  # stop at September
python3 cli/catch_up_check.py my-tracker.csv --requests requests.csv
python3 cli/catch_up_check.py my-tracker.csv --json              # for scripts
python3 cli/catch_up_check.py my-tracker.csv --strict            # exit 1 until caught up
```

Exit codes: 0 when the tracker file is valid, 1 when it has errors (or, with `--strict`, when work is left), 2 when it can't be read.

## How ZeraBooks does catch-up bookkeeping

![ZeraBooks reconciliation for a May 2026 statement: deposits, withdrawals and net each match the statement with a difference of $0.00](https://zerabooks.github.io/images/app/banks-statement-ties.png)

The order is the same as this tracker. With [ZeraBooks](https://www.zerabooks.com/catch-up-bookkeeping), you send every statement, years of them if needed, with no sorting or renaming, and ZeraBooks sets you up and catches up your past months for free. A month only closes when the ledger matches the statement's printed opening and closing balances, and gaps in the chain become a short list of what to send. Transfers, owner draws and anything unclear come to you in one list. Once you're current, ZeraBooks keeps the books done for $79 a month billed annually or $149 month to month, with a 7-day free trial.

## FAQ

### Where do you start when you are months behind?

At the most recent month whose closing balance in the books matches the bank. If no month ties, the job is a cleanup, not a catch-up, because months that were done wrong have to be fixed before new ones are added on top.

### What if two statements in a row are missing?

The next statement you do have still opens at a number. The difference from the last closing you have is the combined net change of all the missing months. Each missing statement, once it arrives, has to open where the one before it closed, and together they have to land on the next opening.

### Can I skip ahead and do the recent months first?

You can record them, but don't call them done. A month's opening balance depends on every month before it. If an earlier month changes, the later ones change with it.

### Do I need receipts to catch up?

Not to start. Bank and card statements carry every transaction and the balances that prove each month. Receipts and invoices answer category questions, and the questions list tells you which ones matter.

### What deadlines does being behind put at risk?

For 2026, individual estimated tax is due April 15, June 15 and September 15, 2026 and January 15, 2027 ([IRS](https://www.irs.gov/faqs/estimated-tax)). Form 1099-NEC is due to contractors and the IRS by January 31 ([IRS](https://www.irs.gov/forms-pubs/about-form-1099-nec)). Both need current books, and so does any lender or landlord asking for a recent profit and loss.

## Run the tests

```bash
python3 scripts/generate_samples.py
python3 scripts/build_manifest.py
python3 -m unittest discover -s tests -v
```

`MANIFEST.json` lists every sample, schema and rules file with its size, row count and SHA-256. Check them with `shasum -a 256 -c checksums.txt`.

## Learn more

Full guide: [Catch-up bookkeeping](https://www.zerabooks.com/catch-up-bookkeeping). Related: [ZeraBooks](https://www.zerabooks.com/) and [bookkeeping cleanup](https://www.zerabooks.com/bookkeeping-cleanup).

## License and citation

The content and data in this repository are licensed under [CC BY 4.0](LICENSE). The code (`*.py`) is licensed under [MIT](LICENSE-CODE). Cite it with [`CITATION.cff`](CITATION.cff) or as: ZeraBooks, *Catch-up Bookkeeping Tracker*, v1.1.0, 2026, https://github.com/ZeraBooks/catch-up-bookkeeping-tracker.

ZeraBooks is accounting software that does your books for you, with free setup and a free catch-up of your past months. Maintained by [ZeraBooks](https://www.zerabooks.com).
