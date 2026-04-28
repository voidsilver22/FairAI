import pandas as pd
import json
from fairlearn.metrics import MetricFrame, selection_rate, true_positive_rate, false_negative_rate, false_positive_rate

class FairnessAuditor:
    def __init__(self, dataframe, score_col='Model_Predicted_Score', threshold=0.70):
        """
        Initializes the auditor with a DataFrame and binarizes the scores.
        """
        self.df = dataframe.copy()
        self.threshold = threshold

        # Binarize continuous scores into hard Accept/Reject decisions
        self.df['Predicted_Label'] = (self.df[score_col] >= threshold).astype(int)
        self.df['True_Label'] = (self.df['matched_score'] >= threshold).astype(int)

    def evaluate_slice(self, attribute_name, priv_group, unpriv_group, priv_values=None):
        if priv_values is None:
            priv_values = [priv_group]
            
        y_true = self.df['True_Label']
        y_pred = self.df['Predicted_Label']
        sensitive_features = self.df[attribute_name]
        
        mf = MetricFrame(
            metrics={
                'selection_rate': selection_rate,
                'tpr': true_positive_rate,
                'fnr': false_negative_rate,
                'fpr': false_positive_rate
            },
            y_true=y_true,
            y_pred=y_pred,
            sensitive_features=sensitive_features
        )
        
        # Extract rates
        sr_unpriv = mf.by_group['selection_rate'][unpriv_group]
        tpr_unpriv = mf.by_group['tpr'][unpriv_group]
        fnr_unpriv = mf.by_group['fnr'][unpriv_group]
        fpr_unpriv = mf.by_group['fpr'][unpriv_group]
        
        sr_priv = mf.by_group['selection_rate'][priv_values].mean()
        tpr_priv = mf.by_group['tpr'][priv_values].mean()
        fnr_priv = mf.by_group['fnr'][priv_values].mean()
        fpr_priv = mf.by_group['fpr'][priv_values].mean()
        
        # Calculations
        disparate_impact = sr_unpriv / sr_priv if sr_priv > 0 else 0
        eod = tpr_unpriv - tpr_priv
        fnrd = fnr_unpriv - fnr_priv
        fprd = fpr_unpriv - fpr_priv
        
        metrics_payload = [
            self._format_metric("Disparate Impact", disparate_impact, 0.80, disparate_impact >= 0.80, 
                               f"Unprivileged group is selected at {disparate_impact*100:.1f}% the rate of the privileged group."),
            self._format_metric("Equal Opportunity Difference", eod, -0.10, eod >= -0.10, 
                               f"Qualified {unpriv_group} candidates have a {eod*100:.1f}% difference in selection rate vs {priv_group}."),
            self._format_metric("False Negative Rate Difference", fnrd, 0.10, fnrd <= 0.10, 
                               f"{unpriv_group} candidates are incorrectly rejected {fnrd*100:.1f}% more often."),
            self._format_metric("False Positive Rate Difference", fprd, 0.10, fprd <= 0.10, 
                               f"{unpriv_group} candidates are incorrectly accepted {fprd*100:.1f}% more often.")
        ]
        
        failed_count = sum(1 for m in metrics_payload if not m['passed'])
        audit_status = "FAIL" if (disparate_impact < 0.80 or failed_count >= 3) else "PASS"
        
        return {
            "audit_status": audit_status,
            "evaluated_group": {
                "attribute": attribute_name,
                "privileged": priv_group,
                "unprivileged": unpriv_group
            },
            "metrics": metrics_payload
        }

    def _format_metric(self, name, value, threshold, passed, description):
        return {
            "name": name,
            "value": round(float(value), 3),
            "threshold": threshold,
            "passed": bool(passed),
            "description": description
        }
        
    def run_full_audit(self):
        return {
            "gender": self.evaluate_slice("gender", "Male", "Female"),
            "age_group": self.evaluate_slice("age_group", "35-44", "21-26"),
            "college_tier": self.evaluate_slice("college_tier", "Tier 2", "Tier 3", ["Tier 1", "Tier 2"]),
            "region": self.evaluate_slice("region", "Non-Metro", "Metro")
        }

def generate_audit_report(csv_path, score_col, threshold, output_json_path=None):
    """
    Public API function for the FastAPI backend to call.
    Reads a CSV, runs the audit, and returns/saves the JSON payload.
    """
    df = pd.read_csv(csv_path)
    auditor = FairnessAuditor(df, score_col, threshold)
    results = auditor.run_full_audit()
    
    if output_json_path:
        with open(output_json_path, 'w') as f:
            json.dump(results, f, indent=2)
            
    return results