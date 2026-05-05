export interface DatasetListItem {
  dataset_id: string;
  source: string;
  run_count: number;
  event_count: number;
  loaded_at: string;
  validation_passed?: boolean;
}

export interface DatasetSummary {
  dataset_id: string;
  source: string;
  run_count: number;
  event_count: number;
  loaded_at: string;
  pipeline_status?: string;
  capability: Record<string, boolean | string[]>;
  metrics_preview?: {
    efficiency?: EfficiencySummary;
    pareto?: ParetoItem[];
    groups?: Record<string, number>;
    action_summary?: ActionSummary;
  };
  cards?: DatasetCard[];
  validation: {
    production_runs: { passed: boolean; errors?: string[]; stats?: Record<string, unknown> };
    downtime_events: { passed: boolean; errors?: string[]; stats?: Record<string, unknown> };
  };
}

export interface DatasetCard {
  key: string;
  title: string;
  enabled: boolean;
  reason: string;
  route: string;
}

export interface EfficiencySummary {
  total_downtime_min: number | null;
  total_planned_min: number | null;
  total_runtime_min: number | null;
  downtime_ratio: number | null;
  line_efficiency: number | null;
  total_runs: number;
  total_events: number;
}

export interface ParetoItem {
  rank: number;
  category: string;
  total_downtime_min: number;
  event_count: number;
  ratio: number;
  cumulative_ratio: number;
}

export interface DowntimeGroupItem {
  group_key?: string;
  category?: string;
  machine_id?: string;
  product_id?: string;
  operator_id?: string;
  total_downtime_min: number;
  event_count: number;
  ratio: number;
}

export interface DowntimeEvent {
  event_id: string;
  run_id?: string;
  source_dataset: string;
  machine_id?: string;
  line_id?: string;
  product_id?: string;
  operator_id?: string;
  downtime_min: number;
  raw_reason: string;
  standard_loss_category?: string;
  raw_note?: string;
  metadata?: Record<string, unknown>;
}

export interface SimilarEventItem {
  event_id: string;
  raw_note: string;
  raw_reason: string;
  downtime_min: number;
  similarity_score: number;
  rerank_score?: number;
}

export interface SearchResult {
  query: string;
  results: SimilarEventItem[];
}

export interface ReportResponse {
  report_type: string;
  period: string;
  report_markdown: string;
  check_result: Record<string, boolean>;
}

export interface ActionItem {
  action_id: string;
  related_event_id?: string;
  problem: string;
  temporary_action?: string;
  permanent_action?: string;
  owner?: string;
  due_date?: string;
  status: string;
  close_date?: string;
  recurrence_flag: boolean;
}

export interface ActionSummary {
  total: number;
  open: number;
  in_progress: number;
  closed: number;
  overdue: number;
  recurred: number;
  reason?: string;
}
