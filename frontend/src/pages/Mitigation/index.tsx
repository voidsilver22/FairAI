import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { jobService } from '../../services/api';
import { 
  Loader2, 
  ShieldAlert, 
  CheckCircle2, 
  TrendingUp, 
  AlertTriangle,
  Download,
  Terminal,
  ArrowRight
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import type { MetricResult, FeatureAttribution } from '../../types';

const MetricRing: React.FC<{ metric: MetricResult }> = ({ metric }) => {
  const value = metric.value;
  const threshold = metric.threshold;
  
  // Normalized value for the ring (0 to 1)
  // For 'gte', closer to 1 is better. For 'abs_lte', closer to 0 is better.
  const chartValue = metric.passed ? 1 : Math.max(0.1, value / threshold);
  
  const data = [
    { value: chartValue },
    { value: 1 - chartValue },
  ];
  
  const COLORS = metric.passed ? ['#10b981', '#f1f5f9'] : ['#ef4444', '#f1f5f9'];

  return (
    <div className="flex flex-col items-center p-5 bg-white rounded-2xl border border-slate-100 shadow-sm">
      <div className="h-28 w-28 relative flex items-center justify-center">
        <ResponsiveContainer width={112} height={112}>
          <PieChart>
            <Pie
              data={data}
              innerRadius={30}
              outerRadius={45}
              paddingAngle={0}
              dataKey="value"
              startAngle={90}
              endAngle={-270}
              stroke="none"
              isAnimationActive={false}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <span className={metric.passed ? "text-emerald-600 font-black text-lg" : "text-red-500 font-black text-lg"}>
            {value.toFixed(2)}
          </span>
        </div>
      </div>
      <span className="text-xs font-bold text-slate-800 mt-3 text-center line-clamp-1 uppercase tracking-tight">
        {(metric.metric_name || 'Metric').replace(' Difference', '').replace(' (4/5ths Rule)', '')}
      </span>
      <span className="text-[10px] font-medium text-slate-400 mt-1">
        THRESHOLD: {metric.metric_key === 'disparate_impact' ? `>${threshold}` : `±${threshold}`}
      </span>
    </div>
  );
};

const Mitigation: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [isMitigating, setIsMitigating] = useState(false);

  const { data: job, error } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobService.getJob(jobId!),
    refetchInterval: (query) => {
      const job = query.state.data;
      if (job?.status === 'completed' || job?.status === 'failed') return false;
      return 3000;
    },
    enabled: !!jobId,
  });

  if (error) return <div className="p-8 text-red-500 font-bold bg-red-50 rounded-xl border border-red-100">Error loading job data.</div>;

  if (job?.status === 'failed') {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-100 rounded-2xl p-8 flex flex-col items-center text-center space-y-4">
          <div className="bg-red-500 text-white p-4 rounded-full shadow-lg">
            <ShieldAlert size={48} />
          </div>
          <h2 className="text-2xl font-black text-red-900">Audit Pipeline Failed</h2>
          <p className="text-red-700/80 font-medium max-w-md">
            The machine learning pipeline encountered an error:
            <br />
            <span className="font-mono mt-2 block bg-red-100 p-2 rounded text-sm">{job.error || 'Unknown error'}</span>
          </p>
          <button 
            onClick={() => window.history.back()}
            className="mt-4 px-6 py-2 bg-red-900 text-white rounded-xl font-bold"
          >
            Go Back & Fix
          </button>
        </div>
      </div>
    );
  }

  if (job?.status === 'pending' || job?.status === 'running') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-8">
        <div className="relative">
          <div className="h-24 w-24 border-4 border-slate-100 border-t-primary rounded-full animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <TrendingUp size={32} className="text-primary/30" />
          </div>
        </div>
        <div className="text-center max-w-md">
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">
            {job.status === 'pending' ? 'Job Enqueued' : 'Adversarial Training Active'}
          </h2>
          <p className="text-slate-500 mt-3 font-medium leading-relaxed">
            FairAI is extracting features and optimizing the model against fairness constraints. This usually takes 30-60 seconds.
          </p>
        </div>
      </div>
    );
  }

  const report = job?.result?.report;
  if (!report) return null;

  const isCompliant = report.verification_metrics?.every(m => m.passed) ?? false;
  
  // Calculate accuracy drop
  const baselineAcc = report.baseline_performance?.accuracy || 0;
  const verificationAcc = report.verification_performance?.accuracy || 0;
  const accDrop = baselineAcc > 0 ? ((baselineAcc - verificationAcc) / baselineAcc) * 100 : 0;
  
  // Calculate fairness improvement
  const baselinePassed = (report.baseline_metrics || []).filter(m => m.passed).length;
  const verificationPassed = (report.verification_metrics || []).filter(m => m.passed).length;
  const totalMetrics = (report.baseline_metrics || []).length || 1;
  const fairnessImprovement = ((verificationPassed - baselinePassed) / totalMetrics) * 100;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-20">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            Audit ID: <span className="text-primary font-mono select-all">FX-{jobId?.slice(0, 4).toUpperCase()}</span>
          </h1>
          <p className="text-slate-500 mt-2 font-medium">Compliance verification for {job.file_uri.split('/').pop()}</p>
        </div>
        <div className="flex gap-3">
          <button className="px-5 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-600 font-bold text-sm shadow-sm hover:bg-slate-50 transition-all flex items-center gap-2">
            <Download size={18} /> Export Report
          </button>
        </div>
      </div>

      {/* Status Banner */}
      {!isCompliant ? (
        <div className="bg-red-50 border border-red-100 rounded-2xl p-6 flex items-center gap-5 shadow-sm shadow-red-100/50">
          <div className="bg-red-500 text-white p-3 rounded-xl shadow-lg shadow-red-200">
            <ShieldAlert size={28} />
          </div>
          <div className="flex-1">
            <h3 className="font-black text-red-900 text-lg">CRITICAL: Non-Compliant Model Detected</h3>
            <p className="text-red-700/80 font-medium">The current model iteration fails {totalMetrics - verificationPassed} out of {totalMetrics} core fairness metrics. Immediate mitigation is required.</p>
          </div>
        </div>
      ) : (
        <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-6 flex items-center gap-5 shadow-sm shadow-emerald-100/50 animate-in zoom-in-95 duration-500">
          <div className="bg-emerald-500 text-white p-3 rounded-xl shadow-lg shadow-emerald-200">
            <CheckCircle2 size={28} />
          </div>
          <div className="flex-1">
            <h3 className="font-black text-emerald-900 text-lg">Bias Neutralized — EEOC Compliant</h3>
            <p className="text-emerald-700/80 font-medium">Adversarial training completed successfully across all protected classes. Model is ready for production.</p>
          </div>
          <div className="px-4 py-2 bg-emerald-100 text-emerald-700 rounded-lg font-black text-xs uppercase tracking-widest">
            Status: Compliant
          </div>
        </div>
      )}

      {/* Core Metrics */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-black text-slate-900 tracking-tight">Core Fairness Metrics</h2>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">At Risk</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">In Compliance</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {(isMitigating ? report.verification_metrics : report.baseline_metrics)
            .slice(0, 5)
            .map((metric, i) => (
              <MetricRing key={i} metric={metric} />
            ))}
        </div>
      </section>

      {/* Proxy Variables or Tradeoff */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-8">
          <h3 className="text-lg font-black text-slate-900 mb-6 flex items-center gap-2">
            Discriminatory Proxy Variables Detected <TrendingUp size={20} className="text-red-500" />
          </h3>
          <p className="text-sm text-slate-400 font-medium mb-8">SHAP value analysis reveals features driving biased predictions.</p>
          <div className="space-y-6">
            {report.feature_attributions.slice(0, 4).map((attr, i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-between items-end">
                  <span className="text-sm font-bold text-slate-800">{attr.feature_name}</span>
                  <span className="text-xs font-black text-red-500">+{attr.disparity_score.toFixed(2)} Impact</span>
                </div>
                <div className="h-2.5 w-full bg-slate-50 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-red-400 to-red-500 rounded-full transition-all duration-1000"
                    style={{ width: `${Math.min(100, attr.disparity_score * 200)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-8 flex flex-col">
          <h3 className="text-lg font-black text-slate-900 mb-2">Accuracy vs. Fairness Tradeoff</h3>
          <p className="text-sm text-slate-400 font-medium mb-10">Adjusting mitigation intensity affects overall model utility.</p>
          
          <div className="flex-1 flex flex-col justify-center">
            <div className="h-3 w-full bg-gradient-to-r from-red-500 via-amber-400 to-emerald-500 rounded-full relative mb-12">
              <div className="absolute left-[85%] top-1/2 -translate-y-1/2 w-6 h-6 bg-white border-4 border-primary rounded-full shadow-lg" />
            </div>
            
            <div className="grid grid-cols-2 gap-8 border-t border-slate-50 pt-8">
              <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Historical Accuracy</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-black text-slate-900">{(verificationAcc * 100).toFixed(1)}%</span>
                  <span className="text-xs font-bold text-red-500">-{accDrop.toFixed(1)}% drop</span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Fairness Compliance</p>
                <div className="flex items-baseline justify-end gap-2">
                  <span className="text-3xl font-black text-emerald-600">{((verificationPassed / totalMetrics) * 100).toFixed(1)}%</span>
                  <span className="text-xs font-bold text-emerald-500">+{fairnessImprovement.toFixed(1)}% gain</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-6 bg-white rounded-2xl border border-slate-100 shadow-sm flex items-center justify-between hover:border-primary/30 transition-all cursor-pointer group">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl group-hover:bg-primary group-hover:text-white transition-all">
              <Terminal size={24} />
            </div>
            <div>
              <h4 className="font-black text-slate-900">Deploy FairAI API</h4>
              <p className="text-xs text-slate-400 font-medium mt-0.5">Stream mitigated predictions directly via endpoint.</p>
            </div>
          </div>
          <ArrowRight className="text-slate-300 group-hover:text-primary transition-all" />
        </div>
        <div className="p-6 bg-white rounded-2xl border border-slate-100 shadow-sm flex items-center justify-between hover:border-emerald-500/30 transition-all cursor-pointer group">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl group-hover:bg-emerald-500 group-hover:text-white transition-all">
              <Download size={24} />
            </div>
            <div>
              <h4 className="font-black text-slate-900">Download Debiased Model</h4>
              <p className="text-xs text-slate-400 font-medium mt-0.5">Export PyTorch weights for on-prem deployment.</p>
            </div>
          </div>
          <ArrowRight className="text-slate-300 group-hover:text-emerald-500 transition-all" />
        </div>
      </div>

      {/* Floating Mitigation Bar (Fixed Bottom) */}
      {!isMitigating && !isCompliant && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 w-full max-w-4xl px-4 animate-in slide-in-from-bottom-8 duration-1000 delay-500">
          <button 
            onClick={() => setIsMitigating(true)}
            className="w-full bg-slate-900 text-white p-5 rounded-2xl font-black text-lg flex items-center justify-center gap-3 shadow-2xl shadow-slate-900/40 hover:bg-slate-800 transition-all group"
          >
            Mitigate Bias — Train FairAI GAN
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      )}
    </div>
  );
};

export default Mitigation;
