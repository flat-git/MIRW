import api from './client';
import type { EfficiencySummary, ParetoItem, DowntimeGroupItem } from '../types';

export async function getSummary(datasetId: string): Promise<EfficiencySummary> {
  const { data } = await api.get(`/datasets/${datasetId}/metrics/summary`);
  return data;
}

export async function getPareto(datasetId: string, topN = 10): Promise<ParetoItem[]> {
  const { data } = await api.get(`/datasets/${datasetId}/metrics/pareto?top_n=${topN}`);
  return data;
}

export async function getDowntimeByGroup(
  datasetId: string,
  groupBy: string
): Promise<DowntimeGroupItem[]> {
  const { data } = await api.get(`/datasets/${datasetId}/metrics/downtime?group_by=${groupBy}`);
  return data;
}
