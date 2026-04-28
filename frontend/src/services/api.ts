import axios from 'axios';
import type { AsyncJobRecord, UploadInitResponse, FairnessReport } from '../types';

const API_BASE_URL = 'http://localhost:8080/api/v1';
const API_ORIGIN = 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const uploadService = {
  initUpload: async (filename: string): Promise<UploadInitResponse> => {
    const response = await api.post('/uploads/init', { filename });
    return response.data;
  },
  uploadFile: async (url: string, file: File): Promise<void> => {
    // For local development, the backend expects a POST request with multipart/form-data
    // and a field named 'file'.
    const formData = new FormData();
    formData.append('file', file);
    
    // Ensure we use the full URL if a relative path is provided
    const uploadUrl = url.startsWith('/') ? `${API_ORIGIN}${url}` : url;
    
    await axios.post(uploadUrl, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

export const jobService = {
  createDebiasJob: async (fileUri: string, config: any): Promise<{ job_id: string; status_url: string }> => {
    const response = await api.post('/jobs/debias', { file_uri: fileUri, config });
    return response.data;
  },
  getJob: async (jobId: string): Promise<AsyncJobRecord> => {
    const response = await api.get(`/jobs/${jobId}`);
    return response.data.job;
  },
  listJobs: async (): Promise<AsyncJobRecord[]> => {
    const response = await api.get('/jobs');
    return response.data.jobs;
  },
  getReport: async (jobId: string): Promise<FairnessReport> => {
    const response = await api.get(`/jobs/${jobId}/report`);
    return response.data.report;
  },
};

export default api;
