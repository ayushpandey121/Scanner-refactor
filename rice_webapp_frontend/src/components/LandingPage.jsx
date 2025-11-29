import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();

  const handleNewScan = () => {
    navigate('/upload');
  };

  const handleReports = () => {
    navigate('/report');
  };

  return (
    <div className="landing-container">
      <div className="landing-header">
        <h1 className="landing-title">Agsure Scanner App</h1>
        <p className="landing-subtitle">
          Advanced AI-powered rice grain analysis for quality assessment and agricultural insights
        </p>
      </div>

      <div className="landing-content">
        <div className="feature-cards">
          <div className="feature-card" onClick={handleNewScan}>
            <div className="card-icon">
              <span className="icon-scan">📷</span>
            </div>
            <h3>New Scan</h3>
            <p>
              Upload or scan rice grain images for comprehensive quality analysis.
              Get detailed reports on grain characteristics, defects, and quality metrics.
            </p>
            <button className="card-button">Start Scanning</button>
          </div>

          <div className="feature-card" onClick={handleReports}>
            <div className="card-icon">
              <span className="icon-reports">📊</span>
            </div>
            <h3>Reports & History</h3>
            <p>
              View historical analysis reports, track quality trends, and access
              detailed grain data from previous scans and assessments.
            </p>
            <button className="card-button">View Reports</button>
          </div>
        </div>

        
      </div>
    </div>
  );
};

export default LandingPage;
