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

def main():
    test_zenodo_license_object()
    test_cff_date_as_string()
    print("all normalize tests pass")

if __name__ == "__main__":
    main()
