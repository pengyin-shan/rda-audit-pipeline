"""Normalize harvested surfaces into one canonical record:
{title, authors[{family, given, orcid}], version, year, doi, license}.
CFF preferred-citation is extracted as the pseudo-surface cff_preferred so
intra-file conflicts are measurable. .zenodo.json license objects
({"id": ...}) are unwrapped (live-run defect fix; see README Notes).
"""
import json
import re

from ..common import load_snapshot

def _year(value):
    if value is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(value))
    return int(m.group(0)) if m else None

def _doi_norm(value):
    if not value:
        return None
    d = str(value).strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d.rstrip(".,;") or None

def _person_from_cff(p):
    if not isinstance(p, dict):
        return {"family": None, "given": str(p), "orcid": None}
    orcid = p.get("orcid")
    if orcid:
        orcid = str(orcid).rsplit("/", 1)[-1]
    return {"family": p.get("family-names"), "given": p.get("given-names"), "orcid": orcid,
            "_entity": p.get("name")}  # CFF entities (orgs) have `name`

def from_cff(parsed, preferred=False):
    if not isinstance(parsed, dict):
        return None
    src = parsed.get("preferred-citation") if preferred else parsed
    if not isinstance(src, dict):
        return None
    doi = src.get("doi")
    if not doi:
        for ident in src.get("identifiers", []) or []:
            if isinstance(ident, dict) and ident.get("type") == "doi":
                doi = ident.get("value")
                break
    return {
        "title": src.get("title"),
        "authors": [_person_from_cff(a) for a in src.get("authors", []) or []],
        "version": src.get("version"),
        "year": _year(src.get("date-released") or src.get("year")),
        "doi": _doi_norm(doi),
        "license": src.get("license"),
    }

def _person_from_name(name):
    """Split 'Given Family' / 'Family, Given' heuristically."""
    if not name:
        return None
    name = str(name).strip()
    if "," in name:
        fam, _, giv = name.partition(",")
        return {"family": fam.strip(), "given": giv.strip() or None, "orcid": None}
    parts = name.split()
    if len(parts) == 1:
        return {"family": parts[0], "given": None, "orcid": None}
    return {"family": parts[-1], "given": " ".join(parts[:-1]), "orcid": None}

def from_codemeta(parsed):
    if not isinstance(parsed, dict):
        return None
    authors = []
    raw = parsed.get("author") or parsed.get("creator") or []
    if isinstance(raw, dict):
        raw = [raw]
    for a in raw:
        if isinstance(a, dict):
            orcid = a.get("@id") or a.get("id")
            orcid = orcid.rsplit("/", 1)[-1] if orcid and "orcid" in str(orcid).lower() else None
            fam, giv = a.get("familyName"), a.get("givenName")
            if not fam and a.get("name"):
                p = _person_from_name(a["name"]) or {}
                fam, giv = p.get("family"), p.get("given")
            authors.append({"family": fam, "given": giv, "orcid": orcid})
    lic = parsed.get("license")
    if isinstance(lic, str) and "spdx.org" in lic:
        lic = lic.rstrip("/").rsplit("/", 1)[-1]
    return {
        "title": parsed.get("name"),
        "authors": authors,
        "version": str(parsed["version"]) if parsed.get("version") is not None else None,
        "year": _year(parsed.get("datePublished") or parsed.get("dateCreated")),
        "doi": _doi_norm(parsed.get("identifier") if isinstance(parsed.get("identifier"), str) else None),
        "license": lic,
    }

def _zenodo_license(value):
    if isinstance(value, dict):
        return value.get("id") or value.get("licence") or value.get("license")
    return value

