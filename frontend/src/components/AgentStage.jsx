import React, { useState } from 'react';
import { ChevronDown, Copy } from 'lucide-react';
import '../styles/agentstage.css';

const AgentStage = ({ stage, status, output }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const Icon = stage.icon;

  const toggleExpand = () => {
    if (status !== 'waiting') {
      setIsExpanded(!isExpanded);
    }
  };

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(output);
  };

  return (
    <div className={`agent-stage ${status} ${isExpanded ? 'expanded' : ''}`}>
      <div className="stage-header" onClick={toggleExpand}>
        <div className="stage-info">
          <span className="stage-number">{stage.number} /</span>
          <div className="stage-icon-wrapper">
            <Icon size={18} />
          </div>
          <h3 className="agent-name">{stage.name}</h3>
        </div>
        
        <div className="stage-status">
          <div className="status-indicator">
            <div className="status-dot"></div>
            <span className="status-text">
              {status === 'waiting' && 'Waiting'}
              {status === 'active' && 'Processing'}
              {status === 'completed' && 'Complete'}
              {status === 'failed' && 'Failed'}
            </span>
          </div>
          <ChevronDown className="chevron" size={18} />
        </div>
      </div>

      <div className="stage-content-wrapper">
        <div className="stage-content">
          {output ? (
            <div className="output-container">
              <button className="copy-stage-btn" onClick={handleCopy} title="Copy stage output">
                <Copy size={14} />
              </button>
              <div className="output-text">
                {output.split('\n').map((line, i) => (
                  <React.Fragment key={i}>
                    {line}
                    <br />
                  </React.Fragment>
                ))}
              </div>
            </div>
          ) : status === 'active' ? (
            <div className="shimmer-container">
              <div className="shimmer-line"></div>
              <div className="shimmer-line" style={{ width: '80%' }}></div>
              <div className="shimmer-line" style={{ width: '90%' }}></div>
            </div>
          ) : (
            <p className="awaiting-text">Awaiting output...</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentStage;
