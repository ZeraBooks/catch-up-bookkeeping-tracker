import csv
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cli"))
import catch_up_check as cu  # noqa: E402

S = os.path.join(ROOT, "samples")
CLI = os.path.join(ROOT, "cli", "catch_up_check.py")


def run(path, through=None):
    header, rows = cu.load(path)
    errors, accounts = cu.validate(header, rows)
    assert not errors, [str(e) for e in errors]
    return cu.status(accounts, through)


def rules(findings, severity=None):
    return [f.rule for f in findings if severity is None or f.severity == severity]


class Halden(unittest.TestCase):
    """The README example, nine months behind."""

    def setUp(self):
        self.findings, self.report, self.totals = run(os.path.join(S, "valid", "halden-bike-repair.csv"))

    def test_totals_match_readme(self):
        self.assertEqual((self.totals["account_months"], self.totals["reconciled"], self.totals["to_go"], self.totals["missing"]),
                         (27, 7, 20, 2))

    def test_checking_gap_and_untied_march(self):
        c = self.report["Checking 2201"]
        self.assertEqual(c["missing"], ["2026-04"])
        self.assertEqual(c["gaps"][0]["net_change"], "1343.35")
        self.assertEqual(c["untied"], [{"month": "2026-03", "statement": "18770.95", "books": "18686.95", "difference": "84.00"}])
        self.assertEqual(c["next"], "find the +84.00 difference in 2026-03")

    def test_visa_july_missing(self):
        v = self.report["Visa 5530"]
        self.assertEqual(v["missing"], ["2026-07"])
        self.assertEqual(v["gaps"][0]["net_change"], "-472.85")
        self.assertEqual(v["next"], "record 2026-03 and reconcile it")

    def test_root_tracker_is_the_same_file(self):
        self.assertEqual(open(os.path.join(ROOT, "catch-up-tracker.csv")).read(),
                         open(os.path.join(S, "valid", "halden-bike-repair.csv")).read())


class Juniper(unittest.TestCase):
    """Two months in a row missing, and a month reconciled out of order."""

    def setUp(self):
        self.findings, self.report, self.totals = run(os.path.join(S, "valid", "juniper-lane-florist.csv"))

    def test_two_month_gap_is_one_combined_net_change(self):
        g = self.report["Checking 3318"]["gaps"]
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["months"], ["2026-03", "2026-04"])
        # March -1,140.75 and April +2,602.33 together
        self.assertEqual(Decimal(g[0]["net_change"]), Decimal("-1140.75") + Decimal("2602.33"))
        self.assertEqual(Decimal(g[0]["opening_after"]) - Decimal(g[0]["closing_before"]), Decimal("1461.58"))

    def test_august_reconciled_out_of_order(self):
        self.assertEqual(self.report["Checking 3318"]["out_of_order"], ["2026-08"])
        self.assertIn("CU-011", rules(self.findings, "warning"))

    def test_totals(self):
        self.assertEqual((self.totals["account_months"], self.totals["reconciled"], self.totals["to_go"]), (22, 6, 16))
        self.assertEqual(self.totals["percent_done"], 27)

    def test_card_imported_month_is_next_to_reconcile(self):
        self.assertEqual(self.report["Visa 7702"]["next"], "reconcile 2026-02")


class Others(unittest.TestCase):
    def test_pinecrest_is_caught_up(self):
        findings, report, totals = run(os.path.join(S, "valid", "pinecrest-tutoring.csv"))
        self.assertEqual(findings, [])
        self.assertTrue(totals["caught_up"])
        out = subprocess.run([sys.executable, CLI, "--strict", os.path.join(S, "valid", "pinecrest-tutoring.csv")], capture_output=True)
        self.assertEqual(out.returncode, 0)

    def test_brook_and_vale_needs_cleanup_first(self):
        findings, report, totals = run(os.path.join(S, "valid", "brook-and-vale-cafe.csv"))
        self.assertEqual(rules(findings), ["CU-010"])
        self.assertTrue(report["Checking 9044"]["cleanup"])
        self.assertFalse(totals["caught_up"])
        self.assertIn("458.00 below", findings[0].message)

    def test_through_limits_the_window(self):
        _, report, totals = run(os.path.join(S, "valid", "halden-bike-repair.csv"), "2026-03")
        self.assertEqual(totals["account_months"], 9)
        self.assertEqual(report["Checking 2201"]["missing"], [])

    def test_missing_month_at_the_end_has_no_net_change_yet(self):
        _, report, _ = run(os.path.join(S, "valid", "pinecrest-tutoring.csv"), "2026-10")
        self.assertEqual(report["Checking 0571"]["missing"], ["2026-10"])
        self.assertIsNone(report["Checking 0571"]["gaps"][-1]["net_change"])


