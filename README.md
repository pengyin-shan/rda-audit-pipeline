# RDA Metadata-Consistency Audit Pipeline

Audit pipeline for cross-surface consistency of software citation metadata: harvest a project's self-description surfaces (CITATION.cff, codemeta.json, .zenodo.json, DOI record, PyPI/npm, README), normalize to six fields, score every pair, and report where they disagree.

**Paper:** Shan, P. (2026). A Multi-Surface Consistency Audit of Software Citation Metadata. arXiv:2608.17159. https://doi.org/10.48550/arXiv.2608.17159
**Software:** https://doi.org/10.5281/zenodo.21969695 (concept DOI) ·
**Data, snapshots, verification log:** https://doi.org/10.5281/zenodo.21969769

## Status
v0.2.2 produced every number reported in the paper. v0.2.3 adds LICENSE, CITATION.cff and this README; measurement code is identical. v0.2.4 update information for paper. v0.2.5 updates pyproject.toml for author information and CITATION.cff to reflect the new release date (2026-10-01) and version (0.2.5).

Tags v0.2.0 and v0.2.1 point to the same squashed commit (public history was flattened before release); the stage history those tags name is documented in the paper, §3.5.

## Cite
See [CITATION.cff](CITATION.cff), or use GitHub's "Cite this repository" button.

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
> Refer to https://github.com/pengyin-shan/baseline-sampler for baseline-sampler details.

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

## Version history

The public history of this repository was flattened when it was made public; tags v0.2.0 and v0.2.1 therefore point to the same squashed commit. The version designations refer to instrument stages documented in the accompanying paper (Section 3.5):

- **v0.2.0** — pre-run instrument. Two defect classes found in pre-run
  live testing (YAML date serialization in CITATION.cff snapshots;
  .zenodo.json license objects) were fixed before any measurement.
- **v0.2.1** — first-run corrections: DOI-string hygiene (resolver-URL
  prefixes, badge-image suffixes, non-DOI identifier values).
- **v0.2.2** — verification-phase corrections (brace-matching BibTeX
  extraction; PyPI license normalization; DataCite familyName
  token-duplication fix), plus the final verification log and
  sensitivity outputs. **v0.2.2 produced every number reported in the
  paper.**
- **v0.2.3** — packaging only (LICENSE, CITATION.cff, README);
  measurement code identical to v0.2.2.
- **v0.2.4** — updated citation and README to reflect the new DOI for the paper (10.48550/arXiv.2608.17159).
- **v0.2.5** — updated pyproject.toml for author information and CITATION.cff to reflect the new release date (2026-10-01) and version (0.2.5).

## Run log (study provenance)
- probe guard bug: duplicate host check after prefix strip rejected all candidates; removed 2026-08-12, no probe output existed prior.
- canonical_repo truncated deep GitHub URLs to owner/name, 2026-08-12; 12 such records in frame, 1 in window, no R1/dedup side effects.
- Record JOSS accepted 15 and pyOpenSci accepted 15 at commit 171c8d856ea7cd335536c6c871c9968cf5b350ac.
- When manually verifying DOIs, noticed that for some repos, the Zenodo archive exists but the CITATION.CFF never mention it or README includes both badge for Software DOI but recommending to cite paper instead.
- one npm detection removed for corpus.csv on review as community-published, not project-controlled.
- Pre-run instrument and locked corpus: commit e706b2cc786f28d882eb7d0f5dbcc4ce05cf6702.
- One curation error (paper DOIs) caught at first-run review, emptied before verification stage.
- For adaptivecpp, lcoi, or thread-pool rows, the verdicts are now built on paper-DOI records that the projects themselves declared.
- Registry detections were hand-reviewed; two (qiskit npm, fluidx3d PyPI) were removed as packages not controlled by the project.
- Hand verification identified one systematic normalization defect (DataCite creator records carrying full names in familyName caused token duplication and depressed author matching); it was corrected and the affected comparisons re-scored and re-verified.
- Freeze raw snapshots (sha256): b76f47aae6b63a1589aae6161695a7561fed9f632b28e7fe7351d98b597c8f06  