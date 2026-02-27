import React from 'react';
import { Search } from 'lucide-react';
import JobCard from './JobCard';
import '../styles/joblist.css';

const JobList = ({ jobs, loading, selectedJobId, onJobSelect, onRefresh }) => {
  return (
    <aside className="job-list">
      <div className="job-list-header">
        <label className="section-label">RECENT ANALYSES</label>
        <button className="refresh-btn" onClick={onRefresh} title="Refresh list">
          <Search size={14} />
        </button>
      </div>
      
      <div className="job-list-content">
        {loading && jobs.length === 0 ? (
          <div className="list-empty-state">
            <div className="shimmer-card"></div>
            <div className="shimmer-card"></div>
            <div className="shimmer-card"></div>
          </div>
        ) : jobs.length === 0 ? (
          <div className="list-empty-state">
            <span className="empty-text">No analyses yet</span>
          </div>
        ) : (
          jobs.map((job) => (
            <JobCard
              key={job.job_id}
              job={job}
              isSelected={selectedJobId === job.job_id}
              onClick={() => onJobSelect(job.job_id)}
            />
          ))
        )}
      </div>
    </aside>
  );
};

export default JobList;
