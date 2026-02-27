import React, { useState, useEffect } from 'react';
import { checkHealth } from '../api';
import '../styles/header.css';

const Header = () => {
  const [isHealthy, setIsHealthy] = useState(null);

  useEffect(() => {
    const check = async () => {
      const status = await checkHealth();
      setIsHealthy(status);
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="header">
      <div className="header-left">
        <span className="logo-monogram">FDA</span>
        <span className="logo-label">FINANCIAL DOCUMENT ANALYZER</span>
      </div>
      <div className="header-right">
        <div className={`health-indicator ${isHealthy === true ? 'healthy' : isHealthy === false ? 'unhealthy' : 'checking'}`}>
          <div className="health-dot"></div>
          <span className="health-label">API STATUS: {isHealthy === true ? 'ONLINE' : isHealthy === false ? 'OFFLINE' : 'CHECKING'}</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
