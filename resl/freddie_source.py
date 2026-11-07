"""Verify Freddie Mac acquisition metadata and private local ZIP archives.

No network access, extraction, row analysis, model fitting or source acceptance.
AI-assisted implementation; licensed records remain outside GitHub Actions.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import zipfile


FORMAT = "resl-freddie-source-v1"
SOURCE = "Freddie Mac Single-Family Loan-Level Dataset, Standard vintage samples"
PORTAL = "https://claritydownload.fmapps.freddiemac.com/CRT/#/sflld"
TERMS = "https://capitalmarkets.freddiemac.com/crt/docs/pdfs/fre_terms_conditions_sflld.pdf"
FIELDS = {"format", "source", "downloaded_on", "download_portal", "terms_reference",
          "guide_release", "performance_cutoff", "cohort_status", "archives"}
ARCHIVE_FIELDS = {"vintage_year", "filename", "bytes", "sha256", "members"}


def validate_manifest(manifest):
    """Accept only public provenance fields, not paths, records or credentials."""
    if not isinstance(manifest, dict) or set(manifest) != FIELDS:
        raise ValueError("Unexpected source-manifest fields")
    if (manifest["format"] != FORMAT or manifest["source"] != SOURCE
            or manifest["download_portal"] != PORTAL or manifest["terms_reference"] != TERMS):
        raise ValueError("Expected official Freddie Mac source references")
    try:
        downloaded = date.fromisoformat(manifest["downloaded_on"])
        cutoff = date.fromisoformat(manifest["performance_cutoff"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Source dates must be ISO calendar dates") from exc
    if cutoff > downloaded or downloaded > date.today():
        raise ValueError("Source dates cannot be future dated or inconsistent")
    if not isinstance(manifest["guide_release"], str) or not manifest["guide_release"].strip():
        raise ValueError("Guide release reference is required")
    if manifest["cohort_status"] != "provisional_unassigned":
        raise ValueError("This acquisition manifest does not accept study partitions")
    archives = manifest["archives"]
    if not isinstance(archives, list) or not archives:
        raise ValueError("At least one archive is required")
    seen = set()
    for item in archives:
        if not isinstance(item, dict) or set(item) != ARCHIVE_FIELDS:
            raise ValueError("Unexpected archive fields")
        year = item["vintage_year"]
        if type(year) is not int or not 1999 <= year <= downloaded.year or year in seen:
            raise ValueError("Vintage years must be unique valid integers")
        seen.add(year)
        if item["filename"] != f"sample_{year}.zip":
            raise ValueError("Expected a canonical sample archive filename")
        if type(item["bytes"]) is not int or item["bytes"] <= 0:
            raise ValueError("Archive byte size must be a positive integer")
        digest = item["sha256"]
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("Archive SHA-256 must be 64 lowercase hexadecimal characters")
        expected = [f"sample_orig_{year}.txt", f"sample_perf_{year}.txt"]
        if (not isinstance(item["members"], list)
                or any(not isinstance(name, str) for name in item["members"])
                or sorted(item["members"]) != sorted(expected)):
            raise ValueError("Expected exactly the vintage origination/performance pair")
    return manifest


def verify_archives(manifest, archive_dir):
    """Check size, SHA-256, exact member names and CRC; never extract files."""
    validate_manifest(manifest)
    directory = Path(archive_dir).resolve()
    verified = []
    for item in manifest["archives"]:
        path = directory / item["filename"]
        if path.resolve().parent != directory or not path.is_file():
            raise ValueError(f"Missing or out-of-directory archive: {item['filename']}")
        if path.stat().st_size != item["bytes"]:
            raise ValueError(f"Archive size mismatch: {item['filename']}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != item["sha256"]:
            raise ValueError(f"Archive SHA-256 mismatch: {item['filename']}")
        try:
            with zipfile.ZipFile(path) as archive:
                if sorted(archive.namelist()) != sorted(item["members"]):
                    raise ValueError(f"Unexpected archive members: {item['filename']}")
                if any(info.flag_bits & 1 for info in archive.infolist()):
                    raise ValueError("Encrypted archives are not supported")
                if archive.testzip() is not None:
                    raise ValueError(f"Archive CRC mismatch: {item['filename']}")
        except (zipfile.BadZipFile, RuntimeError) as exc:
            raise ValueError(f"Invalid ZIP archive: {item['filename']}") from exc
        verified.append({key: item[key] for key in ("vintage_year", "filename", "bytes", "sha256")}
                        | {"zip_crc_valid": True})
    return verified


def source_report(manifest, archive_dir=None):
    validate_manifest(manifest)
    verified = verify_archives(manifest, archive_dir) if archive_dir is not None else []
    return {"format": FORMAT, "manifest_valid": True,
            "mode": "metadata_only" if archive_dir is None else "local_archive_verification",
            "local_archives_verified": archive_dir is not None,
            "declared_archives": len(manifest["archives"]), "verified_archives": verified,
            "loan_rows_analyzed": False, "cohorts_accepted": False,
            "model_trained": False, "final_test_evaluated": False,
            "limitation": "Acquisition verification only; source/input/label/split review remains required."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("docs/freddie_source_manifest.json"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--metadata-only", action="store_true")
    mode.add_argument("--archive-dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[1]
        if args.out and not args.out.resolve().is_relative_to(root / "results"):
            raise ValueError("Reports must stay in ignored repository results/ storage")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = source_report(manifest, args.archive_dir)
        text = json.dumps(report, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
