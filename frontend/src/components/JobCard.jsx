import React from 'react';
import { formatTimeAgo, truncate } from '../utils/formatters';
import StatusBadge from './StatusBadge';

const JobCard = ({ job, isSelected, onClick }) => {
  return (
    <div 
      className={`job-card ${isSelected ? 'selected' : ''}`} 
      onClick={onClick}
    >
      <div className="job-card-top">
        <div className={`status-dot ${job.status}`}></div>
        <span className="job-query">{truncate(job.query, 35)}</span>
      </div>
      <div className="job-card-mid">
        <span className="job-filename">{truncate(job.original_filename, 20)}</span>
        <span className="job-time">{formatTimeAgo(job.created_at)}</span>
      </div>
      <div className="job-card-bottom">
        <StatusBadge status={job.status} />
        {job.duration_seconds && (
          <span className="job-duration">{job.duration_seconds}s</span>
        )}
      </div>
    </div>
  );
};

export default JobCard;
