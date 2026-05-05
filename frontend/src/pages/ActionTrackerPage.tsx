import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import DatasetHeader, { MissingDataset } from '../components/DatasetHeader';
import { getDataset } from '../api/datasets';
import { listActions, getActionSummary } from '../api/actions';
import type { ActionItem, ActionSummary, DatasetSummary } from '../types';

export default function ActionTrackerPage() {
  const { datasetId = '' } = useParams();
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [summary, setSummary] = useState<ActionSummary | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    Promise.all([getDataset(datasetId), getActionSummary(datasetId), listActions(datasetId)])
      .then(([d, s, items]) => {
        setDataset(d);
        setSummary(s);
        setActions(items);
      })
      .catch(() => setMissing(true));
  }, [datasetId]);

  if (missing) return <MissingDataset />;
  if (!dataset || !summary) return <div className="text-slate-500">加载中...</div>;

  const card = dataset.cards?.find((c) => c.key === 'actions');
  const enabled = card?.enabled ?? false;

  return (
    <div>
      <DatasetHeader summary={dataset} title="改善项跟踪" />

      {!enabled && (
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded p-4 mb-6">
          {summary.reason || card?.reason || '当前数据集没有改善项'}
        </div>
      )}

      <div className="grid grid-cols-6 gap-3 mb-6">
        <Badge label="Total" value={summary.total} color="slate" />
        <Badge label="Open" value={summary.open} color="blue" />
        <Badge label="In Progress" value={summary.in_progress} color="yellow" />
        <Badge label="Closed" value={summary.closed} color="green" />
        <Badge label="Overdue" value={summary.overdue} color="red" />
        <Badge label="Recurred" value={summary.recurred} color="orange" />
      </div>

      {actions.length > 0 && (
        <div className="bg-white rounded-lg border overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">ID</th>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">Problem</th>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">Owner</th>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">Status</th>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">Temporary Action</th>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">Recurred</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((a) => (
                <tr key={a.action_id} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-2 font-mono text-xs text-slate-500">{a.action_id}</td>
                  <td className="px-4 py-2 text-slate-800 max-w-sm">{a.problem}</td>
                  <td className="px-4 py-2 text-slate-600">{a.owner ?? '-'}</td>
                  <td className="px-4 py-2"><StatusBadge status={a.status} /></td>
                  <td className="px-4 py-2 text-slate-600 max-w-sm">{a.temporary_action ?? '-'}</td>
                  <td className="px-4 py-2">{a.recurrence_flag && <span className="text-red-500 text-xs font-medium">复发</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Badge({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    slate: 'bg-slate-100 text-slate-700',
    blue: 'bg-blue-100 text-blue-700',
    yellow: 'bg-amber-100 text-amber-700',
    green: 'bg-green-100 text-green-700',
    red: 'bg-red-100 text-red-700',
    orange: 'bg-orange-100 text-orange-700',
  };
  return (
    <div className={`rounded-lg p-3 text-center ${colors[color] ?? colors.slate}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs mt-0.5">{label}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Open: 'bg-blue-100 text-blue-700',
    'In Progress': 'bg-amber-100 text-amber-700',
    Closed: 'bg-green-100 text-green-700',
  };
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status] ?? 'bg-gray-100 text-gray-600'}`}>{status}</span>;
}
