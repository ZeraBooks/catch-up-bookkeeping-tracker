# Changelog

## 1.1.0 (2026-11-06)

- `SPEC.md`: the tracker layout, account-month states, the balance chain across one or more missing months, order of work, next-step logic and the statement request list.
- JSON Schema for one tracker row in `schema/`.
- Eleven rules with IDs in `rules/tracker-rules.csv`: file errors, findings and an out-of-order warning.
- `cli/catch_up_check.py`: validates the tracker, reports status per account with rule IDs, writes a statement request list (`--requests`), `--through`, `--json` and `--strict`.
- Samples: Halden Bike Repair (the original example), Juniper Lane Florist (two missing months in a row, a month reconciled out of order), Brook and Vale Cafe (the trusted month doesn't tie), Pinecrest Tutoring (caught up), and seven invalid trackers with `expected.json`.
- `scripts/generate_samples.py`, tests, CI, `MANIFEST.json`, `checksums.txt` and a release zip.
- The template, checklist, root tracker and `catch_up_status.py` are unchanged.

## 1.0.0 (2026-11-04)

- Tracker template, the Halden Bike Repair example, `catch_up_status.py` and the catch-up checklist.
