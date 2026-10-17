import unittest

from resl.data_checks import (FEATURES, check_records, chronological_split,
                              feature_record, outcome)


def origination(loan_id="S1", started="2017-01-01"):
    return {"loan_id": loan_id, "origination_date": started,
            **{name: "1" for name in FEATURES}}


def performance(month, days=0, status="active", loan_id="S1"):
    return {"loan_id": loan_id, "month_on_book": str(month),
            "delinquency_days": str(days), "status": status}


class OutcomeTests(unittest.TestCase):
    def test_complete_followup_is_negative(self):
        self.assertEqual(outcome([performance(m) for m in range(1, 25)])["target"], 0)

    def test_observed_90_days_is_positive_even_with_gaps(self):
        self.assertEqual(outcome([performance(3, 90)])["target"], 1)

    def test_foreclosure_and_reo_are_positive_at_horizon(self):
        for status in ("foreclosure", "reo"):
            with self.subTest(status=status):
                self.assertEqual(outcome([performance(24, status=status)])["target"], 1)

    def test_event_after_horizon_does_not_change_complete_negative(self):
        rows = [performance(m) for m in range(1, 25)] + [performance(25, 90)]
        self.assertEqual(outcome(rows)["target"], 0)

    def test_early_payoff_is_censored(self):
        rows = [performance(1), performance(2, status="paid_off")]
        self.assertEqual(outcome(rows), {"target": None, "reason": "censored_early_payoff"})

    def test_payoff_after_observed_event_keeps_positive(self):
        self.assertEqual(outcome([performance(1, 90), performance(2, status="paid_off")])["target"], 1)

    def test_gap_is_not_negative(self):
        result = outcome([performance(m) for m in range(1, 25) if m != 5])
        self.assertEqual(result["reason"], "censored_followup_gap")
        self.assertIsNone(result["target"])

    def test_short_or_absent_followup_is_not_negative(self):
        for rows in ([], [performance(m) for m in range(1, 24)]):
            self.assertEqual(outcome(rows)["reason"], "censored_incomplete_followup")

    def test_missing_delinquency_and_unknown_codes_stop_processing(self):
        for row in (performance(1, ""), performance(1, status="unknown")):
            with self.assertRaises(ValueError):
                outcome([row])

    def test_duplicate_month_or_records_after_payoff_stop_processing(self):
        for rows in ([performance(1), performance(1)],
                     [performance(1, status="paid_off"), performance(2)]):
            with self.assertRaises(ValueError):
                outcome(rows)


class JoinAndTimingTests(unittest.TestCase):
    def test_duplicate_loan_ids_rejected(self):
        with self.assertRaises(ValueError):
            check_records([origination(), origination()], [])

    def test_orphan_performance_records_rejected(self):
        with self.assertRaises(ValueError):
            check_records([origination()], [performance(1, loan_id="other")])

    def test_missing_input_is_reported_without_imputation(self):
        row = origination()
        row["credit_score"] = ""
        result = check_records([row], [performance(1)])
        self.assertEqual(result["missing_candidate_inputs"], {"credit_score": 1})

    def test_input_allowlist_drops_identifiers_and_future_outcomes(self):
        row = {**origination(), "delinquency_days": "90", "target": "1", "current_balance": "0"}
        features = feature_record(row)
        self.assertEqual(set(features), set(FEATURES))
        self.assertFalse({"loan_id", "origination_date", "delinquency_days", "target", "current_balance"} & set(features))

    def test_split_boundaries_keep_loans_disjoint_and_in_order(self):
        rows = [origination("a", "2017-12-31"), origination("b", "2018-01-01"),
                origination("c", "2018-12-31"), origination("d", "2019-01-01")]
        result = chronological_split(rows, "2018-01-01", "2019-01-01")
        self.assertEqual(result, {"train": ["a"], "validation": ["b", "c"], "test": ["d"]})

    def test_invalid_or_overlapping_split_is_rejected(self):
        with self.assertRaises(ValueError):
            chronological_split([origination()], "2019-01-01", "2018-01-01")
        with self.assertRaises(ValueError):
            chronological_split([origination(), origination()], "2018-01-01", "2019-01-01")


if __name__ == "__main__":
    unittest.main()
