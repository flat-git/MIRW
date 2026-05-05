import api from './client';
import type { SearchResult } from '../types';

export async function searchEvents(
  datasetId: string,
  query: string,
  topK = 5,
  useReranker = true
): Promise<SearchResult> {
  const { data } = await api.post(`/datasets/${datasetId}/search`, {
    query,
    top_k: topK,
    use_reranker: useReranker,
  });
  return data;
}
