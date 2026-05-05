import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import DatasetHeader, { MissingDataset } from '../components/DatasetHeader';
import { getDataset } from '../api/datasets';
import { generateIeWeekly, generateCapa } from '../api/reports';
import type { DatasetSummary, ReportResponse } from '../types';

type ReportTab = 'ie-weekly' | 'capa';

export default function ReportPage() {
  const { datasetId = '' } = useParams();
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [tab, setTab] = useState<ReportTab>('ie-weekly');
  const [period, setPeriod] = useState('当前导入数据集');
  const [reports, setReports] = useState<Partial<Record<ReportTab, ReportResponse>>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    getDataset(datasetId).then(setDataset).catch(() => setMissing(true));
  }, [datasetId]);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const r = tab === 'ie-weekly'
        ? await generateIeWeekly(datasetId, period)
        : await generateCapa(datasetId, period);
      setReports((prev) => ({ ...prev, [tab]: r }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '生成失败');
    } finally {
      setLoading(false);
    }
  };

  if (missing) return <MissingDataset />;
  if (!dataset) return <div className="text-slate-500">加载中...</div>;

  const card = dataset.cards?.find((c) => c.key === 'reports');
  const enabled = card?.enabled ?? false;
  const report = reports[tab] ?? null;
  const checkerEntries = report ? Object.entries(report.check_result) : [];

  return (
    <div>
      <DatasetHeader summary={dataset} title="报告生成" />

      {!enabled && (
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded p-4 mb-6">
          {card?.reason ?? '当前数据集不支持报告生成'}
        </div>
      )}

      <div className="bg-white rounded-lg border p-4 mb-6">
        <div className="flex gap-2 mb-4">
          {(['ie-weekly', 'capa'] as ReportTab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              disabled={!enabled}
              className={`px-3 py-1.5 rounded text-sm disabled:opacity-50 ${
                tab === t ? 'bg-blue-500 text-white' : 'bg-gray-100 text-slate-600 hover:bg-gray-200'
              }`}>
              {t === 'ie-weekly' ? 'IE 周报' : '质量 CAPA'}
            </button>
          ))}
        </div>
        <div className="flex gap-3 items-end">
          <div>
            <label className="text-xs text-slate-500 block mb-1">报告标识</label>
            <input value={period} onChange={(e) => setPeriod(e.target.value)}
              disabled={!enabled} className="border rounded px-3 py-2 text-sm w-40 disabled:bg-slate-100" />
            <div className="text-xs text-slate-400 mt-1">仅用于报告标题，不过滤数据范围</div>
          </div>
          <button onClick={handleGenerate} disabled={loading || !enabled}
            className="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600 disabled:opacity-50">
            {loading ? '生成中...' : '生成报告'}
          </button>
        </div>
        {error && <div className="text-red-500 text-sm mt-3">{error}</div>}
      </div>

      {report && (
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 bg-white rounded-lg border p-6 overflow-auto max-h-[70vh]">
            <div className="markdown-body">
              <ReactMarkdown>{report.report_markdown}</ReactMarkdown>
            </div>
          </div>
          <div>
            <div className="bg-white rounded-lg border p-4">
              <h3 className="font-semibold text-slate-700 mb-3">报告校验</h3>
              <div className="space-y-2">
                {checkerEntries.map(([key, val]) => (
                  <div key={key} className="flex items-center gap-2 text-sm">
                    <span className={val ? 'text-green-500' : 'text-red-400'}>{val ? '✓' : '×'}</span>
                    <span className="text-slate-600 text-xs">{key}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
