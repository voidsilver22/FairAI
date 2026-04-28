import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { jobService } from '../../services/api';
import { 
  Search, 
  Filter, 
  ChevronRight, 
  User, 
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  Info,
  Terminal
} from 'lucide-react';
import type { CounterfactualFlip } from '../../types';

const CounterfactualExplorer: React.FC = () => {
  const [selectedExample, setSelectedExample] = useState<CounterfactualFlip | null>(null);

  // Fetch all jobs to find the latest completed one with a report
  const { data: jobs, isLoading: isLoadingJobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobService.listJobs(),
  });

  const latestCompletedJob = jobs
    ?.filter(j => j.status === 'completed' && j.result?.report)
    .sort((a, b) => new Date(b.completed_at || 0).getTime() - new Date(a.completed_at || 0).getTime())[0];

  const report = latestCompletedJob?.result?.report;
  const counterfactuals = report?.counterfactuals || [];
  
  // Flatten all examples from all counterfactual audits
  const allExamples = counterfactuals.flatMap(audit => 
    audit.examples.map(example => ({
      ...example,
      protected_attribute: audit.protected_attribute
    }))
  );

  if (isLoadingJobs) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!latestCompletedJob) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
        <div className="bg-slate-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6">
          <AlertCircle className="text-slate-400" size={32} />
        </div>
        <h2 className="text-xl font-black text-slate-900 tracking-tight">No Completed Audits Found</h2>
        <p className="text-slate-500 mt-2 max-w-sm mx-auto">
          You need to complete at least one fairness audit to explore counterfactual examples.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">Counterfactual Explorer</h1>
        <p className="text-slate-500 mt-2 font-medium">
          Analyzing individual data points where model predictions flip based on protected attribute changes.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* List Pane */}
        <div className="lg:col-span-1 bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden h-fit">
          <div className="p-5 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
            <span className="font-black text-slate-700 text-xs uppercase tracking-widest">
              Impacted Rows ({allExamples.length})
            </span>
          </div>
          <div className="divide-y divide-slate-50 max-h-[600px] overflow-y-auto">
            {allExamples.map((ex, i) => (
              <div 
                key={i} 
                onClick={() => setSelectedExample(ex)}
                className={`p-5 cursor-pointer transition-all border-l-4 ${
                  selectedExample === ex ? 'bg-primary/5 border-primary' : 'hover:bg-slate-50 border-transparent'
                }`}
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400">
                      <Terminal size={18} />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm">Row Index: {ex.row_index}</h4>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
                        Attr: {ex.protected_attribute}
                      </p>
                    </div>
                  </div>
                  <ChevronRight size={16} className={selectedExample === ex ? 'text-primary' : 'text-slate-300'} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Details Pane */}
        <div className="lg:col-span-2 space-y-6">
          {selectedExample ? (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-10 space-y-8 animate-in slide-in-from-right-4 duration-500">
              <div className="flex justify-between items-start border-b border-slate-50 pb-8">
                <div className="flex gap-5 items-center">
                  <div className="w-16 h-16 bg-gradient-to-br from-slate-100 to-slate-200 rounded-2xl flex items-center justify-center text-slate-400 text-2xl font-black">
                    #{selectedExample.row_index}
                  </div>
                  <div>
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight">Example Attribution</h2>
                    <p className="text-slate-500 font-medium">Counterfactual analysis for row index {selectedExample.row_index}</p>
                  </div>
                </div>
                <div className={`px-4 py-2 rounded-xl font-black text-xs uppercase tracking-widest ${
                  selectedExample.original_prediction !== selectedExample.alternative_prediction 
                    ? 'bg-red-50 text-red-600' 
                    : 'bg-emerald-50 text-emerald-600'
                }`}>
                  {selectedExample.original_prediction !== selectedExample.alternative_prediction ? 'Prediction Flip' : 'Stable'}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100">
                  <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-4">Original State</span>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-bold text-slate-600">{selectedExample.protected_attribute}</span>
                      <span className="text-sm font-black text-slate-900 px-2 py-1 bg-white rounded-lg border border-slate-200">
                        {selectedExample.original_group}
                      </span>
                    </div>
                    <div className="flex justify-between items-center pt-4 border-t border-slate-200">
                      <span className="text-sm font-bold text-slate-600">Prediction</span>
                      <span className={`text-sm font-black px-3 py-1 rounded-lg ${
                        selectedExample.original_prediction === 1 ? 'bg-emerald-500 text-white' : 'bg-slate-300 text-slate-700'
                      }`}>
                        {selectedExample.original_prediction === 1 ? 'HIRED' : 'REJECTED'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-primary/5 rounded-2xl border border-primary/10 relative">
                  <span className="text-[10px] font-black text-primary uppercase tracking-widest block mb-4">Alternative State</span>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-bold text-primary/70">{selectedExample.protected_attribute}</span>
                      <span className="text-sm font-black text-primary px-2 py-1 bg-white rounded-lg border border-primary/20">
                        {selectedExample.alternative_group}
                      </span>
                    </div>
                    <div className="flex justify-between items-center pt-4 border-t border-primary/10">
                      <span className="text-sm font-bold text-primary/70">Prediction</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-black px-3 py-1 rounded-lg ${
                          selectedExample.alternative_prediction === 1 ? 'bg-emerald-500 text-white' : 'bg-slate-300 text-slate-700'
                        }`}>
                          {selectedExample.alternative_prediction === 1 ? 'HIRED' : 'REJECTED'}
                        </span>
                        {selectedExample.original_prediction !== selectedExample.alternative_prediction && (
                          <div className="bg-red-500 p-1 rounded-full text-white animate-pulse">
                            <ArrowRight size={12} />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-slate-50 rounded-2xl p-6 flex gap-4 border border-slate-100">
                <div className="text-primary pt-1">
                  <Info size={20} />
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">Understanding this result</h4>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                    This counterfactual test shows that by simply changing the <strong>{selectedExample.protected_attribute}</strong> from 
                    <em> {selectedExample.original_group}</em> to <em>{selectedExample.alternative_group}</em>, 
                    the model's prediction <strong>{selectedExample.original_prediction !== selectedExample.alternative_prediction ? 'changed' : 'remained the same'}</strong>. 
                    Flips indicate areas where the model is using protected attributes as a high-signal proxy for decision making.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-100 border-dashed shadow-sm p-12 text-center h-full flex flex-col justify-center items-center">
              <div className="bg-slate-50 w-20 h-20 rounded-full flex items-center justify-center mb-6">
                <Search className="text-slate-300" size={32} />
              </div>
              <h3 className="text-xl font-black text-slate-900 tracking-tight">Select an example to inspect</h3>
              <p className="text-slate-500 mt-2 max-w-xs font-medium">
                Choose a row from the sidebar to explore its counterfactual predictions and flip-risk.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CounterfactualExplorer;