class Chains(unittest.TestCase):
    def test_every_received_statement_adds_up_within_its_account(self):
        # Within a run with no missing month, each opening equals the previous closing.
        for p in glob.glob(os.path.join(S, "valid", "*.csv")):
            prev = {}
            for r in csv.DictReader(open(p, encoding="utf-8")):
                a = r["Account"]
                last = prev.get(a)
                if r["Statement received"] == "Yes" and r["Printed opening"] and last \
                        and last[0] and cu.next_month(last[1]) == r["Month"]:
                    self.assertEqual(r["Printed opening"], last[0], f"{p} {a} {r['Month']}")
                prev[a] = (r["Printed closing"] if r["Statement received"] == "Yes" else None, r["Month"])


class Invalid(unittest.TestCase):
    def test_each_invalid_file_fails_only_its_rule(self):
        expected = json.load(open(os.path.join(S, "invalid", "expected.json"), encoding="utf-8"))
        self.assertEqual(sorted(expected), sorted(os.path.basename(p) for p in glob.glob(os.path.join(S, "invalid", "*.csv"))))
        for name, rule in expected.items():
            out = subprocess.run([sys.executable, CLI, "--json", os.path.join(S, "invalid", name)], capture_output=True, text=True)
            self.assertEqual(out.returncode, 1, name)
            self.assertEqual({e["rule"] for e in json.loads(out.stdout)["errors"]}, {rule}, name)

    def test_unreadable_file_exits_2(self):
        out = subprocess.run([sys.executable, CLI, "no-such-file.csv"], capture_output=True)
        self.assertEqual(out.returncode, 2)

    def test_blank_template_rows_are_ignored(self):
        header, rows = cu.load(os.path.join(ROOT, "catch-up-tracker-template.csv"))
        errors, _ = cu.validate(header, rows)
        # The template's first row has no account or month yet.
        self.assertEqual({e.rule for e in errors}, {"CU-002"})


class Requests(unittest.TestCase):
    def test_request_list_for_juniper(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "req.csv")
            subprocess.run([sys.executable, CLI, os.path.join(S, "valid", "juniper-lane-florist.csv"), "--requests", out],
                           check=True, capture_output=True)
            rows = list(csv.DictReader(open(out, encoding="utf-8")))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Missing months"], "2026-03 to 2026-04")
        self.assertEqual((rows[0]["Should open at"], rows[0]["Should close at"], rows[0]["Net change"]),
                         ("19938.89", "21400.47", "1461.58"))


class Schema(unittest.TestCase):
    def test_valid_samples_match_schema(self):
        schema = json.load(open(os.path.join(ROOT, "schema", "catch-up-tracker.schema.json"), encoding="utf-8"))
        for p in glob.glob(os.path.join(S, "valid", "*.csv")):
            reader = csv.DictReader(open(p, encoding="utf-8"))
            self.assertEqual(reader.fieldnames, schema["required"])
            for row in reader:
                for k, v in row.items():
                    prop = schema["properties"][k]
                    if "pattern" in prop:
                        self.assertRegex(v, re.compile(prop["pattern"]), f"{p} {k}")
                    if "enum" in prop:
                        self.assertIn(v, prop["enum"], f"{p} {k}")


if __name__ == "__main__":
    unittest.main()
