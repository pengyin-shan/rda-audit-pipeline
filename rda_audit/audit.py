"""Single-project audit primitive: harvest -> normalize -> score for one repository."""
from .harvest.github_surfaces import harvest_github
from .harvest.doi_records import resolve_doi
from .harvest.registries import harvest_registries
from .score.normalize import normalize_project
from .score.score import score_project


def audit_project(row, cfg, fetch=True):
    row = dict(row)
    row.setdefault("doi", "")
    row.setdefault("pypi_package", "")
    row.setdefault("npm_package", "")

    if fetch:
        harvest_github(row, cfg)
        resolve_doi(row, cfg)
        harvest_registries(row, cfg)

    records = normalize_project(row, cfg)
    comparisons, intra, orcid = score_project(
        row["project_id"], records,
        domain=row.get("domain", ""), stratum=row.get("stratum", ""))

    comparable = [c for c in comparisons if c["verdict"] != "missing"]
    agree = [c for c in comparable if c["verdict"] in ("exact", "minor")]
    conflicts = [c for c in comparisons if c["verdict"] == "conflict"]
    summary = {
        "project_id": row["project_id"],
        "surfaces_present": sorted(k for k in records if not k.endswith("__error")),
        "n_comparable": len(comparable),
        "n_agree": len(agree),
        "n_conflict": len(conflicts),
        "agreement": round(len(agree) / len(comparable), 3) if comparable else None,
        "conflict_fields": sorted({c["field"] for c in conflicts}),
    }
    return {"records": records, "comparisons": comparisons,
            "intra_cff": intra, "orcid": orcid, "summary": summary}
