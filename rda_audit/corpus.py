"""Corpus loading and the baseline-sampler schema adapter:
PIPELINE schema: project_id, github_repo, domain, doi, pypi_package, npm_package, stratum, source. The SAMPLER schema differs (name, repo, repo_canonical, stratum, discipline, ecosystem, source) and carries an
asymmetry inherited from export_corpus.py: for sc26 rows the sampler's `stratum` column holds hpc/qc and `discipline` the discipline; for baseline rows `stratum` holds joss/pyopensci and `discipline` the domain_bin. adapt_sampler_corpus resolves this. 
load_corpus REFUSES sampler-schema files loudly (the v0.1 loader silently dropped every such row). canonical_repo truncates deep GitHub URLs (.../tree/...) to the owner/name identity.
"""
import csv
import re
from pathlib import Path

PIPELINE_FIELDS = ["project_id", "github_repo", "domain", "doi",
                   "pypi_package", "npm_package", "stratum", "source"]
SAMPLER_FIELDS = {"name", "repo", "repo_canonical", "stratum",
                  "discipline", "ecosystem", "source"}

def canonical_repo(repo: str) -> str:
    r = (repo or "").strip().lower()
    had_gh = False
    for prefix in ("https://github.com/", "http://github.com/",
                   "https://www.github.com/", "github.com/"):
        if r.startswith(prefix):
            r = r[len(prefix):]
            had_gh = True
            break
    if r.endswith(".git"):
        r = r[:-4]
    r = r.strip("/")
    if had_gh:
        r = "/".join(r.split("/")[:2])
    return r

def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "project"

def load_corpus(cfg_or_path):
    """Load the pipeline-schema corpus. Accepts a Config or a path."""
    path = getattr(cfg_or_path, "corpus_path", cfg_or_path)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = set(reader.fieldnames or [])
        if "github_repo" not in header:
            if header >= SAMPLER_FIELDS or "repo_canonical" in header:
                raise SystemExit(
                    f"{path} is in baseline-sampler schema, not pipeline schema.\n"
                    "Run the adapter first:\n"
                    "    python3 -m rda_audit adapt-corpus --sampler-corpus "
                    f"{path} --out corpus.csv\n"
                    "Loading it directly would silently drop every row."
                )
            raise SystemExit(
                f"{path} lacks a github_repo column; expected pipeline schema: "
                + ",".join(PIPELINE_FIELDS)
            )
        rows = [r for r in reader if (r.get("github_repo") or "").strip()]
    for r in rows:
        r["project_id"] = r["project_id"].strip()
        r["github_repo"] = r["github_repo"].strip()
        r.setdefault("stratum", "")
        r.setdefault("source", "")
    return rows


def adapt_sampler_corpus(sampler_path, out_path,
                         detected_registry_path=None) -> int:
    detected = {}
    if detected_registry_path and Path(detected_registry_path).exists():
        with open(detected_registry_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                detected[row.get("repo_canonical", "")] = {
                    "pypi": (row.get("pypi_package_detected") or "").strip(),
                    "npm": (row.get("npm_package_detected") or "").strip(),
                }
    with open(sampler_path, newline="", encoding="utf-8") as f:
        src = list(csv.DictReader(f))
    out_rows, seen_ids, seen_repos = [], {}, set()
    for r in src:
        canon = canonical_repo(r.get("repo_canonical") or r.get("repo") or "")
        if not canon or "/" not in canon:
            raise SystemExit(f"Row without a usable repo: {r}")
        if canon in seen_repos:
            raise SystemExit(f"Duplicate repo in sampler corpus: {canon}")
        seen_repos.add(canon)

        pid = _slug(canon.split("/")[-1])
        if pid in seen_ids:
            seen_ids[pid] += 1
            pid = f"{pid}-{seen_ids[pid]}"
        else:
            seen_ids[pid] = 1
        source = (r.get("source") or "").strip()
        if source.startswith("sc26"):
            stratum = "sc26"
            domain = (r.get("stratum") or "").strip()      # hpc/qc lives here
        else:
            stratum = (r.get("stratum") or "").strip()      # joss/pyopensci
            domain = (r.get("discipline") or "").strip()    # sampler domain_bin
        det = detected.get(canon, {})
        out_rows.append({
            "project_id": pid,
            "github_repo": canon,
            "domain": domain,
            "doi": "",
            "pypi_package": det.get("pypi", ""),
            "npm_package": det.get("npm", ""),
            "stratum": stratum,
            "source": source,
        })
    out_path = Path(out_path)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PIPELINE_FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {out_path}: {len(out_rows)} rows "
          f"({sum(1 for r in out_rows if r['stratum'] == 'sc26')} sc26, "
          f"{sum(1 for r in out_rows if r['stratum'] == 'joss')} joss, "
          f"{sum(1 for r in out_rows if r['stratum'] == 'pyopensci')} pyopensci)")
    print("Now hand-fill the doi column (your curated concept DOIs win over "
          "auto-discovery) and review any pre-filled registry names.")
    return len(out_rows)
