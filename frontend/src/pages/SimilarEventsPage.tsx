import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import DatasetHeader, { MissingDataset } from '../components/DatasetHeader';
import { getDataset } from '../api/datasets';
import { searchEvents } from '../api/search';
import type { DatasetSummary, SimilarEventItem } from '../types';

export default function SimilarEventsPage() {
  const { datasetId = '' } = useParams();
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [query, setQuery] = useState('Motor overheated and caused a shutdown');
  const [topK, setTopK] = useState(5);
  const [useReranker, setUseReranker] = useState(true);
  const [results, setResults] = useState<SimilarEventItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    getDataset(datasetId).then(setDataset).catch(() => setMissing(true));
  }, [datasetId]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await searchEvents(datasetId, query, topK, useReranker);
      setResults(res.results);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '检索失败');
    } finally {
      setLoading(false);
    }
  };

  if (missing) return <MissingDataset />;
  if (!dataset) return <div className="text-slate-500">加载中...</div>;

  const card = dataset.cards?.find((c) => c.key === 'similar');
  const enabled = card?.enabled ?? false;

  return (
    <div>
      <DatasetHeader summary={dataset} title="相似事件检索" />

      {!enabled && (
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded p-4 mb-6">
          {card?.reason ?? '当前数据集不支持相似事件检索'}
        </div>
      )}

      <div className="bg-white rounded-lg border p-4 mb-6">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs text-slate-500 block mb-1">查询文本</label>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && enabled && handleSearch()}
              disabled={!enabled}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-slate-100"
              placeholder="输入异常描述..."
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Top K</label>
            <input type="number" value={topK} onChange={(e) => setTopK(Number(e.target.value))}
              disabled={!enabled} className="w-16 border rounded px-2 py-2 text-sm text-center disabled:bg-slate-100" min={1} max={20} />
          </div>
          <label className="flex items-center gap-1.5 text-sm text-slate-600 pb-2">
            <input type="checkbox" checked={useReranker} disabled={!enabled} onChange={(e) => setUseReranker(e.target.checked)} />
            Reranker
          </label>
          <button onClick={handleSearch} disabled={loading || !enabled}
            className="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600 disabled:opacity-50">
            {loading ? '检索中...' : '检索'}
          </button>
        </div>
        {error && <div className="text-red-500 text-sm mt-3">{error}</div>}
      </div>

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((r) => (
            <div key={r.event_id} className="bg-white rounded-lg border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-mono text-slate-500">{r.event_id}</span>
                <div className="flex gap-3 text-xs">
                  <span className="text-blue-600 font-medium">emb: {r.similarity_score.toFixed(4)}</span>
                  {r.rerank_score != null && <span className="text-green-600 font-medium">rerank: {r.rerank_score.toFixed(4)}</span>}
                </div>
              </div>
              <div className="text-sm text-slate-800 mb-1">{r.raw_note}</div>
              <div className="flex gap-4 text-xs text-slate-500">
                <span>原因: {r.raw_reason}</span>
                <span>停机: {r.downtime_min} min</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
