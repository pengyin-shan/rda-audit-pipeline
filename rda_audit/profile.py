"""Phase 0: profile which metadata surfaces exist per project (availability matrix)."""
from .common import http_get, write_csv

def profile(row, cfg):
    repo = row["github_repo"]
    base = f"https://api.github.com/repos/{repo}"
    out = {
        "project_id": row["project_id"],
        "github_repo": repo,
        "domain": row.get("domain", ""),
        "stratum": row.get("stratum", ""),
        "source": row.get("source", ""),
    }
    r = http_get(base, cfg.gh_headers())
    if r is None:
        out["repo_found"] = 0
        print(f"[{row['project_id']}] repo NOT FOUND")
        return out
    meta = r.json()
    out["repo_found"] = 1
    out["default_branch"] = meta.get("default_branch", "main")
    out["license_spdx"] = (meta.get("license") or {}).get("spdx_id", "") or ""
    out["archived"] = int(bool(meta.get("archived")))

    listing = http_get(base + "/contents/", cfg.gh_headers())
    names = {item["name"].lower(): item["name"]
             for item in (listing.json() if listing else [])}
    out["citation_cff"] = int("citation.cff" in names)
    out["codemeta_json"] = int("codemeta.json" in names)
    out["zenodo_json"] = int(".zenodo.json" in names)
    out["readme"] = int(any(n.startswith("readme") for n in names))
    out["security_md"] = int("security.md" in names)

    rel = http_get(base + "/releases/latest", cfg.gh_headers())
    out["has_release"] = int(rel is not None)

    out["doi_in_corpus"] = int(bool((row.get("doi") or "").strip()))
    out["pypi_listed"] = 0
    out["npm_listed"] = 0
    if (row.get("pypi_package") or "").strip():
        out["pypi_listed"] = int(
            http_get(f"https://pypi.org/pypi/{row['pypi_package'].strip()}/json",
                     cfg.ua()) is not None
        )
    if (row.get("npm_package") or "").strip():
        out["npm_listed"] = int(
            http_get(f"https://registry.npmjs.org/{row['npm_package'].strip()}",
                     cfg.ua()) is not None
        )

    surfaces = (out["citation_cff"] + out["codemeta_json"] + out["zenodo_json"]
                + out["doi_in_corpus"] + out["pypi_listed"] + out["npm_listed"])
    out["n_structured_surfaces"] = surfaces
    print(f"[{row['project_id']}] cff={out['citation_cff']} codemeta={out['codemeta_json']} "
          f".zenodo={out['zenodo_json']} readme={out['readme']} release={out['has_release']}")
    return out


def run_profile(cfg, rows):
    cfg.results.mkdir(parents=True, exist_ok=True)
    out = [profile(r, cfg) for r in rows]
    write_csv(cfg.results / "availability_matrix.csv", out)
    found = [r for r in out if r.get("repo_found")]
    if found:
        n = len(found)
        print(f"\n=== Availability over {n} resolvable projects ===")
        for k in ("citation_cff", "codemeta_json", "zenodo_json", "readme",
                  "security_md", "has_release", "doi_in_corpus"):
            c = sum(r.get(k, 0) for r in found)
            print(f"  {k:15s} {c:3d}/{n}  ({100*c/n:.0f}%)")
    return out
