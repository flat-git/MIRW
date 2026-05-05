import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listDatasets, loadDataset, uploadDataset } from '../api/datasets';
import type { DatasetListItem } from '../types';

const sources = [
  { id: 'maven', name: 'Maven Manufacturing', desc: '汽水灌装线，38 批次，61 停机事件' },
  { id: 'gomask', name: 'GoMask Downtime Logs', desc: '多设备车间，200 停机事件，含异常描述和处理措施' },
  { id: 'kaggle', name: 'Kaggle OEE / Downtime', desc: 'OEE/停机数据，按本地文件可用性加载' },
  { id: 'synthetic', name: 'Synthetic Demo', desc: '合成异常备注和改善项，用于演示文本流程' },
];

export default function DataSourcePage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [mapping, setMapping] = useState('');

  const refresh = () => listDatasets().then(setDatasets).catch(() => setDatasets([]));

  useEffect(() => {
    refresh();
  }, []);

  const handleLoad = async (source: string) => {
    setLoading(source);
    setError('');
    try {
      const result = await loadDataset(source);
      await refresh();
      navigate(`/datasets/${result.dataset_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading('');
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading('upload');
    setError('');
    try {
      const result = await uploadDataset(file, mapping);
      await refresh();
      navigate(`/datasets/${result.dataset_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '上传失败');
    } finally {
      setLoading('');
    }
  };

  return (
    <div>
      <h2 className="text-xl font-bold text-slate-800 mb-1">数据源中心</h2>
      <p className="text-sm text-slate-500 mb-6">先导入一个数据源，再进入该数据集的二级分析工作台。</p>

      {error && <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded p-3 mb-4">{error}</div>}

      <section className="bg-white border rounded-lg overflow-hidden mb-6">
        <div className="px-4 py-3 border-b">
          <h3 className="font-semibold text-slate-700">历史导入记录</h3>
        </div>
        {datasets.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">当前后端运行内还没有导入记录。</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">数据源</th>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">导入时间</th>
                <th className="text-right px-4 py-2 text-xs text-slate-500 font-medium">批次</th>
                <th className="text-right px-4 py-2 text-xs text-slate-500 font-medium">事件</th>
                <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">校验</th>
                <th className="text-right px-4 py-2 text-xs text-slate-500 font-medium">Open</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.dataset_id} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-2">
                    <div className="font-medium text-slate-800">{d.source}</div>
                    <div className="font-mono text-xs text-slate-400">{d.dataset_id}</div>
                  </td>
                  <td className="px-4 py-2 text-slate-500">{new Date(d.loaded_at).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-slate-700">{d.run_count}</td>
                  <td className="px-4 py-2 text-right text-slate-700">{d.event_count}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${d.validation_passed === false ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                      {d.validation_passed === false ? '失败' : '通过'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Link to={`/datasets/${d.dataset_id}`} className="text-blue-600 hover:text-blue-700 text-sm">
                      进入
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="grid grid-cols-2 gap-6">
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-slate-700 mb-3">新建内置数据源导入</h3>
          <div className="grid grid-cols-2 gap-3">
            {sources.map((s) => (
              <button
                key={s.id}
                onClick={() => handleLoad(s.id)}
                disabled={!!loading}
                className="text-left p-4 rounded-lg border hover:border-blue-300 hover:bg-blue-50 disabled:opacity-50"
              >
                <div className="font-semibold text-slate-800">{s.name}</div>
                <div className="text-xs text-slate-500 mt-1">{s.desc}</div>
                {loading === s.id && <div className="text-xs text-blue-500 mt-2">导入中...</div>}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-slate-700 mb-3">上传 Excel / CSV</h3>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-600 mb-3"
          />
          <label className="text-xs text-slate-500 block mb-1">YAML 字段映射（可选）</label>
          <textarea
            value={mapping}
            onChange={(e) => setMapping(e.target.value)}
            className="w-full h-32 border rounded px-3 py-2 text-xs font-mono"
            placeholder="留空则使用 data/sample/generic_excel_mapping.yaml"
          />
          <button
            onClick={handleUpload}
            disabled={!file || !!loading}
            className="mt-3 bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600 disabled:opacity-50"
          >
            {loading === 'upload' ? '上传导入中...' : '上传并导入'}
          </button>
        </div>
      </section>
    </div>
  );
}
