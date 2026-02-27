const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Submit new analysis
export async function submitAnalysis(file, query) {
  const form = new FormData();
  form.append('file', file);
  form.append('query', query || 'Analyze this financial document for investment insights');
  
  const res = await fetch(`${BASE_URL}/analyze/async`, { 
    method: 'POST', 
    body: form 
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'An unexpected error occurred' }));
    throw new Error(errorData.detail || 'Failed to submit analysis');
  }
  
  return res.json(); // { job_id, task_id, status, query, file_processed }
}

// Get single job status
export async function getJob(jobId) {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}`);
  if (!res.ok) throw new Error('Failed to fetch job status');
  return res.json();
}

// Get job result (agent outputs)
export async function getResult(jobId) {
  const res = await fetch(`${BASE_URL}/results/${jobId}`);
  if (!res.ok) return null; // not ready yet
  return res.json();
}

// List all jobs
export async function listJobs(limit = 30) {
  const res = await fetch(`${BASE_URL}/jobs?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch jobs list');
  return res.json(); // { jobs: [...], total }
}

// Health check
export async function checkHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    const data = await res.json();
    return res.ok && data.status === 'healthy';
  } catch { 
    return false; 
  }
}
