export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';
export type Severity = 'low' | 'medium' | 'high' | 'critical';

export interface MetricResult {
  metric_key: string;
  metric_name: string;
  stage: string;
  protected_attribute: string;
  group_a: string;
  group_b: string;
  value: number;
  threshold: number;
  passed: bool;
  severity: Severity;
  human_summary: string;
  regulation_refs: string[];
  notes?: string;
}

export interface ModelPerformance {
  accuracy: number;
  precision: number;
  recall: number;
  positive_rate: number;
}

export interface FeatureAttribution {
  protected_attribute: string;
  feature_name: string;
  disparity_score: number;
  baseline_contribution_gap: number;
  verification_contribution_gap: number;
  explanation: string;
}

export interface CounterfactualFlip {
  row_index: number;
  original_group: string;
  alternative_group: string;
  original_prediction: number;
  alternative_prediction: number;
}

export interface CounterfactualAudit {
  protected_attribute: string;
  stage: string;
  flip_rate: number;
  sample_size: number;
  severity: Severity;
  examples: CounterfactualFlip[];
}

export interface FairnessReport {
  job_id: string;
  created_at: string;
  baseline_performance: ModelPerformance;
  verification_performance: ModelPerformance;
  baseline_metrics: MetricResult[];
  verification_metrics: MetricResult[];
  counterfactuals: CounterfactualAudit[];
  feature_attributions: FeatureAttribution[];
}

export interface AsyncJobRecord {
  job_id: string;
  status: JobStatus;
  file_uri: string;
  config: any;
  result?: {
    report?: FairnessReport;
  };
  error?: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface UploadInitResponse {
  file_id: string;
  file_uri: string;
  upload_url: string;
  storage_mode: string;
}
