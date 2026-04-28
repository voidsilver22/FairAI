import React, { useState, useEffect } from 'react';
import { Key, Globe, Shield, Database, Check } from 'lucide-react';

const Settings: React.FC = () => {
  const [apiKey, setApiKey] = useState('fl_live_51Px9K2L9z...');
  const [copied, setCopied] = useState(false);
  const [impactRatio, setImpactRatio] = useState(0.8);
  const [minGroup, setMinGroup] = useState(5);

  useEffect(() => {
    const savedRatio = localStorage.getItem('disparate_impact_threshold');
    const savedMinGroup = localStorage.getItem('min_group_representation');
    if (savedRatio) setImpactRatio(parseFloat(savedRatio));
    if (savedMinGroup) setMinGroup(parseInt(savedMinGroup, 10));
  }, []);

  const handleRegenerate = () => {
    const newKey = 'fl_live_' + Array.from(crypto.getRandomValues(new Uint8Array(16)))
      .map(b => b.toString(16).padStart(2, '0')).join('');
    setApiKey(newKey);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRatioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setImpactRatio(val);
    localStorage.setItem('disparate_impact_threshold', val.toString());
  };

  const handleMinGroupChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    setMinGroup(val);
    localStorage.setItem('min_group_representation', val.toString());
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      <div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">Settings</h1>
        <p className="text-slate-500 mt-2 font-medium">Manage your API keys, compliance thresholds, and integration settings.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-6">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
            <Key className="text-primary" size={24} />
            <h3 className="font-bold text-slate-900">API Authentication</h3>
          </div>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest">Public API Key</label>
              <div className="mt-2 flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={apiKey}
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-mono text-slate-600 focus:outline-none"
                />
                <button 
                  onClick={handleCopy}
                  className="px-5 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-colors flex items-center gap-2"
                >
                  {copied ? <Check size={16} className="text-emerald-400" /> : 'Copy'}
                </button>
              </div>
            </div>
            <button 
              onClick={handleRegenerate}
              className="text-primary text-sm font-bold hover:underline transition-all"
            >
              Regenerate Secret Key
            </button>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-6">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
            <Shield className="text-primary" size={24} />
            <h3 className="font-bold text-slate-900">Compliance Thresholds</h3>
          </div>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-3">
                <label className="text-sm font-bold text-slate-700">Disparate Impact Ratio (EEOC)</label>
                <span className="text-sm font-black text-primary bg-primary/10 px-2 py-0.5 rounded-md">{impactRatio.toFixed(2)}</span>
              </div>
              <input 
                type="range" 
                min="0.5" 
                max="1.0" 
                step="0.05" 
                value={impactRatio} 
                onChange={handleRatioChange}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary" 
              />
            </div>
            <div>
              <div className="flex justify-between mb-3">
                <label className="text-sm font-bold text-slate-700">Min. Group Representation</label>
                <span className="text-sm font-black text-primary bg-primary/10 px-2 py-0.5 rounded-md">{minGroup}%</span>
              </div>
              <input 
                type="range" 
                min="1" 
                max="20" 
                step="1" 
                value={minGroup} 
                onChange={handleMinGroupChange}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary" 
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-6 md:col-span-2">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
            <Database className="text-primary" size={24} />
            <h3 className="font-bold text-slate-900">Storage Adapters</h3>
          </div>
          <div className="space-y-4 max-w-xl">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center gap-4">
                <Globe size={24} className="text-slate-400" />
                <div>
                  <p className="text-sm font-bold text-slate-900">Google Cloud Storage</p>
                  <p className="text-xs text-slate-500 mt-0.5 font-medium">bucket: fairlens-audit-artifacts</p>
                </div>
              </div>
              <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-black rounded-lg uppercase tracking-widest">Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
