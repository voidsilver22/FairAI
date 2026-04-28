import React, { useState } from 'react';
import { Upload, FileText, CheckCircle2, Loader2, ShieldAlert } from 'lucide-react';
import { uploadService, jobService } from '../../services/api';
import { useNavigate } from 'react-router-dom';

const NewAudit: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [fileUri, setFileUri] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      setIsUploading(true);
      setUploadProgress(10);
      
      const { upload_url, file_uri } = await uploadService.initUpload(file.name);
      setUploadProgress(30);
      
      await uploadService.uploadFile(upload_url, file);
      setUploadProgress(100);
      setFileUri(file_uri);
    } catch (error) {
      console.error('Upload failed', error);
      alert('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const startAudit = async () => {
    if (!fileUri) return;
    
    try {
      const { job_id } = await jobService.createDebiasJob(fileUri, {
        label_column: 'hired',
        protected_attributes: ['gender', 'race', 'age'],
      });
      navigate(`/mitigation/${job_id}`);
    } catch (error) {
      console.error('Failed to start audit', error);
      alert('Failed to start audit.');
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">New Fairness Audit</h1>
        <p className="text-slate-500 mt-2">Upload your historical hiring dataset to begin the bias mitigation pipeline.</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        {!fileUri ? (
          <div 
            className="border-2 border-dashed border-slate-200 rounded-xl p-12 flex flex-col items-center justify-center space-y-4 hover:border-primary/50 transition-colors bg-slate-50/50"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
            }}
          >
            <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center">
              <Upload className="text-primary h-8 w-8" />
            </div>
            <div className="text-center">
              <p className="text-lg font-semibold text-slate-900">
                {file ? file.name : 'Click or drag dataset to upload'}
              </p>
              <p className="text-sm text-slate-500">Supports CSV, JSON, or Parquet</p>
            </div>
            <input 
              type="file" 
              className="hidden" 
              id="file-upload" 
              onChange={handleFileChange}
              accept=".csv,.json,.parquet"
            />
            <label 
              htmlFor="file-upload"
              className="px-6 py-2 bg-white border border-slate-200 rounded-lg font-medium text-slate-700 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
            >
              Select File
            </label>
            
            {file && !isUploading && (
              <button
                onClick={handleUpload}
                className="mt-4 px-8 py-3 bg-primary text-white rounded-lg font-bold shadow-md hover:bg-primary/90 transition-all flex items-center gap-2"
              >
                Upload & Initialize
              </button>
            )}

            {isUploading && (
              <div className="w-full max-w-xs mt-4">
                <div className="flex justify-between text-xs mb-1">
                  <span>Uploading...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                  <div 
                    className="bg-primary h-full transition-all duration-300" 
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="w-20 h-20 bg-success/10 rounded-full flex items-center justify-center">
              <CheckCircle2 className="text-success h-10 w-10" />
            </div>
            <div className="text-center">
              <h2 className="text-xl font-bold text-slate-900">Dataset Ready</h2>
              <p className="text-slate-500">{file?.name}</p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => setFileUri(null)}
                className="px-6 py-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 font-medium"
              >
                Change File
              </button>
              <button
                onClick={startAudit}
                className="px-8 py-3 bg-primary text-white rounded-lg font-bold shadow-lg hover:bg-primary/90 transition-all flex items-center gap-2"
              >
                Run Compliance Audit
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="w-10 h-10 bg-indigo-50 text-indigo-600 rounded-lg flex items-center justify-center mb-4">
            <FileText size={20} />
          </div>
          <h3 className="font-bold text-slate-900">Data Scrubber</h3>
          <p className="text-sm text-slate-500 mt-1">Automatic masking of PII and direct identifiers during ingestion.</p>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="w-10 h-10 bg-amber-50 text-amber-600 rounded-lg flex items-center justify-center mb-4">
            <ShieldAlert size={20} />
          </div>
          <h3 className="font-bold text-slate-900">Proxy Detection</h3>
          <p className="text-sm text-slate-500 mt-1">Identifies hidden bias patterns in non-protected features.</p>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center mb-4">
            <CheckCircle2 size={20} />
          </div>
          <h3 className="font-bold text-slate-900">Compliance Check</h3>
          <p className="text-sm text-slate-500 mt-1">Validated against EEOC 4/5ths rule and disparate impact standards.</p>
        </div>
      </div>
    </div>
  );
};

export default NewAudit;
