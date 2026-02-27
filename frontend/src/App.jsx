import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import UploadPanel from './components/UploadPanel';
import JobList from './components/JobList';
import JobDetail from './components/JobDetail';
import { useJobList } from './hooks/useJobList';
import './styles/global.css';

function App() {
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);
  const { jobs, loading, refetch } = useJobList();

  // Handle new job submission
  const handleJobSubmitted = (data, mode) => {
    const newJobId = data.job_id;
    refetch();
    if (newJobId) {
      setSelectedJobId(newJobId);
    }
  };

  const handleJobSelect = (id) => {
    setSelectedJobId(id);
    setIsDrawerOpen(false); // Collapse drawer when a job is selected
  };

  return (
    <div className="app-container">
      <div className="grain-overlay"></div>
      <Header />
      
      <main className="main-content">
        <UploadPanel 
          onJobSubmitted={handleJobSubmitted} 
          isOpen={isDrawerOpen}
          setIsOpen={setIsDrawerOpen}
        />
        
        <div className="workspace">
          <JobList 
            jobs={jobs} 
            loading={loading} 
            selectedJobId={selectedJobId} 
            onJobSelect={handleJobSelect}
            onRefresh={refetch}
          />
          <JobDetail jobId={selectedJobId} />
        </div>
      </main>

      <style>{`
        .app-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          width: 100vw;
          overflow: hidden;
          background-color: var(--bg-base);
        }

        .main-content {
          margin-top: var(--header-height);
          display: flex;
          flex-direction: column;
          flex: 1;
          overflow: hidden;
        }

        .workspace {
          display: flex;
          flex: 1;
          overflow: hidden;
        }

        @media (max-width: 768px) {
          .workspace {
            flex-direction: column;
          }
          
          .job-list {
            width: 100%;
            height: 300px;
            border-right: none;
            border-bottom: 1px solid var(--border-subtle);
          }
        }
      `}</style>
    </div>
  );
}

export default App;
