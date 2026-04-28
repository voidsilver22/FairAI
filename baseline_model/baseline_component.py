# ==========================================================
# baseline_component.py
# FairLens Baseline ATS + Full Dataset Audit Engine
# ==========================================================

import os
import sys
import json
import random
import warnings
import joblib
import shap
import numpy as np
import pandas as pd

from sentence_transformers import SentenceTransformer

warnings.filterwarnings("ignore")

# ==========================================================
# CONFIG
# ==========================================================

MODEL_PATH = "biased_baseline_ats.pkl"
DATASET_PATH = "fairlens_dataset_unstructured.csv"
SELECTION_THRESHOLD = 0.60

# ==========================================================
# LOAD SYSTEM
# ==========================================================

print("Loading baseline ATS model...")
model = joblib.load(MODEL_PATH)

print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading SHAP explainer...")
explainer = shap.TreeExplainer(model)

print("System ready.\n")

# ==========================================================
# RESUME TEXT BUILDER
# ==========================================================

def build_resume_text(
    role="Not Provided",
    company="Not Provided",
    summary="Not Provided",
    year="Not Provided",
    university="Not Provided",
    degree="Not Provided",
    field="Not Provided",
    skills="Not Provided",
    certs="Not Provided",
    languages="Not Provided"
):

    templates = [

        f"Role: {role} @ {company}. {summary} "
        f"Graduated {year} from {university} "
        f"({degree} - {field}). "
        f"Proficiencies: {skills}. "
        f"Extra certs: {certs}. "
        f"Languages: {languages}.",

        f"Alumni of {university} ({year}) with a {degree} in {field}. "
        f"Expert in {skills}. "
        f"Certified in {certs}. "
        f"Professional background includes time at {company} as a {role}. "
        f"{summary} "
        f"Languages spoken: {languages}.",

        f"{summary} Previously, I worked as a {role} at {company}. "
        f"I hold a {degree} in {field} from {university}, graduating in {year}. "
        f"My technical toolkit includes {skills} "
        f"and I have certifications in {certs}. "
        f"I am fluent in {languages}."
    ]

    return random.choice(templates)

# ==========================================================
# HUMAN SIGNAL EXTRACTION
# ==========================================================

def extract_signals(text, neg_strength):

    txt = text.lower()

    positive = []
    negative = []

    if any(k in txt for k in ["python", "sql", "machine learning", "excel", "java", "aws"]):
        positive.append("Relevant technical skills detected")

    if any(k in txt for k in ["analyst", "engineer", "developer", "manager", "lead"]):
        positive.append("Relevant professional role experience detected")

    if any(k in txt for k in ["b.tech", "bachelor", "master", "mba", "m.sc"]):
        positive.append("Recognized educational qualification present")

    if "certified" in txt and "not provided" not in txt:
        positive.append("Certifications mentioned")

    if any(k in txt for k in ["english", "hindi", "marathi"]):
        positive.append("Language proficiency listed")

    if "fresher" in txt or "intern" in txt:
        negative.append("Limited professional experience indicated")

    if txt.count("not provided") >= 1:
        negative.append("Some profile fields were incomplete")

    if len(txt) < 250:
        negative.append("Limited resume detail provided")

    if len(negative) == 0 and neg_strength < -0.05:
        negative.append("Model detected negative patterns that are not easily interpretable")

    return positive, negative

# ==========================================================
# LABELS
# ==========================================================

def score_label(score):

    if score >= 0.75:
        return "High Predicted Fit"
    elif score >= 0.60:
        return "Moderate Predicted Fit"
    elif score >= 0.45:
        return "Needs Human Review"
    return "Low Predicted Fit"

# ==========================================================
# SINGLE CANDIDATE MODE
# ==========================================================

def run_baseline(
    role="Not Provided",
    company="Not Provided",
    summary="Not Provided",
    year="Not Provided",
    university="Not Provided",
    degree="Not Provided",
    field="Not Provided",
    skills="Not Provided",
    certs="Not Provided",
    languages="Not Provided"
):

    resume_text = build_resume_text(
        role, company, summary, year,
        university, degree, field,
        skills, certs, languages
    )

    vec = embed_model.encode([resume_text])

    score = float(model.predict(vec)[0])

    shap_vals = explainer.shap_values(vec)[0]

    pos_strength = float(np.sum(shap_vals[shap_vals > 0]))
    neg_strength = float(np.sum(shap_vals[shap_vals < 0]))

    positive, negative = extract_signals(resume_text, neg_strength)

    return {
        "model_name": "Baseline ATS",
        "generated_resume_text": resume_text,
        "score": round(score, 4),
        "assessment": score_label(score),
        "positive_signal_strength": round(pos_strength, 4),
        "negative_signal_strength": round(neg_strength, 4),
        "positive_signals": positive,
        "negative_signals": negative,
        "transparency_warning":
            "This baseline model relies on latent learned patterns that may not be fully interpretable.",
        "recommendation":
            "Use as screening support only. Human review recommended."
    }

