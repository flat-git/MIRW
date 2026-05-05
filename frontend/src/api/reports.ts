import api from './client';
import type { ReportResponse } from '../types';

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
