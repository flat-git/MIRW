import { Link } from 'react-router-dom';
import type { DatasetSummary } from '../types';

export default function DatasetHeader({ summary, title }: { summary: DatasetSummary; title: string }) {
  const loadedAt = new Date(summary.loaded_at).toLocaleString();

  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
        <Link to="/" className="text-blue-600 hover:text-blue-700">数据源</Link>
        <span>/</span>
        <Link to={`/datasets/${summary.dataset_id}`} className="text-blue-600 hover:text-blue-700">
          {summary.source}
        </Link>
        <span>/</span>
        <span>{title}</span>
      </div>
      <div className="bg-white border rounded-lg p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800">{title}</h2>
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
              <span>数据源: <span className="font-mono text-slate-700">{summary.source}</span></span>
              <span>数据集: <span className="font-mono text-slate-700">{summary.dataset_id}</span></span>
              <span>导入时间: {loadedAt}</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-right text-xs">
            <div className="bg-slate-50 rounded px-3 py-2">
              <div className="text-slate-500">批次</div>
              <div className="text-lg font-bold text-slate-800">{summary.run_count}</div>
            </div>
            <div className="bg-slate-50 rounded px-3 py-2">
              <div className="text-slate-500">事件</div>
              <div className="text-lg font-bold text-slate-800">{summary.event_count}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function MissingDataset() {
  return (
    <div className="bg-white border rounded-lg p-8 text-center">
      <h2 className="text-lg font-semibold text-slate-800">数据集不存在或后端已重启</h2>
      <p className="text-sm text-slate-500 mt-2">本版本的导入记录只保存在后端本次运行内。</p>
      <Link to="/" className="inline-block mt-4 bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600">
        返回数据源重新导入
      </Link>
    </div>
  );
}