# ==========================================================
# FULL DATASET AUDIT MODE
# ==========================================================

def run_full_audit():

    print("Loading dataset...")
    df = pd.read_csv(DATASET_PATH)

    if "Raw_Resume_Text" not in df.columns:
        print("ERROR: Raw_Resume_Text column not found.")
        return

    print("Encoding all resumes...")
    texts = df["Raw_Resume_Text"].fillna("").tolist()

    X = embed_model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True
    )

    print("Predicting scores for all rows...")
    df["Baseline_Score"] = model.predict(X)

    df["Selected"] = (df["Baseline_Score"] >= SELECTION_THRESHOLD).astype(int)

    # ------------------------
    # GROUP METRICS
    # ------------------------

    gender_scores = df.groupby("gender")["Baseline_Score"].mean().to_dict()
    tier_scores = df.groupby("college_tier")["Baseline_Score"].mean().to_dict()
    region_scores = df.groupby("region")["Baseline_Score"].mean().to_dict()

    gender_select = df.groupby("gender")["Selected"].mean().to_dict()
    tier_select = df.groupby("college_tier")["Selected"].mean().to_dict()

    protected_scores = (
        df.groupby("protected_group")["Baseline_Score"]
        .mean()
        .sort_values()
        .to_dict()
    )

    # ------------------------
    # SHAP SAMPLE ANALYSIS
    # ------------------------

    print("Running SHAP audit sample...")

    sample_size = min(300, len(df))
    idx = np.random.choice(len(df), sample_size, replace=False)

    X_sample = X[idx]

    shap_vals = explainer.shap_values(X_sample)

    mean_abs = np.abs(shap_vals).mean(axis=0)

    top_features = []

    for i in np.argsort(mean_abs)[::-1][:15]:
        top_features.append({
            "feature": f"embed_{i}",
            "importance": round(float(mean_abs[i]), 6)
        })

    # ------------------------
    # EXPORT RESULTS
    # ------------------------

    df.to_csv("baseline_full_predictions.csv", index=False)

    report = {
        "model_name": "Baseline ATS",
        "rows_evaluated": int(len(df)),
        "selection_threshold": SELECTION_THRESHOLD,

        "mean_score_gender": gender_scores,
        "mean_score_college_tier": tier_scores,
        "mean_score_region": region_scores,

        "selection_rate_gender": gender_select,
        "selection_rate_college_tier": tier_select,

        "protected_group_ranking": protected_scores,

        "top_hidden_embedding_features": top_features,

        "summary": [
            "Baseline ATS demonstrates opaque latent scoring behavior.",
            "Protected-group variation indicates fairness review is needed.",
            "Selection disparities should be compared against FairLens.",
            "Embedding dimensions are abstract and difficult to interpret directly."
        ]
    }

    with open("baseline_bias_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # ------------------------
    # CONSOLE SUMMARY
    # ------------------------

    print("\n==============================")
    print("BASELINE AUDIT COMPLETE")
    print("==============================")
    print("Rows Evaluated:", len(df))
    print("Saved: baseline_full_predictions.csv")
    print("Saved: baseline_bias_report.json")

    print("\nMean Score by Gender:")
    print(gender_scores)

    print("\nMean Score by College Tier:")
    print(tier_scores)

    print("\nMean Score by Region:")
    print(region_scores)

# ==========================================================
# MAIN ENTRY
# ==========================================================

if __name__ == "__main__":

    # FULL DATASET AUDIT MODE
    if len(sys.argv) > 1 and sys.argv[1].lower() == "audit":
        run_full_audit()

    # SINGLE CANDIDATE MODE
    else:
        sample = run_baseline(
            role="Data Analyst",
            company="Infosys",
            summary="Experienced analytics professional seeking growth opportunities.",
            year="2021",
            university="Mumbai University",
            degree="B.Tech",
            field="Computer Science",
            skills="Python, SQL, Power BI, Excel, Machine Learning",
            certs="Google Data Analytics",
            languages="English, Hindi"
        )

        print(json.dumps(sample, indent=2))