# RDA Metadata-Consistency Audit Pipeline
**Status: v0.2.0. Draft instrument, smoke-tested end-to-end on a 5-project
sample under v0.1; restructured as an importable library with logic-identical
harvest, normalization, and scoring.**

## Setup
```bash
pip install -e .
export GITHUB_TOKEN=ghp_...
export AUDIT_CONTACT=you@example.edu
```

## Corpus schema (canonical)
`corpus.csv` columns:
`project_id,github_repo,domain,doi,pypi_package,npm_package,stratum,source`
- `github_repo` is the `owner/name` form; `doi` is your hand-curated concept DOI when you know it (it wins over auto-discovery)
- `stratum` is the analysis stratum (`sc26` | `joss` | `pyopensci`)
- The baseline-sampler writes a DIFFERENT schema; never feed it directly. The loader refuses it; convert with `adapt-corpus` (below).

## End-to-end sequence for the real study (order matters)
```bash
python3 export_corpus.py --out corpus.csv          
python3 fetch_frames.py                            
python3 sample_baseline.py --seed <SEED> --oversample 30

python3 -m rda_audit probe-candidates \
    --candidates ../baseline-sampler/out/candidates_joss.csv \
                 ../baseline-sampler/out/candidates_pyopensci.csv \
    --out ../baseline-sampler/out/candidate_availability.csv
    
python3 accept_candidates.py \
    --availability out/candidate_availability.csv --corpus corpus.csv
#   -> corpus.csv now holds 87 + accepted baseline rows (SAMPLER schema)

python3 -m rda_audit adapt-corpus \
    --sampler-corpus ../baseline-sampler/corpus.csv --out corpus.csv \
    --detected-registry ../baseline-sampler/out/candidate_availability.csv

python3 -m rda_audit profile
python3 -m rda_audit harvest-github
python3 -m rda_audit harvest-doi
python3 -m rda_audit harvest-registries   
python3 -m rda_audit normalize
python3 -m rda_audit score
python3 -m rda_audit analyze
# or, for clean re-runs:  python3 -m rda_audit all   (or python3 run_all.py)
```

## Note
- probe guard bug: duplicate host check after prefix strip rejected all candidates; removed 2026-08-12, no probe output existed prior.
- canonical_repo truncated deep GitHub URLs to owner/name, 2026-08-12; 12 such records in frame, 1 in window, no R1/dedup side effects.
- Record JOSS accepted 15 and pyOpenSci accepted 15 at commit 171c8d856ea7cd335536c6c871c9968cf5b350ac.
- When manually verifying DOIs, noticed that for some repos, the Zenodo archive exists but the CITATION.CFF never mention it or README includes both badge for Software DOI but recommending to cite paper instead.
- one npm detection removed for corpus.csv on review as community-published, not project-controlled.
