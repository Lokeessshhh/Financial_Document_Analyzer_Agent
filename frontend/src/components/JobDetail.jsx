import React from 'react';
import { Copy, ShieldCheck, BarChart2, TrendingUp, AlertTriangle, FileText } from 'lucide-react';
import { useJobPoller } from '../hooks/useJobPoller';
import AgentStage from './AgentStage';
import StatusBadge from './StatusBadge';
import { formatTimeAgo, formatDuration } from '../utils/formatters';
import '../styles/jobdetail.css';

const STAGES = [
  { key: 'verification',        name: 'Financial Document Verifier', icon: ShieldCheck,   number: '01' },
  { key: 'financial_analysis',  name: 'Senior Financial Analyst',    icon: BarChart2,     number: '02' },
  { key: 'investment_analysis', name: 'Investment Advisor',          icon: TrendingUp,    number: '03' },
  { key: 'risk_assessment',     name: 'Risk Assessment Specialist',  icon: AlertTriangle, number: '04' },
];

const JobDetail = ({ jobId }) => {
  const { job, result, isPolling, error } = useJobPoller(jobId);

  // When jobId changes, the useJobPoller hook handles clearing state.
  // We just need to ensure the UI reflects the current job's state.

  if (!jobId) {
    return (
      <div className="job-detail-empty">
        <h2 className="empty-title">Select an analysis to view details</h2>
        <div className="decorative-line"></div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="job-detail-loading">
        <div className="shimmer-header"></div>
        <div className="shimmer-line"></div>
        <div className="shimmer-line"></div>
      </div>
    );
  }

  const handleCopyId = () => {
    navigator.clipboard.writeText(job.job_id);
  };

  const getStageStatus = (stageKey, index) => {
    if (result?.agent_outputs?.[stageKey]) return 'completed';
    if (job.status === 'completed') return 'completed'; // Ensure they don't stay 'waiting' if job is done
    if (job.status === 'failed' && !result?.agent_outputs?.[stageKey]) return 'failed';
    
    // Logic for processing stage
    if (job.status === 'processing') {
      const outputKeys = result?.agent_outputs ? Object.keys(result.agent_outputs) : [];
      if (outputKeys.length === index) return 'active';
    }
    
    return 'waiting';
  };

  const getProgressWidth = () => {
    if (job.status === 'completed') return '100%';
    if (job.status === 'failed') return '0%';
    const outputKeys = result?.agent_outputs ? Object.keys(result.agent_outputs) : [];
    return `${(outputKeys.length / 4) * 100}%`;
  };

  return (
    <div className="job-detail">
      <header className="detail-header">
        <div className="detail-header-top">
          <StatusBadge status={job.status} />
          <div className="job-id-container">
            <span className="job-id-label">JOB ID:</span>
            <span className="job-id-value">{job.job_id}</span>
            <button className="copy-btn" onClick={handleCopyId} title="Copy Job ID">
              <Copy size={14} />
            </button>
          </div>
        </div>
        
        <h1 className="detail-query">{job.query}</h1>
        
        <div className="detail-meta">
          <span className="meta-item"><FileText size={14} /> {job.original_filename}</span>
          <span className="meta-sep">·</span>
          <span className="meta-item">{formatTimeAgo(job.created_at)}</span>
          {job.duration_seconds && (
            <>
              <span className="meta-sep">·</span>
              <span className="meta-item">Duration: {formatDuration(job.duration_seconds)}</span>
            </>
          )}
        </div>
      </header>

      <div className="progress-container">
        <div className="progress-bar" style={{ width: getProgressWidth() }}></div>
      </div>

      <div className="stages-container">
        {STAGES.map((stage, index) => (
          <AgentStage
            key={stage.key}
            stage={stage}
            status={getStageStatus(stage.key, index)}
            output={result?.agent_outputs?.[stage.key]}
          />
        ))}
      </div>

      {job.status === 'completed' && job.result && (
        <section className="final-result-section">
          <div className="section-divider">
            <span className="divider-label">FINAL ANALYSIS</span>
          </div>
          <div className="result-content-wrapper">
            <button className="copy-result-btn" onClick={() => navigator.clipboard.writeText(job.result)}>
              <Copy size={16} />
            </button>
            <div className="result-text">
              {job.result.split('\n').map((line, i) => (
                <React.Fragment key={i}>
                  {line}
                  <br />
                </React.Fragment>
              ))}
            </div>
          </div>
        </section>
      )}

      {job.status === 'failed' && (
        <div className="error-panel">
          <label className="section-label">ERROR LOG</label>
          <p className="error-text">{job.error_message || 'An unknown error occurred during processing.'}</p>
        </div>
      )}
    </div>
  );
};

export default JobDetail;
