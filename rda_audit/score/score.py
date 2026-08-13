"""Phase 2b: pairwise scoring across normalized surfaces; stratum carried into output."""
import itertools
import json

from ..common import write_csv
from .comparators import COMPARATORS, FIELDS, SURFACE_ORDER


def score_project(pid, records, domain="", stratum=""):
    comparisons, intra, orcid_rows = [], [], []

    for surface, rec in records.items():
        if surface.endswith("__error") or not isinstance(rec, dict):
            continue
        authors = rec.get("authors") or []
        if authors:
            orcid_rows.append({
                "project_id": pid, "surface": surface, "n_authors": len(authors),
                "n_with_orcid": sum(1 for x in authors if x.get("orcid")),
            })

    if "cff" in records and "cff_preferred" in records:
        for field in FIELDS:
            verdict, detail = COMPARATORS[field](records["cff"].get(field),
                                                 records["cff_preferred"].get(field))
            intra.append({"project_id": pid, "field": field,
                          "verdict": verdict, "detail": detail})

    present = [s for s in SURFACE_ORDER if s in records]
    for sa, sb in itertools.combinations(present, 2):
        for field in FIELDS:
            verdict, detail = COMPARATORS[field](records[sa].get(field),
                                                 records[sb].get(field))
            comparisons.append({"project_id": pid, "domain": domain,
                                "stratum": stratum,
                                "surface_a": sa, "surface_b": sb,
                                "field": field, "verdict": verdict, "detail": detail})
    return comparisons, intra, orcid_rows


def run_score(cfg, rows):
    cfg.results.mkdir(parents=True, exist_ok=True)
    comparisons, intra, orcid_rows = [], [], []
    for row in rows:
        pid = row["project_id"]
        p = cfg.norm / f"{pid}.json"
        if not p.exists():
            continue
        records = json.loads(p.read_text(encoding="utf-8"))
        c, i, o = score_project(pid, records,
                                domain=row.get("domain", ""),
                                stratum=row.get("stratum", ""))
        comparisons.extend(c)
        intra.extend(i)
        orcid_rows.extend(o)
    write_csv(cfg.results / "comparisons.csv", comparisons,
              fieldnames=["project_id", "domain", "stratum",
                          "surface_a", "surface_b", "field", "verdict", "detail"])
    write_csv(cfg.results / "intra_cff.csv", intra)
    write_csv(cfg.results / "orcid_coverage.csv", orcid_rows)
