"""Phase 1c: harvest PyPI/npm records where corpus names them. Spack deferred."""
from ..common import http_get, save_snapshot

def fetch_pypi(pkg, cfg):
    r = http_get(f"https://pypi.org/pypi/{pkg}/json", cfg.ua())
    if r is None:
        return None
    info = r.json().get("info", {})
    return {
        "name": info.get("name"),
        "version": info.get("version"),
        "summary": info.get("summary"),
        "author": info.get("author"),
        "author_email": info.get("author_email"),
        "maintainer": info.get("maintainer"),
        "license": info.get("license"),
        "license_expression": info.get("license_expression"),
        "project_urls": info.get("project_urls"),
        "home_page": info.get("home_page"),
    }

def fetch_npm(pkg, cfg):
    r = http_get(f"https://registry.npmjs.org/{pkg}", cfg.ua())
    if r is None:
        return None
    j = r.json()
    latest_tag = (j.get("dist-tags") or {}).get("latest")
    latest = (j.get("versions") or {}).get(latest_tag, {}) if latest_tag else {}
    author = latest.get("author") or j.get("author")
    if isinstance(author, dict):
        author = author.get("name")
    return {
        "name": j.get("name"),
        "version": latest_tag,
        "description": j.get("description"),
        "author": author,
        "maintainers": [m.get("name") for m in (j.get("maintainers") or []) if isinstance(m, dict)],
        "license": latest.get("license") or j.get("license"),
        "repository": (latest.get("repository") or {}).get("url") if isinstance(latest.get("repository"), dict) else latest.get("repository"),
    }

def harvest_registries(row, cfg):
    """Harvest one project's registry surfaces. Returns dict of found records."""
    pid = row["project_id"]
    found = {}
    if (row.get("pypi_package") or "").strip():
        rec = fetch_pypi(row["pypi_package"].strip(), cfg)
        if rec:
            save_snapshot(cfg, pid, "pypi", rec)
            found["pypi"] = rec
            print(f"[{pid}] pypi {rec['name']} v{rec['version']}")
    if (row.get("npm_package") or "").strip():
        rec = fetch_npm(row["npm_package"].strip(), cfg)
        if rec:
            save_snapshot(cfg, pid, "npm", rec)
            found["npm"] = rec
            print(f"[{pid}] npm {rec['name']} v{rec['version']}")
    return found

def run_harvest_registries(cfg, rows):
    for row in rows:
        harvest_registries(row, cfg)
