import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { jobService } from '../../services/api';
import { Loader2, Inbox } from 'lucide-react';

const Dashboard: React.FC = () => {
  const { data: jobs, isLoading, error } = useQuery({
    queryKey: ['jobs'],
    queryFn: jobService.listJobs,
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <Loader2 className="animate-spin text-primary w-12 h-12" />
        <p className="text-slate-500 mt-4 font-medium">Loading audit history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-red-500 font-bold bg-red-50 rounded-xl border border-red-100">
        Error loading audit history.
      </div>
    );
  }

  const sortedJobs = [...(jobs || [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-20">
      <div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">Audit History</h1>
        <p className="text-slate-500 mt-2 font-medium">View and manage previous fairness audits and remediation reports.</p>
      </div>

      {sortedJobs.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 flex flex-col items-center text-center shadow-sm">
          <div className="bg-slate-50 p-4 rounded-full mb-4">
            <Inbox className="w-12 h-12 text-slate-300" />
          </div>
          <h3 className="text-xl font-bold text-slate-900">No Audits Found</h3>
          <p className="text-slate-500 mt-2 max-w-sm">
            You haven't run any compliance audits yet. Upload a dataset to get started.
          </p>
          <Link 
            to="/new-audit" 
            className="mt-6 px-6 py-2.5 bg-primary text-white rounded-xl font-bold shadow-lg shadow-primary/30 hover:bg-primary/90 transition-all"
          >
            Start New Audit
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 text-sm font-black text-slate-600 uppercase tracking-wider">Audit ID</th>
                <th className="px-6 py-4 text-sm font-black text-slate-600 uppercase tracking-wider">Dataset</th>
                <th className="px-6 py-4 text-sm font-black text-slate-600 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-sm font-black text-slate-600 uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 text-sm font-black text-slate-600 uppercase tracking-wider"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedJobs.map((job) => (
                <tr key={job.job_id} className="hover:bg-slate-50/80 transition-colors group">
                  <td className="px-6 py-4 text-sm font-bold text-slate-900">
                    FX-{job.job_id.slice(0, 4).toUpperCase()}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600 font-mono">
                    {job.file_uri.split('/').pop() || 'dataset.csv'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {job.status === 'completed' && (
                      <span className="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-lg text-xs font-black uppercase tracking-widest">Completed</span>
                    )}
                    {job.status === 'failed' && (
                      <span className="px-3 py-1 bg-red-100 text-red-700 rounded-lg text-xs font-black uppercase tracking-widest">Failed</span>
                    )}
                    {(job.status === 'pending' || job.status === 'running') && (
                      <span className="px-3 py-1 bg-amber-100 text-amber-700 rounded-lg text-xs font-black uppercase tracking-widest flex items-center gap-2 w-max">
                        <Loader2 className="w-3 h-3 animate-spin" /> Processing
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-500 font-medium">
                    {new Date(job.created_at).toLocaleDateString()} {new Date(job.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link 
                      to={`/mitigation/${job.job_id}`}
                      className="text-primary font-bold text-sm hover:underline opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      View Report →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
