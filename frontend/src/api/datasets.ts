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
