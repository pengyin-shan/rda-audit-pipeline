"""Phase 3: aggregate comparisons into stats and figures, incl. per-stratum outputs."""
import json
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

CORE_FIELDS = ["title", "authors", "version", "year", "doi"]
VERDICT_ORDER = ["exact", "minor", "conflict", "missing"]
COLORS = {"exact": "#2a9d8f", "minor": "#e9c46a", "conflict": "#e76f51", "missing": "#d0d0d0"}

def availability_figure(cfg):
    avail_p = cfg.results / "availability_matrix.csv"
    if not avail_p.exists():
        return
    av = pd.read_csv(avail_p)
    cols = [c for c in ("citation_cff", "codemeta_json", "zenodo_json", "readme",
                        "security_md", "has_release", "doi_in_corpus", "pypi_listed") if c in av.columns]
    found = av[av.repo_found == 1]
    (found[cols].mean().sort_values() * 100).plot(kind="barh", figsize=(7, 4), color="#457b9d")
    plt.xlabel("% of projects with surface present")
    plt.title(f"Surface availability (n={len(found)})")
    plt.tight_layout()
    plt.savefig(cfg.results / "fig_availability.png", dpi=200)
    plt.close()
    print("wrote fig_availability.png")


def run_analyze(cfg):
    comp_path = cfg.results / "comparisons.csv"
    comp = pd.read_csv(comp_path) if comp_path.exists() and comp_path.stat().st_size else pd.DataFrame()
    if comp.empty or "verdict" not in comp.columns or not len(comp):
        print("No cross-surface comparisons yet: projects need >=2 normalized surfaces.")
        print("(Check data/normalized/*.json - add DOIs/registry names to corpus.csv to add surfaces.)")
        availability_figure(cfg)
        return
    stats = {}

    per_field = (comp.groupby(["field", "verdict"]).size().unstack(fill_value=0)
                 .reindex(columns=VERDICT_ORDER, fill_value=0))
    per_field.to_csv(cfg.results / "per_field_rates.csv")

    comparable = comp[comp.verdict != "missing"].copy()
    comparable["agree"] = comparable.verdict.isin(["exact", "minor"]).astype(int)
    pair = comparable.groupby(["surface_a", "surface_b"]).agg(
        n=("agree", "size"), agreement=("agree", "mean")).reset_index()
    pair.to_csv(cfg.results / "pair_matrix.csv", index=False)

    proj = comparable.groupby("project_id").agg(
        comparable_pairs=("agree", "size"), agreement=("agree", "mean")).reset_index()
    conflicts = (comp[(comp.verdict == "conflict") & (comp.field.isin(CORE_FIELDS))]
                 .groupby("project_id").size().rename("core_conflicts"))
    proj = proj.merge(conflicts, on="project_id", how="left").fillna({"core_conflicts": 0})
    proj.to_csv(cfg.results / "project_scores.csv", index=False)

    eligible = set(comp.project_id.unique())
    disagree = set(proj[proj.core_conflicts > 0].project_id)
    stats["n_projects_with_2plus_surfaces"] = len(eligible)
    stats["n_projects_with_core_conflict"] = len(disagree)
    stats["pct_projects_disagreeing_with_themselves"] = (
        round(100 * len(disagree) / len(eligible), 1) if eligible else None)
    stats["median_pairwise_agreement"] = round(float(proj.agreement.median()), 3) if len(proj) else None
    for f in CORE_FIELDS:
        sub = comparable[comparable.field == f]
        if len(sub):
            stats[f"agreement_{f}"] = round(float(sub.agree.mean()), 3)

    if "domain" in comp.columns and comp.domain.notna().any():
        dom = comparable.groupby("domain").agree.mean().round(3).to_dict()
        stats["agreement_by_domain"] = dom
    
    if "stratum" in comp.columns and comp.stratum.notna().any():
        strat_rows = []
        for stratum, sub in comparable.groupby("stratum"):
            if not str(stratum).strip():
                continue
            pids = set(sub.project_id.unique())
            confl = pids & disagree
            strat_rows.append({
                "stratum": stratum,
                "n_projects": len(pids),
                "n_comparable_pairs": int(len(sub)),
                "agreement": round(float(sub.agree.mean()), 3),
                "n_projects_core_conflict": len(confl),
                "pct_projects_core_conflict":
                    round(100 * len(confl) / len(pids), 1) if pids else None,
            })
        if strat_rows:
            pd.DataFrame(strat_rows).to_csv(cfg.results / "per_stratum.csv", index=False)
            stats["agreement_by_stratum"] = {
                r["stratum"]: r["agreement"] for r in strat_rows}
            stats["pct_core_conflict_by_stratum"] = {
                r["stratum"]: r["pct_projects_core_conflict"] for r in strat_rows}

    intra_p = cfg.results / "intra_cff.csv"
    if intra_p.exists() and intra_p.stat().st_size:
        intra = pd.read_csv(intra_p)
        n_proj = intra.project_id.nunique()
        n_confl = intra[intra.verdict == "conflict"].project_id.nunique()
        stats["cff_projects_with_preferred_citation"] = int(n_proj)
        stats["cff_projects_root_vs_preferred_conflict"] = int(n_confl)

    (cfg.results / "summary_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))

    ax = (per_field.div(per_field.sum(axis=1), axis=0)
          .loc[:, VERDICT_ORDER]
          .plot(kind="barh", stacked=True, color=[COLORS[v] for v in VERDICT_ORDER], figsize=(8, 4.5)))
    ax.set_xlabel("share of surface-pair comparisons")
    ax.set_title("Do surfaces agree? Verdicts by metadata field")
    ax.legend(loc="lower right", ncols=4, fontsize=8)
    plt.tight_layout()
    plt.savefig(cfg.results / "fig_per_field.png", dpi=200)
    plt.close()

    if len(pair):
        hm = pair.pivot(index="surface_a", columns="surface_b", values="agreement")
        fig, ax = plt.subplots(figsize=(7, 5.5))
        im = ax.imshow(hm.values, cmap="RdYlGn", vmin=0, vmax=1)
        ax.set_xticks(range(len(hm.columns)), hm.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(hm.index)), hm.index)
        for i in range(hm.shape[0]):
            for j in range(hm.shape[1]):
                v = hm.values[i, j]
                if pd.notna(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
        ax.set_title("Surface-pair agreement (exact+minor / comparable)")
        fig.colorbar(im, shrink=0.8)
        plt.tight_layout()
        plt.savefig(cfg.results / "fig_pair_heatmap.png", dpi=200)
        plt.close()

    availability_figure(cfg)
    print("figures written to", cfg.results)