def from_zenodo_json(parsed):
    if not isinstance(parsed, dict):
        return None
    return {
        "title": parsed.get("title"),
        "authors": [
            {**(_person_from_name(c.get("name")) or {}), "orcid": c.get("orcid")}
            for c in parsed.get("creators", []) if isinstance(c, dict)
        ],
        "version": parsed.get("version"),
        "year": _year(parsed.get("publication_date")),
        "doi": _doi_norm(parsed.get("doi")),
        "license": _zenodo_license(parsed.get("license")),
    }

def from_doi_record(rec):
    if not isinstance(rec, dict) or not rec.get("resolved", True):
        return None
    return {
        "title": (rec.get("titles") or [None])[0],
        "authors": [
            {"family": c.get("family") or (_person_from_name(c.get("name")) or {}).get("family"),
             "given": c.get("given") or (_person_from_name(c.get("name")) or {}).get("given"),
             "orcid": c.get("orcid")}
            for c in rec.get("creators", [])
        ],
        "version": rec.get("version"),
        "year": _year(rec.get("publication_year")),
        "doi": _doi_norm(rec.get("doi")),
        "license": (rec.get("rights") or [None])[0],
    }

def from_pypi(rec):
    if not isinstance(rec, dict):
        return None
    author = _person_from_name(rec.get("author") or rec.get("maintainer"))
    return {
        "title": rec.get("name"),
        "authors": [author] if author else [],
        "version": rec.get("version"),
        "year": None,  # PyPI JSON does not expose a stable publication year at info level
        "doi": None,
        "license": rec.get("license_expression") or rec.get("license"),
    }


def from_npm(rec):
    if not isinstance(rec, dict):
        return None
    author = _person_from_name(rec.get("author"))
    return {
        "title": rec.get("name"),
        "authors": [author] if author else [],
        "version": rec.get("version"),
        "year": None,
        "doi": None,
        "license": rec.get("license") if isinstance(rec.get("license"), str) else None,
    }


def from_readme(payload):
    bib = (payload or {}).get("bibtex")
    if not bib:
        return None
    authors = []
    for name in re.split(r"\s+and\s+", bib.get("author", ""), flags=re.IGNORECASE):
        p = _person_from_name(name)
        if p:
            authors.append(p)
    return {
        "title": bib.get("title"),
        "authors": authors,
        "version": bib.get("version"),
        "year": _year(bib.get("year")),
        "doi": _doi_norm(bib.get("doi")),
        "license": None,
    }


EXTRACTORS = {
    "cff": lambda snap: from_cff(snap["payload"].get("parsed")),
    "cff_preferred": lambda snap: from_cff(snap["payload"].get("parsed"), preferred=True),
    "codemeta": lambda snap: from_codemeta(snap["payload"].get("parsed")),
    "zenodo_json": lambda snap: from_zenodo_json(snap["payload"].get("parsed")),
    "doi_record": lambda snap: from_doi_record(snap["payload"]),
    "pypi": lambda snap: from_pypi(snap["payload"]),
    "npm": lambda snap: from_npm(snap["payload"]),
    "readme": lambda snap: from_readme(snap["payload"]),
}
SNAPSHOT_FOR = {"cff_preferred": "cff"}  # pseudo-surfaces read another snapshot

def normalize_project(row, cfg, write=True):
    """Normalize one project's snapshots. Returns the records dict."""
    pid = row["project_id"]
    records = {}
    for surface, extract in EXTRACTORS.items():
        snap = load_snapshot(cfg, pid, SNAPSHOT_FOR.get(surface, surface))
        if snap is None:
            continue
        try:
            rec = extract(snap)
        except Exception as e:  # a malformed file is data, not a crash
            rec = None
            records[surface + "__error"] = str(e)
        if rec:
            records[surface] = rec
    if write:
        cfg.norm.mkdir(parents=True, exist_ok=True)
        (cfg.norm / f"{pid}.json").write_text(
            json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{pid}] normalized surfaces: "
          f"{sorted(k for k in records if not k.endswith('__error'))}")
    return records


def run_normalize(cfg, rows):
    for row in rows:
        normalize_project(row, cfg)
