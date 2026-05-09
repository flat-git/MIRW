import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import DatasetHeader, { MissingDataset } from '../components/DatasetHeader';
import { getDataset, getExcelDownloadUrl, getAnalysisReportDownloadUrl } from '../api/datasets';
import type { DatasetSummary } from '../types';

export default function DatasetOverview() {
  const { datasetId = '' } = useParams();
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    getDataset(datasetId).then(setSummary).catch(() => setMissing(true));
  }, [datasetId]);

  if (missing) return <MissingDataset />;
  if (!summary) return <div className="text-slate-500">加载中...</div>;

  const efficiency = summary.metrics_preview?.efficiency;
  const pareto = summary.metrics_preview?.pareto ?? [];
  const cards = summary.cards ?? [];
  const caps = Object.entries(summary.capability ?? {}).filter(([k]) => k !== 'missing_fields');

  return (
    <div>
      <DatasetHeader summary={summary} title="数据集工作台" />

      <div className="grid grid-cols-4 gap-4 mb-6">
        <Stat label="流程状态" value={(summary.pipeline_status ?? 'completed') === 'completed' ? '已完成' : (summary.pipeline_status ?? '-')} />
        <Stat label="总停机" value={`${efficiency?.total_downtime_min ?? 0} min`} />
        <Stat label="停机比率" value={efficiency?.downtime_ratio != null ? `${(efficiency.downtime_ratio * 100).toFixed(1)}%` : 'N/A'} />
        <Stat label="产线效率" value={efficiency?.line_efficiency != null ? `${(efficiency.line_efficiency * 100).toFixed(1)}%` : 'N/A'} />
      </div>

      <div className="flex gap-3 mb-6">
        <a href={getExcelDownloadUrl(summary.dataset_id)} download
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-white border rounded-lg text-sm text-slate-700 hover:bg-slate-50">
          📊 下载 Excel (.xlsx)
        </a>
        <a href={getAnalysisReportDownloadUrl(summary.dataset_id)} download
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-white border rounded-lg text-sm text-slate-700 hover:bg-slate-50">
          📄 下载分析报告 (.md)
        </a>
      </div>

      <div className="grid grid-cols-3 gap-6 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-slate-700 mb-3">数据校验</h3>
          <Check label="生产批次" ok={summary.validation.production_runs.passed} />
          <Check label="停机事件" ok={summary.validation.downtime_events.passed} />
          <div className="mt-3 text-xs text-slate-500">
            缺少字段：{(summary.capability.missing_fields as string[] | undefined)?.join(', ') || '无'}
          </div>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-slate-700 mb-3">可分析能力</h3>
          <div className="grid grid-cols-2 gap-2">
            {caps.map(([key, val]) => (
              <Check key={key} label={key} ok={Boolean(val)} />
            ))}
          </div>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-slate-700 mb-3">主要损失预览</h3>
          {pareto.length === 0 ? (
            <div className="text-sm text-slate-500">暂无 Pareto 数据</div>
          ) : (
            <div className="space-y-2">
              {pareto.slice(0, 5).map((p) => (
                <div key={p.category} className="flex justify-between text-sm">
                  <span className="text-slate-600 truncate">{p.category}</span>
                  <span className="font-medium text-slate-800">{p.total_downtime_min} min</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <h3 className="font-semibold text-slate-700 mb-3">流程结果</h3>
      <div className="grid grid-cols-3 gap-4">
        {cards.map((card) => {
          const href = card.route ? `/datasets/${summary.dataset_id}/${card.route}` : `/datasets/${summary.dataset_id}`;
          const body = (
            <div className={`h-full border rounded-lg p-4 ${card.enabled ? 'bg-white hover:border-blue-300 hover:bg-blue-50' : 'bg-slate-50 opacity-70'}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="font-semibold text-slate-800">{card.title}</div>
                <span className={`text-xs px-2 py-0.5 rounded ${card.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-500'}`}>
                  {card.enabled ? '可用' : '不可用'}
                </span>
              </div>
              <div className="text-sm text-slate-500">{card.reason}</div>
            </div>
          );
          return card.enabled ? <Link key={card.key} to={href}>{body}</Link> : <div key={card.key}>{body}</div>;
        })}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-xl font-bold text-slate-800 mt-1">{value}</div>
    </div>
  );
}

function Check({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm mb-1">
      <span className={ok ? 'text-green-500' : 'text-red-400'}>{ok ? '✓' : '×'}</span>
      <span className="text-slate-600">{label}</span>
    </div>
  );
}
