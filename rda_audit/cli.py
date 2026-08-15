"""CLI entry point; subcommands per phase plus adapt-corpus, probe-candidates, audit-one."""
import argparse
import sys
from . import __version__
from .config import Config
from .corpus import load_corpus, adapt_sampler_corpus
from .profile import run_profile
from .harvest.github_surfaces import run_harvest_github
from .harvest.doi_records import run_harvest_doi
from .harvest.registries import run_harvest_registries
from .score.normalize import run_normalize
from .score.score import run_score
from .analyze import run_analyze
from .audit import audit_project
from .candidates import run_probe_candidates, README_RULES

def _rows(cfg, only):
    rows = load_corpus(cfg)
    if only:
        want = set(only)
        rows = [r for r in rows if r["project_id"] in want]
        missing = want - {r["project_id"] for r in rows}
        if missing:
            raise SystemExit(f"project_id(s) not in corpus: {sorted(missing)}")
    return rows

def main(argv=None):
    ap = argparse.ArgumentParser(prog="rda_audit",
                                 description="Multi-surface software-metadata consistency audit")
    ap.add_argument("--version", action="version", version=f"rda_audit {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--corpus", default=None, help="corpus.csv path (default ./corpus.csv)")
        p.add_argument("--data-dir", default=None, help="data directory (default ./data)")
        p.add_argument("--only", action="append", default=None,
                       help="restrict to this project_id (repeatable)")
        return p
    for name in ("profile", "harvest-github", "harvest-doi", "harvest-registries",
                 "normalize", "score", "analyze", "all"):
        common(sub.add_parser(name))
    p = sub.add_parser("adapt-corpus",
                       help="convert baseline-sampler corpus schema to pipeline schema")
    p.add_argument("--sampler-corpus", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--detected-registry", default=None,
                   help="candidate_availability.csv from probe-candidates, "
                        "to pre-fill verified registry package names")
    p = sub.add_parser("probe-candidates",
                       help="probe six eligibility surfaces for sampler candidates")
    p.add_argument("--candidates", nargs="+", required=True,
                   help="candidates_joss.csv candidates_pyopensci.csv")
    p.add_argument("--out", required=True)
    p.add_argument("--readme-rule", default="section_or_bibtex", choices=README_RULES)
    p.add_argument("--data-dir", default=None)
    p = common(sub.add_parser("audit-one", help="audit a single repository end to end"))
    p.add_argument("--repo", required=True, help="owner/name")
    p.add_argument("--doi", default="")
    p.add_argument("--pypi", default="")
    p.add_argument("--npm", default="")
    p.add_argument("--no-fetch", action="store_true", help="re-score existing snapshots")
    args = ap.parse_args(argv)
    cfg = Config.from_env(corpus_path=getattr(args, "corpus", None),
                          data_dir=getattr(args, "data_dir", None))
    if not cfg.github_token and args.cmd in ("profile", "harvest-github",
                                             "all", "audit-one", "probe-candidates"):
        print("WARNING: GITHUB_TOKEN not set; unauthenticated GitHub limit is "
              "60 req/hr and this run WILL stall. Ctrl-C and export GITHUB_TOKEN.")
    if args.cmd == "adapt-corpus":
        adapt_sampler_corpus(args.sampler_corpus, args.out,
                             detected_registry_path=args.detected_registry)
        return
    if args.cmd == "probe-candidates":
        run_probe_candidates(cfg, args.candidates, args.out,
                             readme_rule=args.readme_rule)
        return
    if args.cmd == "audit-one":
        from .corpus import canonical_repo
        canon = canonical_repo(args.repo)
        row = {"project_id": canon.split("/")[-1], "github_repo": canon,
               "doi": args.doi, "pypi_package": args.pypi, "npm_package": args.npm}
        report = audit_project(row, cfg, fetch=not args.no_fetch)
        import json
        print(json.dumps(report["summary"], indent=2))
        return
    rows = _rows(cfg, args.only)
    steps = {
        "profile": [lambda: run_profile(cfg, rows)],
        "harvest-github": [lambda: run_harvest_github(cfg, rows)],
        "harvest-doi": [lambda: run_harvest_doi(cfg, rows)],
        "harvest-registries": [lambda: run_harvest_registries(cfg, rows)],
        "normalize": [lambda: run_normalize(cfg, rows)],
        "score": [lambda: run_score(cfg, rows)],
        "analyze": [lambda: run_analyze(cfg)],
    }
    steps["all"] = (steps["profile"] + steps["harvest-github"] + steps["harvest-doi"]
                    + steps["harvest-registries"] + steps["normalize"]
                    + steps["score"] + steps["analyze"])
    for i, fn in enumerate(steps[args.cmd]):
        if args.cmd == "all":
            print(f"\n===== step {i + 1}/{len(steps['all'])} =====")
        fn()

if __name__ == "__main__":
    sys.exit(main())
