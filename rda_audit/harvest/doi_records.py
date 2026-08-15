"""Resolve each project's DOI to its registered metadata record.

DOI priority (first hit wins, provenance recorded):
  1) corpus.csv doi column (hand-curated concept DOI)
  2) CFF doi / identifiers
  3) first DOI in the README citation section
Zenodo DOIs resolve via DataCite; Crossref is the fallback for paper DOIs.
Live-tested against both registries 2026-08-12 (smoke corpus).
Run AFTER harvest-github.
"""
import re
from ..common import http_get, load_snapshot, save_snapshot

DOI_PATTERN = re.compile(r"10\.\d{4,9}/\S+")

def _clean_doi(value):
    if not value:
        return None
    d = str(value).strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = re.sub(r"/(status|badge)\.(svg|png|gif)\S*$", "", d)
    d = d.rstrip(".,;#*")
    m = DOI_PATTERN.search(d)
    return m.group(0) if m else None

def _doi_from_cff(cfg, pid):
    snap = load_snapshot(cfg, pid, "cff")
    cff = (snap or {}).get("payload", {}).get("parsed") or {}
    if not isinstance(cff, dict):
        return None
    if cff.get("doi"):
        return _clean_doi(cff["doi"]), "cff.doi"
    for ident in cff.get("identifiers", []) or []:
        if isinstance(ident, dict) and ident.get("type") == "doi" and ident.get("value"):
            return _clean_doi(ident["value"]), "cff.identifiers"
    return None

def _doi_from_readme(cfg, pid):
    snap = load_snapshot(cfg, pid, "readme")
    payload = (snap or {}).get("payload", {})
    for d in payload.get("dois_in_citation_section", []):
        return _clean_doi(d), "readme.citation_section"
    return None

def pick_doi(row, cfg):
    if (row.get("doi") or "").strip():
        return row["doi"].strip(), "corpus.csv"
    pid = row["project_id"]
    return _doi_from_cff(cfg, pid) or _doi_from_readme(cfg, pid) or (None, None)

def fetch_datacite(doi, cfg):
    r = http_get(f"https://api.datacite.org/dois/{doi}", cfg.ua())
    if r is None:
        return None
    a = r.json().get("data", {}).get("attributes", {})
    return {
        "registry": "datacite",
        "doi": a.get("doi"),
        "titles": [t.get("title") for t in a.get("titles", []) if t.get("title")],
        "creators": [
            {
                "name": c.get("name"),
                "given": c.get("givenName"),
                "family": c.get("familyName"),
                "orcid": next((i.get("nameIdentifier") for i in c.get("nameIdentifiers", [])
                               if "orcid" in (i.get("nameIdentifierScheme") or "").lower()), None),
            }
            for c in a.get("creators", [])
        ],
        "version": a.get("version"),
        "publication_year": a.get("publicationYear"),
        "rights": [x.get("rightsIdentifier") or x.get("rights") for x in a.get("rightsList", [])],
        "publisher": a.get("publisher"),
        "relatedIdentifiers": a.get("relatedIdentifiers", []),
    }

def fetch_crossref(doi, cfg):
    r = http_get(f"https://api.crossref.org/works/{doi}", cfg.ua())
    if r is None:
        return None
    m = r.json().get("message", {})
    return {
        "registry": "crossref",
        "doi": m.get("DOI"),
        "titles": m.get("title", []),
        "creators": [{"name": None, "given": a.get("given"), "family": a.get("family"),
                      "orcid": (a.get("ORCID") or "").replace("http://orcid.org/", "").replace("https://orcid.org/", "") or None}
                     for a in m.get("author", [])],
        "version": None,
        "publication_year": (m.get("issued", {}).get("date-parts", [[None]])[0][0]),
        "rights": [],
        "publisher": m.get("publisher"),
    }

def resolve_doi(row, cfg):
    """Resolve and snapshot one project's DOI record. Returns the record or None."""
    pid = row["project_id"]
    doi, source = pick_doi(row, cfg)
    if not doi:
        print(f"[{pid}] no DOI found on any surface")
        return None
    rec = fetch_datacite(doi, cfg) or fetch_crossref(doi, cfg)
    if rec is None:
        print(f"[{pid}] DOI {doi} did not resolve at DataCite or Crossref")
        save_snapshot(cfg, pid, "doi_record",
                      {"doi": doi, "doi_source": source, "resolved": False})
        return None
    rec.update({"doi_source": source, "resolved": True})
    save_snapshot(cfg, pid, "doi_record", rec)
    print(f"[{pid}] {doi} ({source}) -> {rec['registry']}")
    return rec

def run_harvest_doi(cfg, rows):
    for row in rows:
        resolve_doi(row, cfg)
