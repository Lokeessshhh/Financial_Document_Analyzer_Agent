import { useState, useEffect, useRef } from 'react';
import { getJob, getResult } from '../api';

export function useJobPoller(jobId) {
  const [job, setJob] = useState(null);
  const [result, setResult] = useState(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState(null);
  const pollIntervalRef = useRef(null);

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
      setIsPolling(false);
    }
  };

  const fetchStatus = async () => {
    if (!jobId) return;

    try {
      const jobData = await getJob(jobId);
      setJob(jobData);

      if (jobData.status === 'completed') {
        stopPolling();
        const resultData = await getResult(jobId);
        setResult(resultData);
      } else if (jobData.status === 'failed') {
        stopPolling();
      }
    } catch (err) {
      console.error('Polling error:', err);
      setError(err.message);
      stopPolling();
    }
  };

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setResult(null);
      setError(null);
      stopPolling();
      return;
    }

    setJob(null);
    setResult(null);
    setError(null);
    setIsPolling(true);

    // Initial fetch
    fetchStatus();

    // Start polling
    pollIntervalRef.current = setInterval(fetchStatus, 2500);

    return () => stopPolling();
  }, [jobId]);

  return { job, result, isPolling, error };
}
