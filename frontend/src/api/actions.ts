import api from './client';
import type { ActionItem, ActionSummary } from '../types';

export async function listActions(datasetId: string): Promise<ActionItem[]> {
  const { data } = await api.get(`/datasets/${datasetId}/actions`);
  return data;
}

export async function getActionSummary(datasetId: string): Promise<ActionSummary> {
  const { data } = await api.get(`/datasets/${datasetId}/actions/summary`);
  return data;
}
