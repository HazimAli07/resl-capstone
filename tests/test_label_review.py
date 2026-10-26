"""Additional synthetic acceptance cases for D2 1.3; no source loan data."""
import unittest
from resl.data_checks import outcome


def row(month, days=0, status="active"):
    return dict(month_on_book=str(month), delinquency_days=str(days), status=status)


class LabelReviewTests(unittest.TestCase):
    def test_delinquency_threshold_at_month_24(self):
        for days, target in ((89, 0), (90, 1), (120, 1)):
            with self.subTest(days=days):
                rows = [row(m) for m in range(1, 24)] + [row(24, days)]
                self.assertEqual(outcome(rows)["target"], target)

    def test_month_one_event_is_included(self):
        self.assertEqual(outcome([row(1, 90)])["target"], 1)

    def test_payoff_at_horizon_requires_all_months(self):
        rows = [row(m) for m in range(1, 24)] + [row(24, status="paid_off")]
        self.assertEqual(outcome(rows), dict(target=0, reason="complete_followup_no_event"))
        self.assertEqual(outcome(rows[1:])["reason"], "censored_followup_gap")

    def test_month_23_payoff_remains_censored(self):
        rows = [row(m) for m in range(1, 23)] + [row(23, status="paid_off")]
        self.assertEqual(outcome(rows)["reason"], "censored_early_payoff")

    def test_later_event_cannot_fill_missing_horizon(self):
        self.assertEqual(outcome([row(m) for m in range(1, 24)] + [row(25, 90)]),
                         dict(target=None, reason="censored_incomplete_followup"))

    def test_event_precedes_censoring_decision(self):
        for status in ("foreclosure", "reo"):
            with self.subTest(status=status):
                self.assertEqual(outcome([row(3, status=status), row(8, status="paid_off")])["target"], 1)

    def test_input_order_does_not_change_label(self):
        rows = [row(m) for m in range(1, 25)]
        self.assertEqual(outcome(rows), outcome(list(reversed(rows))))

    def test_invalid_months_and_negative_days_are_rejected(self):
        for record in (row(0), row(-1), row("1.5"), row(1, -1)):
            with self.subTest(record=record), self.assertRaises(ValueError):
                outcome([record])

    def test_ambiguous_records_still_stop_even_with_positive_event(self):
        for rows in ([row(1, 90), row(1)], [row(1, 90), row(2, status="unknown")],
                     [row(1, status="paid_off"), row(2, 90)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                outcome(rows)

    def test_no_in_window_observations_is_incomplete(self):
        self.assertEqual(outcome([row(25)]),
                         dict(target=None, reason="censored_incomplete_followup"))
