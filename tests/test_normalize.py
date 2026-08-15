import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rda_audit.score.normalize import from_zenodo_json, from_cff

def test_zenodo_license_object():
    rec = from_zenodo_json({"title": "X", "creators": [],
                            "license": {"id": "Apache-2.0"}})
    assert rec["license"] == "Apache-2.0"
    rec2 = from_zenodo_json({"title": "X", "creators": [], "license": "MIT"})
    assert rec2["license"] == "MIT"

def test_cff_date_as_string():
    rec = from_cff({"title": "X", "authors": [], "date-released": "2021-09-22"})
    assert rec["year"] == 2021

def test_license_id():
    from rda_audit.score.normalize import _license_id
    full = "MIT License\n\nCopyright (c) 2025 X\n\nPermission is hereby granted..."
    assert _license_id(full) == "MIT License"
    assert _license_id("MIT") == "MIT"
    assert _license_id(None) is None

def test_doi_record_family_only():
    from rda_audit.score.normalize import from_doi_record
    rec = {"resolved": True, "titles": ["x"],
           "creators": [{"name": "Luiz Irber", "given": None,
                         "family": "Luiz Irber", "orcid": None},
                        {"name": "Ada Lovelace", "given": None,
                         "family": None, "orcid": None}]}
    out = from_doi_record(rec)
    a0, a1 = out["authors"]
    assert a0 == {"family": "Luiz Irber", "given": None, "orcid": None}
    assert a1 == {"family": "Lovelace", "given": "Ada", "orcid": None}

def main():
    test_zenodo_license_object()
    test_cff_date_as_string()
    test_license_id()
    test_doi_record_family_only()
    print("all normalize tests pass")

if __name__ == "__main__":
    main()
