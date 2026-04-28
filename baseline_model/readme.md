# FairLens Baseline ATS Benchmark Package

## Included Files

* `baseline_bias_report.json` → Final summarized fairness / bias findings from the legacy ATS baseline model
* `baseline_full_predictions.csv` → Candidate-level predicted scores for the full dataset (9,544 rows)
* `baseline_component.py` → Baseline scoring + audit engine (included for reproducibility / future reruns)
* `biased_baseline_ats.pkl` → Trained baseline ATS model file
* `requirements.txt` → Python dependencies if rerun is needed later

---

## Purpose

This package provides the benchmark results of a conventional ATS-style resume screening model.

It is intended to serve as the **comparison baseline** for the FairLens fairness-aware model.

The outputs highlight how a traditional ATS may produce opaque scoring behavior and structural disparities when evaluated across a full candidate dataset.

---

## Final Key Findings

* No major aggregate gender score gap detected in average scoring
* Unexpected college-tier preference (`Tier 2 > Tier 1`)
* Regional disparity favoring `Non-Metro` candidates
* Latent / difficult-to-interpret scoring behavior observed

---

## Files to Use for Prototype Integration

### Primary Files

Use these directly in the final prototype website:

* `baseline_bias_report.json`
* `baseline_full_predictions.csv`

These files can power:

* charts
* fairness dashboards
* comparison tables
* baseline vs FairLens visuals

---

## Optional Technical Files

Use only if rerunning or extending baseline tests later:

* `baseline_component.py`
* `biased_baseline_ats.pkl`

---

## How Results Were Generated

The baseline model was executed across the full dataset of 9,544 candidate profiles.

Process:

```text
Dataset
→ Resume embeddings
→ Baseline ATS scoring
→ Group fairness analysis
→ Selection metrics
→ Explainability sample audit
→ Final reports
```

---

## Intended Use in Final Prototype

Use this package as the **Legacy ATS Baseline Layer**.

Compare it against FairLens outputs on:

* fairness
* score disparities
* transparency
* explainability
* equitable recommendations

---

## Notes

The prototype does not need to run this model live.

These audited benchmark outputs are sufficient for integration and presentation.

Live reruns remain possible using the included component files if required later.
