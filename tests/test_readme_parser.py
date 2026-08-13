import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rda_audit.harvest.readme_parser import parse_readme

DEMO = """# CoolSim
Fast simulations.
## How to Cite
Please cite our paper (doi:10.5281/zenodo.1234567):
```
@article{cool2024, title={CoolSim: Fast Things}, author={Ada Lovelace and Grace Hopper},
year={2024}, doi={10.1000/xyz123},
}
```
## License
MIT
"""

def test_parse_readme():
    out = parse_readme(DEMO)
    assert out["has_citation_section"]
    assert "10.5281/zenodo.1234567" in out["dois_in_citation_section"]
    assert out["bibtex"]["title"] == "CoolSim: Fast Things"
    assert out["bibtex"]["year"] == "2024"
    assert out["bibtex"]["doi"] == "10.1000/xyz123"

def test_no_citation():
    out = parse_readme("# Plain\nNothing to cite here.")
    assert not out["has_citation_section"]
    assert out["bibtex"] is None
    assert out["dois_in_citation_section"] == []

def main():
    test_parse_readme()
    test_no_citation()
    print("all readme parser tests pass")

if __name__ == "__main__":
    main()
