"""Source checks on invented ZIP contents; no licensed rows in CI."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from resl.freddie_source import FORMAT, SOURCE, PORTAL, TERMS, source_report, validate_manifest


class FreddieSourceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.directory = Path(self.folder.name)
        self.path = self.directory / "sample_2016.zip"
        self.members = ["sample_orig_2016.txt", "sample_perf_2016.txt"]
        with zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_STORED) as z:
            for name in self.members:
                z.writestr(name, "INVENTED SOFTWARE FIXTURE; NOT LOAN DATA\n")
        self.manifest = {"format": FORMAT, "source": SOURCE, "downloaded_on": "2026-11-07",
                         "download_portal": PORTAL, "terms_reference": TERMS,
                         "guide_release": "48, October 2026", "performance_cutoff": "2026-06-30",
                         "cohort_status": "provisional_unassigned", "archives": [{
                             "vintage_year": 2016, "filename": self.path.name,
                             "bytes": self.path.stat().st_size,
                             "sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(),
                             "members": self.members}]}

    def test_metadata_mode_never_claims_files_verified(self):
        self.path.unlink()
        report = source_report(self.manifest)
        self.assertTrue(report["manifest_valid"])
        self.assertFalse(report["local_archives_verified"])
        self.assertEqual(report["verified_archives"], [])

    def test_local_integrity_pass_has_no_paths_or_loan_contents(self):
        report = source_report(self.manifest, self.directory)
        self.assertTrue(report["local_archives_verified"])
        self.assertTrue(report["verified_archives"][0]["zip_crc_valid"])
        for flag in ("loan_rows_analyzed", "cohorts_accepted", "model_trained", "final_test_evaluated"):
            self.assertFalse(report[flag])
        self.assertNotIn(str(self.directory), json.dumps(report))
        self.assertNotIn("INVENTED SOFTWARE", json.dumps(report))

    def test_missing_archive_fails_instead_of_falling_back_to_metadata(self):
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            source_report(self.manifest, self.directory)

    def test_size_and_hash_mismatches_fail(self):
        for key, value in (("bytes", 1), ("sha256", "0" * 64)):
            manifest = copy.deepcopy(self.manifest)
            manifest["archives"][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "mismatch"):
                source_report(manifest, self.directory)

    def test_extra_members_rejected_even_with_updated_file_digest(self):
        with zipfile.ZipFile(self.path, "a") as z:
            z.writestr("unexpected.txt", "invented")
        self.manifest["archives"][0].update(
            bytes=self.path.stat().st_size,
            sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, "Unexpected archive members"):
            source_report(self.manifest, self.directory)

    def test_bad_crc_rejected_even_when_archive_digest_matches(self):
        raw = bytearray(self.path.read_bytes())
        raw[raw.index(b"INVENTED SOFTWARE")] ^= 1
        self.path.write_bytes(raw)
        self.manifest["archives"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, "Invalid ZIP|CRC"):
            source_report(self.manifest, self.directory)

    def test_paths_secret_fields_and_false_source_references_rejected(self):
        for change in ({"local_path": "/private/path"}, {"credential": "invented"},
                       {"download_portal": "https://example.com"}, {"format": "wrong"},
                       {"cohort_status": "accepted"}, {"downloaded_on": "2999-01-01"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_manifest(self.manifest | change)

    def test_unsafe_names_hashes_years_and_sizes_rejected(self):
        for key, value in (("filename", "../sample_2016.zip"), ("vintage_year", True),
                           ("bytes", True), ("bytes", 0), ("sha256", "A" * 64),
                           ("members", ["sample_orig_2016.txt", "../escape"])):
            manifest = copy.deepcopy(self.manifest)
            manifest["archives"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_manifest(manifest)

    def test_duplicate_and_empty_archives_rejected(self):
        for items in ([], self.manifest["archives"] * 2):
            with self.subTest(items=items), self.assertRaises(ValueError):
                validate_manifest(self.manifest | {"archives": items})

    def test_cli_requires_an_explicit_mode(self):
        result = subprocess.run([sys.executable, "-m", "resl.freddie_source"],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("required", result.stderr)

    def test_cli_metadata_validates_committed_manifest_without_local_data(self):
        result = subprocess.run([sys.executable, "-m", "resl.freddie_source", "--metadata-only"],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["local_archives_verified"])

    def test_cli_cannot_overwrite_a_tracked_file(self):
        destination = self.directory / "report.json"
        result = subprocess.run([sys.executable, "-m", "resl.freddie_source", "--metadata-only",
                                 "--out", str(destination)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(destination.exists())
