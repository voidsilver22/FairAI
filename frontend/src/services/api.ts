import axios from 'axios';
import type { AsyncJobRecord, UploadInitResponse, FairnessReport } from '../types';

const API_BASE_URL = 'http://localhost:8080/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const uploadService = {
  initUpload: async (filename: string): Promise<UploadInitResponse> => {
    const response = await api.post('/uploads/init', { filename });
    return response.data;
  },
  uploadFile: async (url: string, file: File): Promise<void> => {
    // In local mode, we might need to send as multipart or raw bytes
    // For now, assume PUT with binary as common for signed URLs
    await axios.put(url, file, {
      headers: {
        'Content-Type': file.type || 'application/octet-stream',
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
    return response.data;
  },
  listJobs: async (): Promise<AsyncJobRecord[]> => {
    const response = await api.get('/jobs');
    return response.data.jobs;
  },
  getReport: async (jobId: string): Promise<FairnessReport> => {
    const response = await api.get(`/jobs/${jobId}/report`);
    return response.data;
  },
};

export default api;
