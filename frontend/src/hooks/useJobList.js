import { useState, useEffect, useRef } from 'react';
import { listJobs } from '../api';

export function useJobList(refreshInterval = 5000) {
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const fetchJobs = async () => {
    try {
      const data = await listJobs();
      setJobs(data.jobs || []);
      setTotal(data.total || 0);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    intervalRef.current = setInterval(fetchJobs, refreshInterval);
    return () => clearInterval(intervalRef.current);
  }, [refreshInterval]);

  return { jobs, total, loading, error, refetch: fetchJobs };
}
