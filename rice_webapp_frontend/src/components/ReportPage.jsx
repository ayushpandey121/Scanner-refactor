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

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const recordsPerPage = 10;

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

  const fetchSellerCodeFromBackend = async (filename) => {
    try {
      if (!filename) return null;
      
      const baseName = filename.replace(/\.[^/.]+$/, '');
      const logFile = `${baseName}.json`;
      
      const response = await fetch(`${backendBaseUrl}/logs/${encodeURIComponent(logFile)}/details`);
      if (response.ok) {
        const details = await response.json();
        return details.seller_code || null;
      }
    } catch (err) {
      console.warn(`Could not fetch seller code for ${filename}:`, err);
    }
    return null;
  };

  const fetchSampleDetailsFromBackend = async (filename) => {
    try {
      if (!filename) return null;
      
      const baseName = filename.replace(/\.[^/.]+$/, '');
      const logFile = `${baseName}.json`;
      
      const response = await fetch(`${backendBaseUrl}/logs/${encodeURIComponent(logFile)}/details`);
      if (response.ok) {
        const details = await response.json();
        return {
          seller_name: details.seller_name || '',
          seller_code: details.seller_code || '',
          sample_name: details.sample_name || '',
          sample_source: details.sample_source || '',
          lot_size: details.lot_size || '',
          lot_unit: details.lot_unit || '',
          variety: details.variety || '',
          sub_variety: details.sub_variety || '',
        };
      }
    } catch (err) {
      console.warn(`Could not fetch sample details for ${filename}:`, err);
    }
    return null;
  };

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${backendBaseUrl}/get_logs`);
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      const data = await response.json();
      const logsData = data.logs || [];
      
      const logsWithSellerCodes = [];
      for (const log of logsData) {
        let sellerCode = null;
        
        if (log.full_data?.details?.seller_code && 
            typeof log.full_data.details.seller_code === 'string' && 
            log.full_data.details.seller_code.trim()) {
          sellerCode = log.full_data.details.seller_code.trim();
        } else if (log.seller_code && typeof log.seller_code === 'string' && log.seller_code.trim()) {
          sellerCode = log.seller_code.trim();
        } else if (log.full_data?.filename) {
          sellerCode = await fetchSellerCodeFromBackend(log.full_data.filename);
        }

        let backendDetails = null;
        if (log.full_data?.filename) {
          backendDetails = await fetchSampleDetailsFromBackend(log.full_data.filename);
        }
        
        logsWithSellerCodes.push({
          ...log,
          fetchedSellerCode: sellerCode,
          backendDetails: backendDetails
        });
      }
      
      setLogs(logsWithSellerCodes);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching logs:', err);
    } finally {
      setLoading(false);
    }
  };

  // Filter logs based on search query (searches across ALL pages)
  const filteredLogs = logs.filter(log => {
    if (!searchQuery.trim()) return true;

    const query = searchQuery.toLowerCase().trim();
    const sellerCode = (log.fetchedSellerCode || '').toLowerCase();
    const avgLength = log.average_length.toFixed(2);
    const avgWidth = log.average_width.toFixed(2);

    // Check if query matches seller code, average length, or average width
    return (
      sellerCode.includes(query) ||
      avgLength.includes(query) ||
      avgWidth.includes(query)
    );
  });

  // Calculate pagination
  const totalPages = Math.ceil(filteredLogs.length / recordsPerPage);
  const indexOfLastRecord = currentPage * recordsPerPage;
  const indexOfFirstRecord = indexOfLastRecord - recordsPerPage;
  const currentRecords = filteredLogs.slice(indexOfFirstRecord, indexOfLastRecord);

  // Reset to page 1 when search query changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
  };

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  // Generate page numbers to display
  const getPageNumbers = () => {
    const pageNumbers = [];
    const maxPagesToShow = 5;
    
    if (totalPages <= maxPagesToShow) {
      for (let i = 1; i <= totalPages; i++) {
        pageNumbers.push(i);
      }
    } else {
      if (currentPage <= 3) {
        for (let i = 1; i <= 4; i++) {
          pageNumbers.push(i);
        }
        pageNumbers.push('...');
        pageNumbers.push(totalPages);
      } else if (currentPage >= totalPages - 2) {
        pageNumbers.push(1);
        pageNumbers.push('...');
        for (let i = totalPages - 3; i <= totalPages; i++) {
          pageNumbers.push(i);
        }
      } else {
        pageNumbers.push(1);
        pageNumbers.push('...');
        pageNumbers.push(currentPage - 1);
        pageNumbers.push(currentPage);
        pageNumbers.push(currentPage + 1);
        pageNumbers.push('...');
        pageNumbers.push(totalPages);
      }
    }
    
    return pageNumbers;
  };

  const handleRowClick = async (log) => {
    if (!log.full_data) {
      console.error('No full data available for this log entry');
      return;
    }

    try {
      const fullData = log.full_data;
      const statistics = fullData.statistics || {};
      const inputImageUrl = resolveStorageUrl(
        fullData.input_image_url ||
        fullData.input_url ||
        (fullData.filename ? `/upload/${fullData.filename}` : null)
      );

      let sampleDetails = null;
      let savedVariety = null;
      let savedSubVariety = null;
      
      if (log.backendDetails) {
        sampleDetails = {
          sellerName: log.backendDetails.seller_name || '',
          sellerCode: log.backendDetails.seller_code || '',
          sampleName: log.backendDetails.sample_name || '',
          sampleSource: log.backendDetails.sample_source || '',
          lotSize: log.backendDetails.lot_size || '',
          lotUnit: log.backendDetails.lot_unit || '',
        };
        savedVariety = log.backendDetails.variety || null;
        savedSubVariety = log.backendDetails.sub_variety || null;
      } else if (fullData.details) {
        sampleDetails = {
          sellerName: fullData.details.seller_name || '',
          sellerCode: fullData.details.seller_code || '',
          sampleName: fullData.details.sample_name || '',
          sampleSource: fullData.details.sample_source || '',
          lotSize: fullData.details.lot_size || '',
          lotUnit: fullData.details.lot_unit || '',
        };
      } else if (fullData.seller_code) {
        sampleDetails = {
          sellerName: fullData.seller_name || '',
          sellerCode: fullData.seller_code || '',
          sampleName: fullData.sample_name || '',
          sampleSource: fullData.sample_source || '',
          lotSize: fullData.lot_size || '',
          lotUnit: fullData.lot_unit || '',
        };
      }

      if (sampleDetails) {
        localStorage.setItem('sampleDetails', JSON.stringify(sampleDetails));
      }

      let selectedVarietyData = null;
      let selectedSubVarietyData = null;
      
      if (savedVariety || savedSubVariety) {
        try {
          const varietiesResponse = await fetch(`${backendBaseUrl}/varieties`);
          if (varietiesResponse.ok) {
            const varietiesData = await varietiesResponse.json();
            const varieties = varietiesData.varieties || [];
            
            if (savedVariety) {
              selectedVarietyData = varieties.find(v => v.name === savedVariety);
              
              if (selectedVarietyData && savedSubVariety) {
                selectedSubVarietyData = selectedVarietyData.subVarieties?.find(
                  s => s.name === savedSubVariety
                );
              }
            }
          }
        } catch (err) {
          console.warn('Failed to fetch varieties data:', err);
        }
      }

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
        sampleDetails: sampleDetails,
        selectedVariety: savedVariety,
        selectedSubVariety: savedSubVariety,
        selectedVarietyData: selectedVarietyData,
        selectedSubVarietyData: selectedSubVarietyData,
      };

      useRiceStore.getState().setRiceData(storeData);
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
        <h2>Rice Quality Report</h2>
        <button
          className="refresh-button"
          onClick={fetchLogs}
        >
          Refresh Data
        </button>
      </div>

      <div className="report-content">
        <div className="report-table-container">
          <div className="report-table-header">
            <h2>Detailed Report</h2>
            <div className="search-bar-wrapper">
              <input
                type="text"
                placeholder="Search by seller code, length, or width..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-bar"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')} 
                  className="clear-search-button"
                  title="Clear search"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {logs.length === 0 ? (
            <div className="no-data">
              <p>No report data available. Please run some analyses first.</p>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="no-data">
              <p>No records match your search criteria.</p>
            </div>
          ) : (
            <>
              <div className="table-wrapper">
                <table className="report-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Seller Code</th>
                      <th>Average Length (mm)</th>
                      <th>Average Width (mm)</th>
                      <th>L/B Ratio</th>
                      <th>Broken</th>
                      <th>Chalky</th>
                      <th>Discolor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentRecords.map((log, index) => {
                      const sellerCode = log.fetchedSellerCode || '-';
                      
                      return (
                        <tr
                          key={index}
                          onClick={() => handleRowClick(log)}
                          style={{ cursor: 'pointer' }}
                          className="clickable-row"
                        >
                          <td>{log.timestamp}</td>
                          <td>{sellerCode}</td>
                          <td>{log.average_length.toFixed(2)}</td>
                          <td>{log.average_width.toFixed(2)}</td>
                          <td>{log.lb_ratio.toFixed(2)}</td>
                          <td>{log.broken}</td>
                          <td>{log.chalky}</td>
                          <td>{log.discolor}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="pagination-container">
                  <button
                    onClick={handlePreviousPage}
                    disabled={currentPage === 1}
                    className="pagination-button"
                  >
                    Previous
                  </button>

                  <div className="pagination-numbers">
                    {getPageNumbers().map((pageNum, index) => (
                      pageNum === '...' ? (
                        <span key={`ellipsis-${index}`} className="pagination-ellipsis">
                          ...
                        </span>
                      ) : (
                        <button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          className={`pagination-number ${currentPage === pageNum ? 'active' : ''}`}
                        >
                          {pageNum}
                        </button>
                      )
                    ))}
                  </div>

                  <button
                    onClick={handleNextPage}
                    disabled={currentPage === totalPages}
                    className="pagination-button"
                  >
                    Next
                  </button>
                </div>
              )}

              <div className="results-summary">
                Showing {indexOfFirstRecord + 1}-{Math.min(indexOfLastRecord, filteredLogs.length)} of {filteredLogs.length} records
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportPage;