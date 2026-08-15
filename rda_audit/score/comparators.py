"""Pairwise consistency comparators. Pure functions, no IO.

Rubric (4 levels): exact = normalized values identical; minor = same referent,
superficial variation (title fuzzy >= 90 token-sort; same author set reordered
or fuzzy-matched; year +/-1; version 'v'-prefix only); conflict = both present,
materially different; missing = at least one side absent. Zenodo
concept-vs-version DOI pairs are flagged HAND-CHECK, not auto-resolved.
Thresholds are part of the registered instrument (v0.2.0): if one changes,
log why and re-run tests/test_comparators.py.
"""
import re
FUZZY=90

from rapidfuzz import fuzz

FIELDS = ("title", "authors", "version", "year", "doi", "license")
SURFACE_ORDER = ["cff", "codemeta", "zenodo_json", "doi_record", "readme", "pypi", "npm"]
LICENSE_ALIASES = {
    "apache 2.0": "apache-2.0", "apache2": "apache-2.0", "apache license 2.0": "apache-2.0",
    "bsd 3-clause": "bsd-3-clause", "bsd": "bsd-3-clause", "new bsd": "bsd-3-clause",
    "gpl v3": "gpl-3.0", "gplv3": "gpl-3.0", "mit license": "mit",
}

def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(s).lower())).strip()

def cmp_title(a, b):
    if not a or not b:
        return "missing", ""
    ca, cb = _clean(a), _clean(b)
    if ca == cb:
        return "exact", ""
    score = fuzz.token_sort_ratio(ca, cb)
    return ("minor", f"fuzzy={score:.0f}") if score >= FUZZY else ("conflict", f"fuzzy={score:.0f} | '{a}' vs '{b}'")

def _author_key(p):
    return _clean(f"{p.get('given') or ''} {p.get('family') or p.get('_entity') or ''}")

def cmp_authors(a, b):
    if not a or not b:
        return "missing", ""
    ka = [_author_key(p) for p in a if _author_key(p)]
    kb = [_author_key(p) for p in b if _author_key(p)]
    if not ka or not kb:
        return "missing", ""
    if ka == kb:
        return "exact", f"n={len(ka)}"
    matched_a = sum(1 for x in ka if any(fuzz.token_sort_ratio(x, y) >= FUZZY for y in kb))
    matched_b = sum(1 for y in kb if any(fuzz.token_sort_ratio(y, x) >= FUZZY for x in ka))
    if matched_a == len(ka) and matched_b == len(kb):
        detail = "order differs" if sorted(ka) == sorted(kb) else "name variants"
        return "minor", f"{detail}; n={len(ka)}"
    return "conflict", f"|A|={len(ka)} |B|={len(kb)} matchedA={matched_a} matchedB={matched_b}"

def cmp_version(a, b):
    if not a or not b:
        return "missing", ""
    va, vb = str(a).strip(), str(b).strip()
    if va == vb:
        return "exact", ""
    if va.lstrip("vV") == vb.lstrip("vV"):
        return "minor", "v-prefix only"
    return "conflict", f"'{va}' vs '{vb}'"

def cmp_year(a, b):
    if a is None or b is None:
        return "missing", ""
    if a == b:
        return "exact", ""
    if abs(int(a) - int(b)) == 1:
        return "minor", f"{a} vs {b} (staleness?)"
    return "conflict", f"{a} vs {b}"

def cmp_doi(a, b):
    if not a or not b:
        return "missing", ""
    if a == b:
        return "exact", ""
    za = a.startswith("10.5281/zenodo."), b.startswith("10.5281/zenodo.")
    if all(za):
        return "conflict", f"{a} vs {b} | both Zenodo: possible concept-vs-version DOI, HAND-CHECK"
    return "conflict", f"{a} vs {b}"

def cmp_license(a, b):
    if not a or not b:
        return "missing", ""
    na = LICENSE_ALIASES.get(_clean(a), _clean(a)).replace(" ", "-")
    nb = LICENSE_ALIASES.get(_clean(b), _clean(b)).replace(" ", "-")
    if na == nb:
        return "exact", "" if str(a) == str(b) else "alias-normalized"
    return "conflict", f"'{a}' vs '{b}'"

COMPARATORS = {"title": cmp_title, "authors": cmp_authors, "version": cmp_version,
               "year": cmp_year, "doi": cmp_doi, "license": cmp_license}
