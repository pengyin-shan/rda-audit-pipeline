#!/usr/bin/env python3
import argparse
import csv
from datetime import date
from pathlib import Path

LOG_FIELDS = ["project_id", "surface_a", "surface_b", "field",
              "pipeline_verdict", "hand_verdict", "agree", "issue_class",
              "note", "checked"]

def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worklist", default="worklist.csv")
    ap.add_argument("--results", default="data/results")
    ap.add_argument("--out", default="verification/verification_log.csv")
    args = ap.parse_args()

    comp = load(Path(args.results) / "comparisons.csv")
    intra = load(Path(args.results) / "intra_cff.csv")
    work = load(args.worklist)

    index = {}
    for r in comp:
        index.setdefault(("comp" if r["verdict"] in ("conflict", "minor") else "exact",
                          r["project_id"], r["field"], r.get("detail", "")), []).append(
            (r["surface_a"], r["surface_b"], r["verdict"]))
    for r in intra:
        if r["verdict"] == "conflict":
            index.setdefault(("intra", r["project_id"], r["field"], r.get("detail", "")),
                             []).append(("cff", "cff_preferred", r["verdict"]))

    today = date.today().strftime("%m/%d/%y")
    out_rows, unmatched = [], []
    for w in work:
        detail = "" if w["values"].startswith("(exact:") else w["values"]
        key = (w["scope"], w["project_id"], w["field"], detail)
        covered = index.get(key)
        if not covered:
            unmatched.append(w["judgment_id"])
            continue
        pairs = set(tuple(p.split("~")) for p in w["covered_pairs"].split(";"))
        for sa, sb, verdict in covered:
            if (sa, sb) not in pairs:
                continue
            out_rows.append({"project_id": w["project_id"], "surface_a": sa,
                             "surface_b": sb, "field": w["field"],
                             "pipeline_verdict": verdict,
                             "hand_verdict": w["hand_verdict"].strip(),
                             "agree": w["agree"].strip() or "1",
                             "issue_class": w["issue_class"].strip(),
                             "note": w["note"].strip(),
                             "checked": w["checked"].strip() or today})

    Path(args.out).parent.mkdir(exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        wcsv.writeheader()
        wcsv.writerows(out_rows)
    print(f"wrote {args.out}: {len(out_rows)} rows from {len(work)} judgments")
    if unmatched:
        print(f"WARNING: {len(unmatched)} judgments matched no current comparison "
              f"row (results regenerated since worklist?): {unmatched[:5]}")

    by = {}
    for r in out_rows:
        b = by.setdefault(r["pipeline_verdict"], [0, 0])
        b[1] += 1
        b[0] += int(r["agree"] == "1")
    total_a = sum(a for a, n in by.values())
    total_n = sum(n for a, n in by.values())
    print("\nPrecision by verdict class:")
    for k, (a, n) in sorted(by.items()):
        print(f"  {k:9s} {a}/{n}  ({100*a/n:.1f}%)")
    print(f"  overall   {total_a}/{total_n}  ({100*total_a/total_n:.1f}%)")
    issues = {}
    for r in out_rows:
        if r["agree"] != "1":
            issues[r["issue_class"] or "UNCLASSIFIED"] = issues.get(
                r["issue_class"] or "UNCLASSIFIED", 0) + 1
    if issues:
        print("Disagreements by issue class:", issues)
        if "UNCLASSIFIED" in issues:
            print("  -> classify these before quoting the precision number.")

if __name__ == "__main__":
    main()
