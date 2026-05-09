import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import DatasetHeader, { MissingDataset } from '../components/DatasetHeader';
import { getDataset } from '../api/datasets';
import { generateIeWeekly, generateCapa, getReportHistory, getReportDownloadUrl } from '../api/reports';

function downloadFile(url: string, filename: string) {
  fetch(url)
    .then(res => res.blob())
    .then(blob => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    });
}
import type { DatasetSummary, ReportResponse, ReportHistoryItem } from '../types';

type ReportTab = 'ie-weekly' | 'capa';

export default function ReportPage() {
  const { datasetId = '' } = useParams();
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [tab, setTab] = useState<ReportTab>('ie-weekly');
  const [period, setPeriod] = useState('当前导入数据集');
  const [reports, setReports] = useState<Partial<Record<ReportTab, ReportResponse>>>({});
  const [history, setHistory] = useState<ReportHistoryItem[]>([]);
  const [viewingHistory, setViewingHistory] = useState<ReportHistoryItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    getDataset(datasetId).then(setDataset).catch(() => setMissing(true));
    getReportHistory(datasetId).then(setHistory).catch(() => {});
  }, [datasetId]);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const r = tab === 'ie-weekly'
        ? await generateIeWeekly(datasetId, period)
        : await generateCapa(datasetId, period);
      setReports((prev) => ({ ...prev, [tab]: r }));
      getReportHistory(datasetId).then(setHistory).catch(() => {});
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

      {/* 查看历史报告 */}
      {viewingHistory && (
        <div className="mt-6 grid grid-cols-3 gap-6">
          <div className="col-span-2 bg-white rounded-lg border p-6 overflow-auto max-h-[60vh]">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-slate-700">{viewingHistory.report_type} · {viewingHistory.period}</h3>
              <button onClick={() => setViewingHistory(null)} className="text-slate-400 hover:text-slate-600 text-sm">关闭</button>
            </div>
            <div className="markdown-body">
              <ReactMarkdown>{viewingHistory.report_markdown}</ReactMarkdown>
            </div>
          </div>
          <div>
            <div className="bg-white rounded-lg border p-4">
              <h3 className="font-semibold text-slate-700 mb-3">报告校验</h3>
              {Object.entries(viewingHistory.check_result).map(([key, val]) => (
                <div key={key} className="flex items-center gap-2 text-sm mb-1">
                  <span className={val ? 'text-green-500' : 'text-red-400'}>{val ? '✓' : '×'}</span>
                  <span className="text-slate-600 text-xs">{key}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 历史报告列表 */}
      {history.length > 0 && (
        <div className="mt-6">
          <h3 className="font-semibold text-slate-700 mb-3">历史报告</h3>
          <div className="space-y-2">
            {history.map((h) => (
              <div key={h.report_id} className="bg-white border rounded-lg p-3 flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-slate-800">{h.report_type}</span>
                  <span className="text-xs text-slate-500 ml-2">{h.period}</span>
                  <span className="text-xs text-slate-400 ml-2">{new Date(h.generated_at).toLocaleString()}</span>
                  <div className="flex gap-2 mt-1">
                    {Object.entries(h.check_result).slice(0, 3).map(([k, v]) => (
                      <span key={k} className={`text-xs ${v ? 'text-green-500' : 'text-red-400'}`}>
                        {v ? '✓' : '×'} {k}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => setViewingHistory(h)}
                    className="px-3 py-1 rounded text-xs bg-slate-100 text-slate-600 hover:bg-slate-200">查看</button>
                  <button onClick={() => downloadFile(getReportDownloadUrl(datasetId, h.report_id), `${h.report_type}_${h.period}.md`)}
                    className="px-3 py-1 rounded text-xs bg-blue-50 text-blue-600 hover:bg-blue-100">下载 .md</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
