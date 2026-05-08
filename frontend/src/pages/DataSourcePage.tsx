import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listDatasets, loadDataset, analyzeFile, importFile } from '../api/datasets';
import type { AnalyzeResponse } from '../api/datasets';
import type { DatasetListItem } from '../types';
import ColumnMapperTable from '../components/ColumnMapperTable';

const sources = [
  { id: 'maven', name: 'Maven Manufacturing', desc: '汽水灌装线，38 批次，61 停机事件' },
  { id: 'gomask', name: 'GoMask Downtime Logs', desc: '多设备车间，200 停机事件，含异常描述和处理措施' },
  { id: 'kaggle', name: 'Kaggle OEE / Downtime', desc: 'OEE/停机数据，按本地文件可用性加载' },
  { id: 'synthetic', name: 'Synthetic Demo', desc: '合成异常备注和改善项，用于演示文本流程' },
];

type ImportStep = 'upload' | 'mapping' | 'result';

export default function DataSourcePage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');

  // 智能导入状态
  const [step, setStep] = useState<ImportStep>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [importResult, setImportResult] = useState<Record<string, unknown> | null>(null);

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

  // Step 1: 上传并分析
  const handleAnalyze = async () => {
    if (!file) return;
    setLoading('analyze');
    setError('');
    try {
      const result = await analyzeFile(file);
      setAnalysis(result);
      // 初始化 mappings：用 LLM 建议的映射
      const initMappings: Record<string, string> = {};
      for (const m of result.suggested_mappings) {
        if (m.target_field) {
          initMappings[m.source_column] = m.target_field;
        }
      }
      setMappings(initMappings);
      setStep('mapping');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '分析失败');
    } finally {
      setLoading('');
    }
  };

  // Step 2: 确认导入
  const handleImport = async () => {
    if (!analysis) return;
    setLoading('import');
    setError('');
    try {
      const confirmedMappings = analysis.columns.map(col => ({
        source_column: col.name,
        target_field: mappings[col.name] || null,
      }));
      const result = await importFile(analysis.analysis_id, confirmedMappings);
      setImportResult(result as unknown as Record<string, unknown>);
      setStep('result');
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '导入失败');
    } finally {
      setLoading('');
    }
  };

  const handleMappingChange = (sourceColumn: string, targetField: string) => {
    setMappings(prev => ({ ...prev, [sourceColumn]: targetField }));
  };

  const mappedCount = Object.values(mappings).filter(v => v).length;

  return (
    <div>
      <h2 className="text-xl font-bold text-slate-800 mb-1">数据源中心</h2>
      <p className="text-sm text-slate-500 mb-6">先导入一个数据源，再进入该数据集的二级分析工作台。</p>

      {error && <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded p-3 mb-4">{error}</div>}

      {/* 历史导入记录 */}
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
                <th className="text-right px-4 py-2 text-xs text-slate-500 font-medium"></th>
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
                    <Link to={`/datasets/${d.dataset_id}`} className="text-blue-600 hover:text-blue-700 text-sm">进入</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="grid grid-cols-2 gap-6">
        {/* 内置数据源 */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-slate-700 mb-3">内置数据源</h3>
          <div className="grid grid-cols-2 gap-3">
            {sources.map((s) => (
              <button key={s.id} onClick={() => handleLoad(s.id)} disabled={!!loading}
                className="text-left p-4 rounded-lg border hover:border-blue-300 hover:bg-blue-50 disabled:opacity-50">
                <div className="font-semibold text-slate-800">{s.name}</div>
                <div className="text-xs text-slate-500 mt-1">{s.desc}</div>
                {loading === s.id && <div className="text-xs text-blue-500 mt-2">导入中...</div>}
              </button>
            ))}
          </div>
        </div>

        {/* 智能导入 3 步向导 */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-slate-700 mb-3">智能导入（LLM 辅助列映射）</h3>

          {/* Step 指示器 */}
          <div className="flex gap-2 mb-4">
            {['上传', '确认映射', '导入结果'].map((label, i) => (
              <div key={label} className={`flex items-center gap-1 text-xs ${['upload','mapping','result'].indexOf(step) >= i ? 'text-blue-600 font-medium' : 'text-slate-400'}`}>
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-white text-xs ${['upload','mapping','result'].indexOf(step) >= i ? 'bg-blue-500' : 'bg-slate-300'}`}>{i + 1}</span>
                {label}
              </div>
            ))}
          </div>

          {/* Step 1: 上传 */}
          {step === 'upload' && (
            <div>
              <input type="file" accept=".csv,.xlsx,.xls"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-slate-600 mb-3" />
              <p className="text-xs text-slate-400 mb-3">支持任意列名和脏数据，系统会自动识别字段含义。</p>
              <button onClick={handleAnalyze} disabled={!file || !!loading}
                className="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600 disabled:opacity-50">
                {loading === 'analyze' ? '分析中...' : '开始分析'}
              </button>
            </div>
          )}

          {/* Step 2: 确认映射 */}
          {step === 'mapping' && analysis && (
            <div>
              <div className="text-xs text-slate-500 mb-2">
                {analysis.file_name} · {analysis.total_rows} 行 · 已映射 {mappedCount}/{analysis.columns.length} 列
                {analysis.unmapped_columns.length > 0 && <span className="text-amber-600"> · {analysis.unmapped_columns.length} 列未识别</span>}
              </div>
              <ColumnMapperTable analysis={analysis} mappings={mappings} onChange={handleMappingChange} />
              <div className="flex gap-2 mt-3">
                <button onClick={() => { setStep('upload'); setAnalysis(null); }}
                  className="px-3 py-1.5 rounded text-sm bg-gray-100 text-slate-600 hover:bg-gray-200">返回</button>
                <button onClick={handleImport} disabled={!!loading}
                  className="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600 disabled:opacity-50">
                  {loading === 'import' ? '导入中...' : '确认导入'}
                </button>
              </div>
            </div>
          )}

          {/* Step 3: 导入结果 */}
          {step === 'result' && importResult && (
            <div>
              <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded p-3 mb-3">
                导入成功！数据集 ID: <span className="font-mono">{String(importResult.dataset_id)}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                <div className="bg-slate-50 rounded p-2"><span className="text-slate-500">事件数:</span> {String(importResult.event_count)}</div>
                <div className="bg-slate-50 rounded p-2"><span className="text-slate-500">批次:</span> {String(importResult.run_count)}</div>
              </div>
              <button onClick={() => navigate(`/datasets/${importResult.dataset_id}`)}
                className="w-full bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600">
                进入数据集
              </button>
              <button onClick={() => { setStep('upload'); setFile(null); setAnalysis(null); setImportResult(null); }}
                className="w-full mt-2 px-4 py-2 rounded text-sm bg-gray-100 text-slate-600 hover:bg-gray-200">
                继续导入
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
