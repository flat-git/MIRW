import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { BarChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart } from 'recharts';
import DatasetHeader, { MissingDataset } from '../components/DatasetHeader';
import { getDataset } from '../api/datasets';
import { getSummary, getPareto, getDowntimeByGroup } from '../api/metrics';
import type { DatasetSummary, EfficiencySummary, ParetoItem, DowntimeGroupItem } from '../types';

export default function LossDashboard() {
  const { datasetId = '' } = useParams();
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [summary, setSummary] = useState<EfficiencySummary | null>(null);
  const [pareto, setPareto] = useState<ParetoItem[]>([]);
  const [byProduct, setByProduct] = useState<DowntimeGroupItem[]>([]);
  const [byOperator, setByOperator] = useState<DowntimeGroupItem[]>([]);
  const [byMachine, setByMachine] = useState<DowntimeGroupItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getDataset(datasetId),
      getSummary(datasetId),
      getPareto(datasetId, 10),
      getDowntimeByGroup(datasetId, 'product').catch(() => []),
      getDowntimeByGroup(datasetId, 'operator').catch(() => []),
      getDowntimeByGroup(datasetId, 'machine').catch(() => []),
    ]).then(([d, s, p, prod, op, machine]) => {
      setDataset(d);
      setSummary(s);
      setPareto(p);
      setByProduct(prod);
      setByOperator(op);
      setByMachine(machine);
    }).catch(() => setMissing(true)).finally(() => setLoading(false));
  }, [datasetId]);

  if (missing) return <MissingDataset />;
  if (loading || !dataset || !summary) return <div className="text-slate-500">加载中...</div>;

  return (
    <div>
      <DatasetHeader summary={dataset} title="停机损失分析" />

      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard label="总停机" value={`${summary.total_downtime_min ?? 0} min`} />
        <MetricCard label="停机比率" value={summary.downtime_ratio != null ? `${(summary.downtime_ratio * 100).toFixed(1)}%` : 'N/A'} />
        <MetricCard label="产线效率" value={summary.line_efficiency != null ? `${(summary.line_efficiency * 100).toFixed(1)}%` : 'N/A'} />
        <MetricCard label="停机事件" value={String(summary.total_events)} />
      </div>

      {pareto.length > 0 && (
        <div className="bg-white rounded-lg border p-4 mb-6">
          <h3 className="font-semibold text-slate-700 mb-3">主要损失 Pareto</h3>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={pareto}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="category" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
              <YAxis yAxisId="left" label={{ value: 'min', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 1]} tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`} />
              <Tooltip />
              <Bar yAxisId="left" dataKey="total_downtime_min" fill="#3b82f6" name="停机 (min)" radius={[4, 4, 0, 0]} />
              <Line yAxisId="right" dataKey="cumulative_ratio" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} name="累计比率" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <GroupChart title="按产品" data={byProduct.slice(0, 8)} dataKey="product_id" color="#6366f1" />
        <GroupChart title="按操作员" data={byOperator.slice(0, 8)} dataKey="operator_id" color="#f59e0b" />
        <GroupChart title="按设备" data={byMachine.slice(0, 8)} dataKey="machine_id" color="#10b981" />
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-bold text-slate-800 mt-1">{value}</div>
    </div>
  );
}

function GroupChart({ title, data, dataKey, color }: { title: string; data: DowntimeGroupItem[]; dataKey: string; color: string }) {
  if (data.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold text-slate-700 mb-3">{title}</h3>
        <div className="text-sm text-slate-500">当前数据集不支持该维度。</div>
      </div>
    );
  }
  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="font-semibold text-slate-700 mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={dataKey} tick={{ fontSize: 11 }} />
          <YAxis />
          <Tooltip />
          <Bar dataKey="total_downtime_min" fill={color} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
