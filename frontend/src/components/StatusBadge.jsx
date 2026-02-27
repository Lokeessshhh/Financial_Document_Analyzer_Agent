import React from 'react';
import '../styles/statusbadge.css';

const StatusBadge = ({ status }) => {
  const getLabel = (s) => {
    switch (s) {
      case 'pending': return 'PENDING';
      case 'processing': return 'ANALYZING';
      case 'completed': return 'COMPLETE';
      case 'failed': return 'FAILED';
      default: return s?.toUpperCase() || 'UNKNOWN';
    }
  };

  return (
    <div className={`status-badge ${status}`}>
      <span className="badge-text">{getLabel(status)}</span>
    </div>
  );
};

export default StatusBadge;
