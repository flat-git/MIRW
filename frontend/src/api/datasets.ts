import api from './client';
import type { DatasetListItem, DatasetSummary, DowntimeEvent } from '../types';

export async function listDatasets(): Promise<DatasetListItem[]> {
  const { data } = await api.get('/datasets');
  return data;
}

export async function loadDataset(source: string): Promise<DatasetSummary> {
  const { data } = await api.post('/datasets/load', { source });
  return data;
}

export async function uploadDataset(file: File, mapping?: string): Promise<DatasetSummary> {
  const form = new FormData();
  form.append('file', file);
  if (mapping?.trim()) form.append('mapping', mapping);
  const { data } = await api.post('/datasets/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getDataset(datasetId: string): Promise<DatasetSummary> {
  const { data } = await api.get(`/datasets/${datasetId}`);
  return data;
}

export async function getEvents(datasetId: string, limit = 200): Promise<DowntimeEvent[]> {
  const { data } = await api.get(`/datasets/${datasetId}/events?limit=${limit}`);
  return data;
}

export async function getRuns(datasetId: string, limit = 200): Promise<Record<string, unknown>[]> {
  const { data } = await api.get(`/datasets/${datasetId}/runs?limit=${limit}`);
  return data;
}

export interface AnalyzeResponse {
  analysis_id: string;
  file_name: string;
  total_rows: number;
  columns: Array<{
    name: string;
    dtype: string;
    null_count: number;
    null_ratio: number;
    unique_count: number;
    sample_values: string[];
    is_numeric: boolean;
    is_datetime: boolean;
    detected_issues: string[];
  }>;
  suggested_mappings: Array<{
    source_column: string;
    target_field: string | null;
    confidence: number;
    reasoning?: string;
  }>;
  unmapped_columns: string[];
  detected_structure: string;
}

export async function analyzeFile(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/datasets/analyze', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function importFile(
  analysisId: string,
  confirmedMappings: Array<{ source_column: string; target_field: string | null }>,
  options?: { deduplicate?: boolean; normalizeNulls?: boolean; coerceTypes?: boolean }
): Promise<DatasetSummary> {
  const { data } = await api.post('/datasets/import', {
    analysis_id: analysisId,
    confirmed_mappings: confirmedMappings,
    deduplicate: options?.deduplicate ?? true,
    normalize_nulls: options?.normalizeNulls ?? true,
    coerce_types: options?.coerceTypes ?? true,
  });
  return data;
}

export function getExcelDownloadUrl(datasetId: string): string {
  return `/api/datasets/${datasetId}/download/excel`;
}

export function getAnalysisReportDownloadUrl(datasetId: string): string {
  return `/api/datasets/${datasetId}/download/report`;
}
