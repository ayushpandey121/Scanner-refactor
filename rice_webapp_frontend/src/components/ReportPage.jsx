import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/ReportPage.css';
import useRiceStore from '../zustand/store';
import { getApiBaseUrl } from '../utils/axiosConfig';

const ReportPage = () => {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const backendBaseUrl = getApiBaseUrl() || 'http://localhost:5000';

  const resolveStorageUrl = (url) => {
    if (!url) return null;
    if (/^(data:|blob:|https?:)/i.test(url)) {
      return url;
    }
    if (url.startsWith('/')) {
      return `${backendBaseUrl}${url}`;
    }
    return `${backendBaseUrl}/${url}`;
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:5000/get_logs');
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching logs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRowClick = (log) => {
    if (!log.full_data) {
      console.error('No full data available for this log entry');
      return;
    }

    try {
      // Extract data from the full log data
      const fullData = log.full_data;
      const statistics = fullData.statistics || {};
      const inputImageUrl = resolveStorageUrl(
        fullData.input_image_url ||
        fullData.input_url ||
        (fullData.filename ? `/upload/${fullData.filename}` : null)
      );

      // Prepare data for the store
      const grains = fullData.grains || [];
      const storeData = {
        grains: grains,
        reportData: {
          grainCount: grains.length || statistics.total_grains || statistics.grain_count || 0,
          avgLength: statistics.avg_length || 0,
          avgWidth: statistics.avg_breadth || 0,
          brokenCount: statistics.broken_count || 0,
          chalkyCount: statistics.chalky_count || 0,
          discolorCount: statistics.discolored_count || 0,
          kettValue: statistics.kett_value || 0,
        },
        previewImage: inputImageUrl,
        croppedImageUrl: resolveStorageUrl(fullData.cropped_url) || null,
        fileName: fullData.filename || 'loaded_from_report',
        date: fullData.timestamp || new Date().toISOString(),
        parameters: {
          minlen: fullData.minlen || 5.0,
          chalky_percentage: fullData.chalky_percentage || 30.0,
        },
        analysisStatus: 'completed',
        analysisError: null,
      };

      // Load sample details from historical data if available
      if (fullData.details) {
        const sampleDetails = {
          sellerName: fullData.details.seller_name || '',
          sellerCode: fullData.details.seller_code || '',
          variety: fullData.details.variety || '',
          type: fullData.details.type || '',
          sampleName: fullData.details.sample_name || '',
          sampleSource: fullData.details.sample_source || '',
          lotSize: fullData.details.lot_size || '',
          lotUnit: fullData.details.lot_unit || '',
        };
        // Save to localStorage for PDF generation
        localStorage.setItem('sampleDetails', JSON.stringify(sampleDetails));
      }

      // Load data into store
      useRiceStore.getState().setRiceData(storeData);

      // Navigate to result page
      navigate('/results');
    } catch (error) {
      console.error('Error loading data from log:', error);
      alert('Failed to load analysis data. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="report-page">
        <div className="report-loading">
          <div className="loading-spinner"></div>
          <h3>Loading Report Data...</h3>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="report-page">
        <div className="report-error">
          <h3>Error Loading Report</h3>
          <p>{error}</p>
          <button onClick={fetchLogs} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="report-page">
      <div className="report-header">
        <button
          className="back-button"
          onClick={() => navigate('/')}
        >
          ← Back to Home
        </button>
        <h1>Rice Quality Report</h1>
        <button
          className="refresh-button"
          onClick={fetchLogs}
        >
          Refresh Data
        </button>
      </div>

      <div className="report-content">
        <div className="report-summary">
          <h2>Analysis Summary</h2>
          <div className="summary-stats">
            <div className="summary-card">
              <span className="summary-label">Total Scans</span>
              <span className="summary-value">{logs.length}</span>
            </div>
            <div className="summary-card">
              <span className="summary-label">Average Length</span>
              <span className="summary-value">
                {logs.length > 0
                  ? (logs.reduce((sum, log) => sum + log.average_length, 0) / logs.length).toFixed(2)
                  : 0} mm
              </span>
            </div>
            <div className="summary-card">
              <span className="summary-label">Average Width</span>
              <span className="summary-value">
                {logs.length > 0
                  ? (logs.reduce((sum, log) => sum + log.average_width, 0) / logs.length).toFixed(2)
                  : 0} mm
              </span>
            </div>
          </div>
        </div>

        <div className="report-table-container">
          <h2>Detailed Report</h2>
          {logs.length === 0 ? (
            <div className="no-data">
              <p>No report data available. Please run some analyses first.</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Average Length (mm)</th>
                    <th>Average Width (mm)</th>
                    <th>L/B Ratio</th>
                    <th>Broken</th>
                    <th>Chalky</th>
                    <th>Discolor</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, index) => (
                    <tr
                      key={index}
                      onClick={() => handleRowClick(log)}
                      style={{ cursor: 'pointer' }}
                      className="clickable-row"
                    >
                      <td>{log.timestamp}</td>
                      <td>{log.average_length.toFixed(2)}</td>
                      <td>{log.average_width.toFixed(2)}</td>
                      <td>{log.lb_ratio.toFixed(2)}</td>
                      <td>{log.broken}</td>
                      <td>{log.chalky}</td>
                      <td>{log.discolor}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportPage;
