"""Phase 1a: harvest in-repo surfaces (CFF, codemeta, .zenodo.json, README, release)."""
import json
import yaml

from ..common import http_get, save_snapshot
from .readme_parser import parse_readme

def _root_listing(repo, cfg):
    r = http_get(f"https://api.github.com/repos/{repo}/contents/", cfg.gh_headers())
    if r is None:
        return {}
    return {item["name"].lower(): item["name"] for item in r.json()}


def _raw_file(repo, branch, actual_name, cfg):
    r = http_get(f"https://raw.githubusercontent.com/{repo}/{branch}/{actual_name}",
                 cfg.ua())
    return r.text if r is not None else None


def harvest_github(row, cfg):
    """Harvest one project's in-repo surfaces. Returns the set of surfaces found."""
    pid, repo = row["project_id"], row["github_repo"]
    meta_r = http_get(f"https://api.github.com/repos/{repo}", cfg.gh_headers())
    if meta_r is None:
        print(f"[{pid}] repo not found, skipping")
        return set()
    meta = meta_r.json()
    branch = meta.get("default_branch", "main")
    save_snapshot(cfg, pid, "github_repo_meta", {
        "full_name": meta.get("full_name"),
        "default_branch": branch,
        "license_spdx": (meta.get("license") or {}).get("spdx_id"),
        "html_url": meta.get("html_url"),
        "archived": meta.get("archived"),
        "pushed_at": meta.get("pushed_at"),
    })

    names = _root_listing(repo, cfg)
    found = set()

    if "citation.cff" in names:
        text = _raw_file(repo, branch, names["citation.cff"], cfg)
        parsed, err = None, None
        try:
            parsed = yaml.safe_load(text) if text else None
        except yaml.YAMLError as e:
            err = str(e)  # an invalid CFF is a finding, not a crash
        save_snapshot(cfg, pid, "cff",
                      {"raw_text": text, "parsed": parsed, "parse_error": err})
        found.add("cff")

    for lower, surface in (("codemeta.json", "codemeta"),
                           (".zenodo.json", "zenodo_json")):
        if lower in names:
            text = _raw_file(repo, branch, names[lower], cfg)
            parsed, err = None, None
            try:
                parsed = json.loads(text) if text else None
            except json.JSONDecodeError as e:
                err = str(e)
            save_snapshot(cfg, pid, surface,
                          {"raw_text": text, "parsed": parsed, "parse_error": err})
            found.add(surface)

    readme_lower = next((n for n in names if n.startswith("readme")), None)
    if readme_lower:
        text = _raw_file(repo, branch, names[readme_lower], cfg)
        if text:
            save_snapshot(cfg, pid, "readme", parse_readme(text))
            found.add("readme")

    rel = http_get(f"https://api.github.com/repos/{repo}/releases/latest",
                   cfg.gh_headers())
    if rel is not None:
        rj = rel.json()
        save_snapshot(cfg, pid, "github_release", {
            "tag_name": rj.get("tag_name"),
            "name": rj.get("name"),
            "published_at": rj.get("published_at"),
        })
        found.add("github_release")
    print(f"[{pid}] harvested: " + (", ".join(sorted(found)) or "nothing"))
    return found

def run_harvest_github(cfg, rows):
    for row in rows:
        harvest_github(row, cfg)
