import type { AnalyzeResponse } from '../api/datasets';

const TARGET_OPTIONS = [
  { value: '', label: '— 跳过 —' },
  { value: 'event_id', label: 'event_id (事件ID)' },
  { value: 'downtime_min', label: 'downtime_min (停机分钟)' },
  { value: 'raw_reason', label: 'raw_reason (停机原因)' },
  { value: 'raw_note', label: 'raw_note (异常备注)' },
  { value: 'machine_id', label: 'machine_id (设备编号)' },
  { value: 'operator_id', label: 'operator_id (操作员)' },
  { value: 'shift', label: 'shift (班次)' },
  { value: 'product_id', label: 'product_id (产品)' },
  { value: 'line_id', label: 'line_id (产线/位置)' },
  { value: 'event_start', label: 'event_start (开始时间)' },
  { value: 'event_end', label: 'event_end (结束时间)' },
  { value: 'run_id', label: 'run_id (批次ID)' },
  { value: 'planned_time_min', label: 'planned_time_min (计划时间)' },
  { value: 'runtime_min', label: 'runtime_min (运行时间)' },
  { value: 'actual_output', label: 'actual_output (实际产出)' },
  { value: 'good_output', label: 'good_output (良品数)' },
  { value: 'scrap_output', label: 'scrap_output (废品数)' },
];

interface Props {
  analysis: AnalyzeResponse;
  mappings: Record<string, string>;
  onChange: (sourceColumn: string, targetField: string) => void;
}

export default function ColumnMapperTable({ analysis, mappings, onChange }: Props) {
  return (
    <div className="bg-white rounded-lg border overflow-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 border-b">
          <tr>
            <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">源列名</th>
            <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">类型</th>
            <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">样例值</th>
            <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">映射到</th>
            <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">置信度</th>
            <th className="text-left px-4 py-2 text-xs text-slate-500 font-medium">问题</th>
          </tr>
        </thead>
        <tbody>
          {analysis.columns.map((col) => {
            const mapping = analysis.suggested_mappings.find(m => m.source_column === col.name);
            const currentTarget = mappings[col.name] ?? mapping?.target_field ?? '';
            const confidence = mapping?.confidence ?? 0;

            return (
              <tr key={col.name} className="border-b last:border-0 hover:bg-slate-50">
                <td className="px-4 py-2 font-medium text-slate-800">{col.name}</td>
                <td className="px-4 py-2 text-xs text-slate-500">
                  {col.is_numeric ? '数值' : col.is_datetime ? '日期' : '文本'}
                </td>
                <td className="px-4 py-2 text-xs text-slate-500 max-w-[200px] truncate">
                  {col.sample_values.slice(0, 3).join(', ')}
                </td>
                <td className="px-4 py-2">
                  <select
                    value={currentTarget}
                    onChange={(e) => onChange(col.name, e.target.value)}
                    className="border rounded px-2 py-1 text-sm w-full"
                  >
                    {TARGET_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-2">
                  <ConfidenceBadge confidence={confidence} />
                </td>
                <td className="px-4 py-2 text-xs text-amber-600 max-w-[160px]">
                  {col.detected_issues.length > 0 ? col.detected_issues.join('; ') : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  if (confidence >= 0.85) {
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">{confidence.toFixed(2)}</span>;
  }
  if (confidence >= 0.7) {
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">{confidence.toFixed(2)}</span>;
  }
  if (confidence > 0) {
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">{confidence.toFixed(2)}</span>;
  }
  return <span className="text-xs text-slate-400">—</span>;
}
