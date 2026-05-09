import api from './client';
import type { ReportResponse, ReportHistoryItem } from '../types';

export async function generateIeWeekly(datasetId: string, period: string): Promise<ReportResponse> {
  const { data } = await api.post(`/datasets/${datasetId}/reports/ie-weekly`, { period });
  return data;
}

export async function generateCapa(datasetId: string, period: string): Promise<ReportResponse> {
  const { data } = await api.post(`/datasets/${datasetId}/reports/capa`, { period });
  return data;
}

export async function generateFiveWhy(datasetId: string, eventId: string): Promise<ReportResponse> {
  const { data } = await api.post(`/datasets/${datasetId}/reports/five-why`, { event_id: eventId });
  return data;
}

export async function getReportHistory(datasetId: string): Promise<ReportHistoryItem[]> {
  const { data } = await api.get(`/datasets/${datasetId}/reports/history`);
  return data;
}

export function getReportDownloadUrl(datasetId: string, reportId: string): string {
  return `/api/datasets/${datasetId}/reports/${reportId}/download`;
}
