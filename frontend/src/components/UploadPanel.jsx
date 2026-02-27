import React, { useState, useRef } from 'react';
import { FileText, Upload, Plus, ChevronUp, ChevronDown } from 'lucide-react';
import { submitAnalysis } from '../api';
import '../styles/upload.css';

const UploadPanel = ({ onJobSubmitted, isOpen, setIsOpen }) => {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('async'); // 'sync' or 'async'
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError('');
    } else {
      setError('Only PDF files are supported.');
      setFile(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF file.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const data = await submitAnalysis(file, query, mode);
      onJobSubmitted(data, mode);
      setIsOpen(false); // Collapse after submit
      setFile(null);
      setQuery('');
    } catch (err) {
      setError(err.message || 'Failed to submit analysis');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`upload-drawer ${isOpen ? 'open' : 'collapsed'}`}>
      <div className="drawer-handle" onClick={() => setIsOpen(!isOpen)}>
        <div className="handle-content">
          {isOpen ? <ChevronUp size={16} /> : <Plus size={16} />}
          <span>{isOpen ? 'COLLAPSE DRAWER' : 'NEW ANALYSIS'}</span>
        </div>
      </div>
      
      <div className="drawer-content">
        <form onSubmit={handleSubmit}>
          <div 
            className={`drop-zone ${file ? 'has-file' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('drag-over'); }}
            onDragLeave={(e) => { e.preventDefault(); e.currentTarget.classList.remove('drag-over'); }}
            onDrop={(e) => {
              e.preventDefault();
              e.currentTarget.classList.remove('drag-over');
              const droppedFile = e.dataTransfer.files[0];
              if (droppedFile?.type === 'application/pdf') {
                setFile(droppedFile);
                setError('');
              } else {
                setError('Only PDF files are supported.');
              }
            }}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              accept=".pdf" 
              style={{ display: 'none' }}
            />
            <div className="drop-zone-content">
              {file ? (
                <>
                  <FileText size={32} className="file-icon" />
                  <span className="filename">{file.name}</span>
                </>
              ) : (
                <>
                  <Upload size={32} className="upload-icon" />
                  <span className="drop-hint">Drop financial PDF or click to browse</span>
                </>
              )}
            </div>
          </div>

          <div className="input-group">
            <label className="section-label">ANALYSIS QUERY</label>
            <textarea 
              placeholder="Analyze Tesla Q2 2025 financial performance..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={2}
            />
          </div>

          <div className="mode-toggle-group">
            <label className="section-label">PROCESSING MODE</label>
            <div className="mode-toggle">
              <button 
                type="button" 
                className={`mode-btn ${mode === 'async' ? 'active' : ''}`}
                onClick={() => setMode('async')}
              >
                ASYNC (QUEUE)
              </button>
              <button 
                type="button" 
                className={`mode-btn ${mode === 'sync' ? 'active' : ''}`}
                onClick={() => setMode('sync')}
              >
                SYNC (LIVE)
              </button>
            </div>
            <p className="mode-hint">
              {mode === 'async' 
                ? 'Returns immediately. Worker processes in background.' 
                : 'Blocks until complete. Ideal for quick reports.'}
            </p>
          </div>

          {error && <div className="error-message">{error}</div>}

          <button 
            type="submit" 
            className={`submit-btn ${isSubmitting ? 'loading' : ''}`}
            disabled={!file || isSubmitting}
          >
            {isSubmitting ? (mode === 'sync' ? 'ANALYZING LIVE' : 'ENQUEUING') : 'ANALYZE DOCUMENT'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default UploadPanel;

