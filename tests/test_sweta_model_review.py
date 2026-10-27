"""Sweta-owned integration checks; existing owners' tests remain unchanged."""
import unittest
from resl.sweta_model_review import matched_review, chart


def cohort():
    return [dict(loan_id=str(i), split='validation', target=y, credit_score=700,
                 dti=30, ltv=70) for i,y in enumerate((0,1,None))]


def predictions():
    return [dict(model=m, loan_id=str(i), split='validation', target=y, probability=p)
            for m in ('a','b') for i,(y,p) in enumerate(((0,.1),(1,.8),(None,.5)))]


class ModelIntegrationTests(unittest.TestCase):
    def test_matched_models_keep_censored_and_points_distinct(self):
        report, scores = matched_review(cohort(), predictions(), max_reviews=1)
        self.assertEqual(report['models']['a']['excluded_censored_count'], 1)
        self.assertAlmostEqual(report['models']['a']['brier_score'], .025)
        self.assertEqual(len(scores), 3)
        self.assertTrue(all('probability' not in r for r in scores))
        self.assertFalse(report['final_test_used'])
        self.assertFalse(report['calibration_fitted'])

    def test_mismatched_ids_labels_and_duplicates_rejected(self):
        for kind in ('missing','duplicate','label','test'):
            rows = predictions()
            if kind == 'missing': rows.pop()
            if kind == 'duplicate': rows[-1] = dict(rows[-2])
            if kind == 'label': rows[-1]['target'] = 1
            if kind == 'test': rows[-1]['split'] = 'test'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                matched_review(cohort(), rows, max_reviews=1)

    def test_tied_rule_scores_do_not_exceed_budget(self):
        report, _ = matched_review(cohort(), predictions(), max_reviews=1)
        self.assertEqual(report['rule_ranking']['reviewed'], 0)
        self.assertIsNone(report['rule_ranking']['precision'])

    def test_invalid_budget_and_source_split_rejected(self):
        for budget in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                matched_review(cohort(), predictions(), max_reviews=budget)
        source = cohort(); source[0]['split'] = 'test'
        with self.assertRaises(ValueError):
            matched_review(source, predictions(), max_reviews=1)

    def test_chart_escapes_labels_and_marks_synthetic(self):
        report, _ = matched_review(cohort(), predictions(), max_reviews=1)
        svg = chart({'<script>': report['models']['a']})
        self.assertIn('SYNTHETIC', svg)
        self.assertIn('&lt;script&gt;', svg)
        self.assertNotIn('<script>', svg)
