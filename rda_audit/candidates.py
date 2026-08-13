"""Availability probe for baseline-sampler candidates.

Writes the CSV accept_candidates.py expects:
  repo_canonical, cff, codemeta, zenodo_json, readme_citation, doi_record, registry

Surface definitions (fixed for the registered eligibility filter, >=2 of six):
  cff / codemeta / zenodo_json : file present in the repository root
  readme_citation : README present AND the parser finds a citation section or
      a BibTeX block (--readme-rule: section_or_bibtex [default, used for the
      registered run] | section_only | any_doi)
  doi_record : a DOI is discoverable from CFF or the README citation section
      (harvest priority order; not resolved at probe time)
  registry : a PyPI or npm package matching the repository name part links
      back to the repository (project_urls / home_page / repository field);
      detected names are recorded for hand review. Conservative by design:
      misses lower a candidate's surface count, never raise it.

Non-GitHub candidates are rejected loudly; the R5 platform rule belongs in sample_baseline, not here.
"""
import csv
from pathlib import Path
from .common import http_get, write_csv
from .corpus import canonical_repo
from .harvest.readme_parser import parse_readme, find_dois

README_RULES = ("section_or_bibtex", "section_only", "any_doi")

def _registry_check_pypi(name, canon, cfg):
    r = http_get(f"https://pypi.org/pypi/{name}/json", cfg.ua())
    if r is None:
        return None
    info = r.json().get("info", {})
    urls = list((info.get("project_urls") or {}).values()) + [info.get("home_page") or ""]
    if any(canon in (u or "").lower() for u in urls):
        return info.get("name") or name
    return None

def _registry_check_npm(name, canon, cfg):
    r = http_get(f"https://registry.npmjs.org/{name}", cfg.ua())
    if r is None:
        return None
    j = r.json()
    repo = j.get("repository")
    if isinstance(repo, dict):
        repo = repo.get("url")
    if repo and canon in str(repo).lower():
        return j.get("name") or name
    return None

def probe_candidate(repo_canonical, cfg, readme_rule="section_or_bibtex"):
    canon = canonical_repo(repo_canonical)
    out = {"repo_canonical": repo_canonical, "repo_found": 0,
           "cff": 0, "codemeta": 0, "zenodo_json": 0, "readme_citation": 0,
           "doi_record": 0, "registry": 0,
           "pypi_package_detected": "", "npm_package_detected": ""}
    base = f"https://api.github.com/repos/{canon}"
    meta_r = http_get(base, cfg.gh_headers())
    if meta_r is None:
        print(f"[{canon}] repo NOT FOUND")
        return out
    out["repo_found"] = 1
    branch = meta_r.json().get("default_branch", "main")

    listing = http_get(base + "/contents/", cfg.gh_headers())
    names = {item["name"].lower(): item["name"]
             for item in (listing.json() if listing else [])}
    out["cff"] = int("citation.cff" in names)
    out["codemeta"] = int("codemeta.json" in names)
    out["zenodo_json"] = int(".zenodo.json" in names)
    parsed_readme, readme_text = None, None
    readme_lower = next((n for n in names if n.startswith("readme")), None)
    if readme_lower:
        r = http_get(f"https://raw.githubusercontent.com/{canon}/{branch}/"
                     f"{names[readme_lower]}", cfg.ua())
        readme_text = r.text if r is not None else None
        if readme_text:
            parsed_readme = parse_readme(readme_text)
            if readme_rule == "section_only":
                out["readme_citation"] = int(parsed_readme["has_citation_section"])
            elif readme_rule == "any_doi":
                out["readme_citation"] = int(bool(parsed_readme["dois_anywhere"]))
            else:  # section_or_bibtex
                out["readme_citation"] = int(parsed_readme["has_citation_section"]
                                             or bool(parsed_readme["bibtex"]))
    doi_found = False
    if out["cff"]:
        r = http_get(f"https://raw.githubusercontent.com/{canon}/{branch}/"
                     f"{names['citation.cff']}", cfg.ua())
        if r is not None and find_dois(r.text):
            doi_found = True
    if not doi_found and parsed_readme and parsed_readme["dois_in_citation_section"]:
        doi_found = True
    out["doi_record"] = int(doi_found)

    name_part = canon.split("/")[-1]
    pypi = _registry_check_pypi(name_part, canon, cfg)
    if pypi:
        out["registry"] = 1
        out["pypi_package_detected"] = pypi
    npm = _registry_check_npm(name_part, canon, cfg)
    if npm:
        out["registry"] = 1
        out["npm_package_detected"] = npm
    n = sum(out[s] for s in ("cff", "codemeta", "zenodo_json",
                             "readme_citation", "doi_record", "registry"))
    print(f"[{canon}] surfaces={n} cff={out['cff']} codemeta={out['codemeta']} "
          f".zenodo={out['zenodo_json']} readme_cit={out['readme_citation']} "
          f"doi={out['doi_record']} registry={out['registry']}")
    return out

def run_probe_candidates(cfg, candidate_csvs, out_path,
                         readme_rule="section_or_bibtex"):
    """Probe every candidate in the given CSVs (rank order preserved)."""
    if readme_rule not in README_RULES:
        raise SystemExit(f"readme_rule must be one of {README_RULES}")
    rows, seen = [], set()
    for path in candidate_csvs:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                canon = row.get("repo_canonical") or ""
                if not canon or canon in seen:
                    continue
                if not canonical_repo(canon).startswith("github.com/") \
                        and "." in canonical_repo(canon).split("/")[0]:
                    raise SystemExit(
                        f"non-GitHub candidate reached the probe: {canon}. "
                        "Apply R5 in sample_baseline before probing.")
                seen.add(canon)
                rows.append(probe_candidate(canon, cfg, readme_rule))
    write_csv(Path(out_path), rows)
    print(f"readme_citation rule used: {readme_rule} "
          "(record this in the lab notebook with the pre-registration)")
    return rows
