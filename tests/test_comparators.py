import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rda_audit.score.comparators import (cmp_title, cmp_authors, cmp_version,
                                         cmp_year, cmp_doi, cmp_license)

A = [{"family": "Lovelace", "given": "Ada"}, {"family": "Hopper", "given": "Grace"}]
B = [{"family": "Hopper", "given": "Grace"}, {"family": "Lovelace", "given": "Ada B."}]
C = [{"family": "Turing", "given": "Alan"}]

def test_comparators():
    assert cmp_title("CoolSim", "coolsim")[0] == "exact"
    assert cmp_title("CoolSim: Fast Simulation", "CoolSim - Fast Simulations")[0] == "minor"
    assert cmp_title("CoolSim", "TensorFlow")[0] == "conflict"
    assert cmp_authors(A, B)[0] == "minor"
    assert cmp_authors(A, C)[0] == "conflict"
    assert cmp_version("v2.1.0", "2.1.0")[0] == "minor"
    assert cmp_year(2023, 2024)[0] == "minor"
    assert cmp_doi("10.5281/zenodo.100", "10.5281/zenodo.200")[0] == "conflict"
    assert cmp_license("Apache 2.0", "Apache-2.0")[0] == "exact"
    assert cmp_title(None, "x")[0] == "missing"

def main():
    test_comparators()
    print("all comparator tests pass")

if __name__ == "__main__":
    main()
