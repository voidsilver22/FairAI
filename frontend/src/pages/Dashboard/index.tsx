import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Audit History</h1>
        <p className="text-slate-500 mt-2">View and manage previous fairness audits and remediation reports.</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600">Audit ID</th>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600">Dataset</th>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600">Status</th>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600">Compliance</th>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600">Date</th>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[1, 2, 3].map((i) => (
              <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4 text-sm font-medium text-slate-900">#AUD-2026-00{i}</td>
                <td className="px-6 py-4 text-sm text-slate-600 font-mono">historical_hiring_v{i}.csv</td>
                <td className="px-6 py-4 text-sm">
                  <span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded-md text-xs font-bold uppercase tracking-wider">Completed</span>
                </td>
                <td className="px-6 py-4 text-sm">
                  <span className="text-emerald-600 font-bold">94.2%</span>
                </td>
                <td className="px-6 py-4 text-sm text-slate-500">2026-04-{20 + i}</td>
                <td className="px-6 py-4 text-right">
                  <button className="text-primary font-semibold text-sm hover:underline">View Report</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Dashboard;
