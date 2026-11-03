"""Invented header exports: conversion behavior, never source/cohort acceptance.

Headers, IDs, dates and values below are made up. Public glossary code meanings
are exercised without downloading any loan files or selecting a release.
"""
import copy
import csv
import io
import unittest

from resl.data_checks import FEATURES, ORIGINATION_FIELDS
from resl.hazim_contract import validate_application
from resl.mannan_mapping import (
    FREDDIE_PURPOSE_MEANINGS, audit_cohort, freddie_origination_mapping, normalize_origination,
    read_header_export,
)


# Deliberately invented export labels; these are not claimed raw-file headers.
HEADERS = dict(zip(ORIGINATION_FIELDS, (
    "invented_key", "independent_note_date", "invented_score", "invented_dti",
    "invented_ltv", "invented_upb", "invented_rate", "invented_term",
    "invented_purpose", "invented_occupancy", "invented_property")))


def export(**changes):
    values = dict(zip(ORIGINATION_FIELDS, (
        "invented-a", "2017-01-03", "740", "32", "80", "250000", "4.5",
        "360", "P", "P", "SF")))
    values.update(changes)
    return {HEADERS[field]: value for field, value in values.items()}


class SourceMappingPR4Tests(unittest.TestCase):
    def setUp(self):
        self.mapping = freddie_origination_mapping(
            HEADERS, ltv_regime="pre_2018q2", date_anchor="exact_origination_date")

    def normalize(self, rows, mapping=None, **options):
        return normalize_origination(
            rows, self.mapping if mapping is None else mapping,
            release="invented-fixture-not-a-selected-release", synthetic=True, **options)

    def test_explicit_headers_convert_units_without_rescaling_or_unrounding(self):
        row = self.normalize([export()])[0]
        self.assertEqual(set(row), set(ORIGINATION_FIELDS))
        self.assertEqual([row[f] for f in (
            "credit_score", "dti", "ltv", "original_balance", "original_rate", "original_term")],
            [740, 32, 80, 250000, 4.5, 360])
        self.assertEqual(row["origination_date"], "2017-01-03")

    def test_all_purpose_codes_follow_existing_contract_with_explicit_coarsening(self):
        values = []
        for code in ("P", "C", "N", "R"):
            values.append(self.normalize([export(loan_purpose=code)])[0]["loan_purpose"])
        self.assertEqual(values, ["purchase", "cash_out", "refinance", "refinance"])
        self.assertNotEqual(FREDDIE_PURPOSE_MEANINGS["N"], FREDDIE_PURPOSE_MEANINGS["R"])

    def test_all_documented_category_outputs_pass_existing_model_interface(self):
        for field, codes in (("loan_purpose", ("P", "C", "N", "R", "9")),
                             ("occupancy", ("P", "I", "S", "9")),
                             ("property_type", ("CP", "CO", "PU", "SF", "MH", "99"))):
            for code in codes:
                with self.subTest(field=field, code=code):
                    row = self.normalize([export(**{field: code})])[0]
                    self.assertEqual(validate_application({f: row[f] for f in FEATURES}),
                                     {f: row[f] for f in FEATURES})

    def test_all_property_codes_preserve_pud_and_cooperative(self):
        values = {code: self.normalize([export(property_type=code)])[0]["property_type"]
                  for code in ("CP", "CO", "PU", "SF", "MH")}
        self.assertEqual(values, {"CP": "cooperative", "CO": "condo", "PU": "pud",
                                  "SF": "single_family", "MH": "manufactured"})

    def test_occupancy_codes_are_explicit(self):
        for code, expected in (("P", "primary"), ("I", "investment"), ("S", "second_home")):
            with self.subTest(code=code):
                self.assertEqual(self.normalize([export(occupancy=code)])[0]["occupancy"], expected)

    def test_documented_sentinels_become_missing(self):
        row = self.normalize([export(credit_score="9999", dti="999", ltv="999",
                                     loan_purpose="9", occupancy="9", property_type="99")])[0]
        for field in ("credit_score", "dti", "ltv", "loan_purpose", "occupancy", "property_type"):
            with self.subTest(field=field):
                self.assertIsNone(row[field])

    def test_null_and_blank_optional_values_remain_missing(self):
        row = self.normalize([export(dti=None, original_rate="  ", property_type=None)])[0]
        self.assertIsNone(row["dti"])
        self.assertIsNone(row["original_rate"])
        self.assertIsNone(row["property_type"])

    def test_unknown_or_wrong_case_codes_fail_instead_of_becoming_missing(self):
        for field, value in (("loan_purpose", "X"), ("occupancy", "p"),
                             ("property_type", "PUD"), ("property_type", "9")):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.normalize([export(**{field: value})])

    def test_selected_vintage_bounds_are_explicit(self):
        for changes in ({"dti": "66"}, {"ltv": "106"}, {"ltv": "5"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.normalize([export(**changes)])
        for regime in ("from_2018q2", "harp"):
            mapping = freddie_origination_mapping(
                HEADERS, ltv_regime=regime, date_anchor="exact_origination_date")
            self.assertEqual(self.normalize([export(ltv="150", dti="999")], mapping)[0]["ltv"], 150)
        with self.assertRaises(ValueError):
            freddie_origination_mapping(HEADERS, ltv_regime="unknown",
                                         date_anchor="exact_origination_date")

    def test_harp_source_regime_requires_unavailable_dti(self):
        mapping = freddie_origination_mapping(
            HEADERS, ltv_regime="harp", date_anchor="exact_origination_date")
        with self.assertRaisesRegex(ValueError, "requires missing"):
            self.normalize([export(dti="32")], mapping)
        self.assertIsNone(self.normalize([export(dti="999")], mapping)[0]["dti"])

    def test_wrong_units_and_nonfinite_or_boolean_values_are_rejected(self):
        mapping = copy.deepcopy(self.mapping)
        mapping["dti"]["unit"] = "fraction"
        with self.assertRaisesRegex(ValueError, "unit"):
            self.normalize([export()], mapping)
        for changes in ({"dti": "NaN"}, {"original_rate": "inf"},
                        {"credit_score": True}, {"original_term": "360.5"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.normalize([export(**changes)])

    def test_required_columns_and_required_identifier_values_cannot_be_missing(self):
        for field in ORIGINATION_FIELDS:
            row = export()
            del row[HEADERS[field]]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.normalize([row])
        for changes in ({"loan_id": None}, {"loan_id": " "}, {"origination_date": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.normalize([export(**changes)])

    def test_new_headers_and_schema_drift_fail(self):
        extra = {**export(), "unreviewed_new_field": "x"}
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            self.normalize([extra])
        # An explicitly ignored export field is permitted, but cannot disappear
        # midway through one file and disguise a changed export schema.
        self.assertEqual(len(self.normalize([extra], ignored_headers=("unreviewed_new_field",))), 1)
        with self.assertRaisesRegex(ValueError, "schema drift"):
            self.normalize([extra, export(loan_id="invented-b")],
                           ignored_headers=("unreviewed_new_field",))

    def test_actual_path_does_not_implicitly_ignore_split_metadata(self):
        row = {**export(), "split": "train"}
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            normalize_origination([row], self.mapping, release="invented-only", reviewed=True)
        self.assertEqual(len(normalize_origination(
            [row], self.mapping, release="invented-only", reviewed=True,
            ignored_headers=("split",))), 1)

    def test_strict_csv_reader_preserves_explicit_blank_cells(self):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(HEADERS.values())
        writer.writerow(export(dti="", property_type="99").values())
        stream.seek(0)
        rows = read_header_export(stream)
        self.assertFalse(stream.closed)
        self.assertEqual(rows[0][HEADERS["dti"]], "")
        self.assertIsNone(self.normalize(rows)[0]["dti"])

    def test_strict_csv_reader_rejects_ragged_rows_and_header_collisions(self):
        cases = ("a,b\n1\n", "a,b\n1,2,3\n", "a,a\n1,2\n", "a,\n1,2\n",
                 " a,b\n1,2\n", "", "a,b\n\n", 'a,b\n"unterminated,2\n')
        for content in cases:
            with self.subTest(content=content), self.assertRaises(ValueError):
                read_header_export(io.StringIO(content))

    def test_empty_duplicate_and_malformed_exports_fail(self):
        for rows in ([], [export(), export()], [None], [["not", "headers"]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.normalize(rows)

    def test_mapping_typos_reuse_and_ambiguous_dictionaries_fail(self):
        changes = []
        typo = copy.deepcopy(self.mapping)
        typo["property_type"]["code"] = typo["property_type"].pop("codes")
        changes.append(typo)
        reused = copy.deepcopy(self.mapping)
        reused["ltv"]["source"] = HEADERS["dti"]
        changes.append(reused)
        overlap = copy.deepcopy(self.mapping)
        overlap["property_type"]["codes"]["99"] = "condo"
        changes.append(overlap)
        for mapping in changes:
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                self.normalize([export()], mapping)

    def test_malformed_source_bounds_cannot_disable_source_validation(self):
        for bounds in ((65, 0), (0, float("nan")), (False, 65), ("0", "65"), (0,)):
            mapping = copy.deepcopy(self.mapping)
            mapping["dti"]["bounds"] = bounds
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                self.normalize([export()], mapping)

    def test_first_payment_is_never_accepted_as_an_exact_origination_date(self):
        with self.assertRaisesRegex(ValueError, "First payment"):
            freddie_origination_mapping(HEADERS, ltv_regime="pre_2018q2",
                                         date_anchor="first_payment_month")
        for header in ("first_payment_date", "First Payment Month"):
            headers = {**HEADERS, "origination_date": header}
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "First payment"):
                freddie_origination_mapping(headers, ltv_regime="pre_2018q2",
                                             date_anchor="exact_origination_date")

    def test_actual_path_rejects_monthly_proxy_even_with_review_attestation(self):
        mapping = copy.deepcopy(self.mapping)
        mapping["origination_date"].update(date_format="%Y%m", date_anchor="synthetic_month_proxy")
        row = export(origination_date="201701")
        with self.assertRaisesRegex(ValueError, "exact date anchor"):
            normalize_origination([row], mapping, release="invented-only", reviewed=True)
        self.assertEqual(self.normalize([row], mapping)[0]["origination_date"], "2017-01-01")

    def test_public_dictionary_helper_is_not_access_or_review_permission(self):
        with self.assertRaisesRegex(ValueError, "reviewed"):
            normalize_origination([export()], self.mapping, release="invented-only")
        for options in ({"synthetic": "yes"}, {"reviewed": 1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                normalize_origination([export()], self.mapping, release="invented-only", **options)

    def test_aggregate_audit_does_not_expose_invented_keys(self):
        rows = self.normalize([export(dti="999"), export(loan_id="invented-b", property_type="PU")])
        report = audit_cohort(rows + [rows[0]], [
            {"loan_id": "invented-orphan", "month_on_book": "1",
             "delinquency_days": "0", "status": "active"}])
        self.assertEqual(report["origination_rows"], 3)
        self.assertEqual(report["duplicate_origination_rows"], 1)
        self.assertEqual(report["unmatched_performance_rows"], 1)
        self.assertEqual(report["missing_inputs"]["dti"]["count"], 2)
        self.assertFalse(report["normalized_checks_passed"])
        self.assertNotIn("invented-", str(report))

    def test_aggregate_audit_reports_unknown_categories_separately(self):
        row = self.normalize([export()])[0]
        row["property_type"] = "unreviewed_category"
        report = audit_cohort([row], [])
        self.assertEqual(report["invalid_categories"], {"property_type": 1})
        self.assertEqual(report["invalid_numeric_values"], {})
        self.assertFalse(report["normalized_checks_passed"])


if __name__ == "__main__":
    unittest.main()
