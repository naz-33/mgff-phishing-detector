export interface EmailScanItem {
  id: number;
  mailbox: string;
  gmail_message_id: string;
  gmail_thread_id?: string | null;
  sender?: string | null;
  subject?: string | null;
  body?: string | null;
  received_at: string;
  classification: 'Phishing' | 'Legitimate' | string;
  risk_tier?: 'Legitimate' | 'Suspicious' | 'High-Confidence Phishing' | string | null;
  phishing_probability: number;
  logistic_regression_probability: number;
  lightgbm_probability: number;
  inference_time_ms: number;
  scanned_at: string;
  model_version: string;
  spf_pass?: boolean | null;
  dkim_pass?: boolean | null;
  dmarc_pass?: boolean | null;
}

export interface EmailListResponse {
  items: EmailScanItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EnsembleWeights {
  logistic_regression: number;
  lightgbm: number;
}

export interface EmailScanDetail extends EmailScanItem {
  threshold: number;
  high_confidence_threshold: number;
  ensemble_weights: EnsembleWeights;
  methodology: {
    fusion_technique: string;
    features: {
      word_tfidf: string;
      char_tfidf: string;
      stylometrics: string;
    };
    classifiers: string;
  };
}

export interface DashboardSummary {
  total_scanned: number;
  total_phishing: number;
  total_legitimate: number;
  total_suspicious: number;
  phishing_ratio_percent: number;
  average_latency_ms: number;
  latest_scan_at: string | null;
  mailbox: string | null;
  scanner_status: string;
  recent_phishing_warnings: EmailScanItem[];
  recent_scans: EmailScanItem[];
}

export interface TimeSeriesPoint {
  date: string;
  total_scanned: number;
  phishing: number;
  legitimate: number;
  average_latency_ms: number;
}

export interface ClassificationDistribution {
  phishing: number;
  legitimate: number;
  phishing_percentage: number;
  legitimate_percentage: number;
}

export interface ResearchMetricItem {
  metric: string;
  baseline_replication: string;
  proposed_hybrid: string;
  delta: string;
}

export interface ResearchBenchmark {
  title: string;
  dataset: string;
  metrics: ResearchMetricItem[];
  confusion_matrix: {
    true_negatives: number;
    false_positives: number;
    false_negatives: number;
    true_positives: number;
  };
  roc_auc: number;
  avg_precision: number;
  latency_ms: number;
  note: string;
}

export interface AnalyticsOverview {
  time_series: TimeSeriesPoint[];
  distribution: ClassificationDistribution;
  latency_trends: Array<{
    latency_ms: number;
    classification: string;
    timestamp: string;
  }>;
  research_benchmark: ResearchBenchmark;
}

export interface ScannerStatus {
  mailbox: string | null;
  oauth_authorized: boolean;
  sync_status: string;
  last_history_id: string | null;
  last_internal_date: number | null;
  last_sync_at: string | null;
  polling_interval_seconds: number;
  credentials_file_present: boolean;
  token_file_present: boolean;
  last_error: string | null;
}

export interface ModelInfo {
  system_name: string;
  model_version: string;
  threshold: number;
  ensemble_weights: EnsembleWeights;
  models_loaded: {
    logistic_regression: boolean;
    lightgbm: boolean;
    word_vectorizer: boolean;
    char_vectorizer: boolean;
    scaler: boolean;
  };
  architecture: {
    feature_fusion: string;
    feature_breakdown: Array<{
      stream: string;
      dimension: number;
      ngrams: string;
      details: string;
    }>;
    ensemble_classifiers: Array<{
      model: string;
      weight: string;
      hyperparameters: string;
    }>;
    decision_threshold: number;
  };
}

export interface UserProfile {
  username: string;
  role: string;
  authenticated: boolean;
}

