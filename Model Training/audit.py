import json
# Import the reusable function from your new library
from fairness_metrics import generate_audit_report

def main():
    print("Initializing Modular Fairness Audit...")

    # 1. API Call for Baseline Data
    print("  -> Processing Baseline Model...")
    baseline_report = generate_audit_report(
        csv_path='baseline_scored_results.csv', 
        score_col='Model_Predicted_Score', 
        threshold=0.70
    )

    # 2. API Call for FairLens Data
    print("  -> Processing FairLens DANN Model...")
    fairlens_report = generate_audit_report(
        csv_path='clean_scored_results.csv', 
        score_col='FairLens_Predicted_Score', 
        threshold=0.685
    )

    # 3. Combine into the final payload expected by the React UI
    final_payload = {
        "Baseline": baseline_report,
        "FairLens": fairlens_report
    }

    # 4. Save the output
    output_file = "final_audit_report.json"
    with open(output_file, 'w') as f:
        json.dump(final_payload, f, indent=2)

    print(f"\n✅ Audit Complete! Results dynamically generated and saved to '{output_file}'")

if __name__ == "__main__":
    main()