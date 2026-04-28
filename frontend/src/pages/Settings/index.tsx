import React from 'react';
import { Key, Globe, Shield, Database } from 'lucide-react';

const Settings: React.FC = () => {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 mt-2">Manage your API keys, compliance thresholds, and integration settings.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
            <Key className="text-primary" size={24} />
            <h3 className="font-bold text-slate-900">API Authentication</h3>
          </div>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Public API Key</label>
              <div className="mt-1 flex gap-2">
                <input
                  type="text"
                  readOnly
                  value="fl_live_51Px9K2L9z..."
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono text-slate-600"
                />
                <button className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-bold">Copy</button>
              </div>
            </div>
            <button className="text-primary text-sm font-bold hover:underline">Regenerate Secret Key</button>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
            <Shield className="text-primary" size={24} />
            <h3 className="font-bold text-slate-900">Compliance Thresholds</h3>
          </div>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-medium text-slate-700">Disparate Impact Ratio (EEOC)</label>
                <span className="text-sm font-bold text-primary">0.80</span>
              </div>
              <input type="range" min="0.5" max="1.0" step="0.05" defaultValue="0.8" className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary" />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-medium text-slate-700">Min. Group Representation</label>
                <span className="text-sm font-bold text-primary">5%</span>
              </div>
              <input type="range" min="1" max="20" step="1" defaultValue="5" className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
            <Database className="text-primary" size={24} />
            <h3 className="font-bold text-slate-900">Storage Adapters</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-3">
                <Globe size={20} className="text-slate-400" />
                <div>
                  <p className="text-sm font-bold text-slate-900">Google Cloud Storage</p>
                  <p className="text-xs text-slate-500">bucket: fairlens-audit-artifacts</p>
                </div>
              </div>
              <span className="px-2 py-0.5 bg-success/10 text-success text-[10px] font-bold rounded uppercase">Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
