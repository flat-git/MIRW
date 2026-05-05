import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import DatasetHeader, { MissingDataset } from '../components/DatasetHeader';
import { getDataset, getEvents, getRuns } from '../api/datasets';
import type { DatasetSummary, DowntimeEvent } from '../types';

export default function EventsPage() {
  const { datasetId = '' } = useParams();
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [events, setEvents] = useState<DowntimeEvent[]>([]);
  const [runs, setRuns] = useState<Record<string, unknown>[]>([]);
  const [tab, setTab] = useState<'events' | 'runs'>('events');
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    Promise.all([getDataset(datasetId), getEvents(datasetId, 200), getRuns(datasetId, 200)])
      .then(([d, e, r]) => {
        setDataset(d);
        setEvents(e);
        setRuns(r);
      })
      .catch(() => setMissing(true));
  }, [datasetId]);

  const rows = tab === 'events' ? events : runs;
  const columns = useMemo(() => {
    const first = rows[0];
    return first ? Object.keys(first).slice(0, 10) : [];
  }, [rows]);

  if (missing) return <MissingDataset />;
  if (!dataset) return <div className="text-slate-500">加载中...</div>;

  return (
    <div>
      <DatasetHeader summary={dataset} title="事件明细" />

      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b flex items-center gap-2">
          <button onClick={() => setTab('events')} className={tab === 'events' ? active : inactive}>停机事件</button>
          <button onClick={() => setTab('runs')} className={tab === 'runs' ? active : inactive}>生产批次</button>
        </div>
        {rows.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">当前数据集没有 {tab === 'events' ? '事件' : '生产批次'} 记录。</div>
        ) : (
          <div className="overflow-auto max-h-[70vh]">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  {columns.map((c) => (
                    <th key={c} className="text-left px-4 py-2 text-xs text-slate-500 font-medium">{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr key={idx} className="border-t hover:bg-slate-50">
                    {columns.map((c) => (
                      <td key={c} className="px-4 py-2 text-slate-700 align-top max-w-xs truncate">
                        {formatValue((row as Record<string, unknown>)[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const active = 'px-3 py-1.5 rounded text-sm bg-blue-500 text-white';
const inactive = 'px-3 py-1.5 rounded text-sm bg-gray-100 text-slate-600 hover:bg-gray-200';

function formatValue(value: unknown) {
  if (value == null) return '-';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
