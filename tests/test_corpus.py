import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rda_audit.corpus import (load_corpus, adapt_sampler_corpus,
                              canonical_repo, PIPELINE_FIELDS)

SAMPLER_HEADER = ["name", "repo", "repo_canonical", "stratum",
                  "discipline", "ecosystem", "source"]
SAMPLER_ROWS = [
    ["Kokkos", "kokkos/kokkos", "github.com/kokkos/kokkos",
     "hpc", "performance", "frame", "sc26_corpus"],
    ["Qiskit", "Qiskit/qiskit", "github.com/qiskit/qiskit",
     "qc", "quantum", "frame", "sc26_corpus"],
    # baseline row
    ["AstroA", "https://github.com/a/astroa", "github.com/a/astroa",
     "joss", "astronomy", "baseline", "baseline_joss"],
]

def _write_sampler_csv(path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(SAMPLER_HEADER)
        w.writerows(SAMPLER_ROWS)

def test_canonical_repo():
    assert canonical_repo("https://github.com/A/B.git") == "a/b"
    assert canonical_repo("github.com/a/b/") == "a/b"
    assert canonical_repo("a/b") == "a/b"
    assert canonical_repo("github.com/a/b/tree/master/joss") == "a/b"

def test_guard_refuses_sampler_schema():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "corpus.csv"
        _write_sampler_csv(p)
        try:
            load_corpus(p)
        except SystemExit as e:
            assert "adapt-corpus" in str(e)
        else:
            raise AssertionError("load_corpus accepted a sampler-schema corpus")

def test_adapter_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "sampler.csv"
        out = Path(d) / "corpus.csv"
        _write_sampler_csv(src)
        n = adapt_sampler_corpus(src, out)
        assert n == 3
        rows = load_corpus(out)
        assert len(rows) == 3, "adapter output must load without dropping rows"
        by_id = {r["project_id"]: r for r in rows}
        assert by_id["kokkos"]["stratum"] == "sc26"
        assert by_id["kokkos"]["domain"] == "hpc"
        assert by_id["qiskit"]["domain"] == "qc"
        assert by_id["astroa"]["stratum"] == "joss"
        assert by_id["astroa"]["domain"] == "astronomy"
        assert by_id["astroa"]["github_repo"] == "a/astroa"
        with open(out, newline="") as f:
            assert csv.DictReader(f).fieldnames == PIPELINE_FIELDS

def main():
    test_canonical_repo()
    test_guard_refuses_sampler_schema()
    test_adapter_roundtrip()
    print("all corpus tests pass")

if __name__ == "__main__":
    main()
