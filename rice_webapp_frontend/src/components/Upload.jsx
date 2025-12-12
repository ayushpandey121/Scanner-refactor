import React, { useState, useEffect } from "react";
import "../styles/Upload.css";
import { useNavigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import useRiceStore from "../zustand/store";
import InstructionPanel from "./InstructionPanel";
import { getApiBaseUrl } from "../utils/axiosConfig";

class EpsonScanner {
  constructor(config = {}) {
    // API base to Python scanner service
    this.API_BASE = config.apiBase || 'http://127.0.0.1:8080/api/scanner';
    this.pollInterval = null;
    this.isScanning = false;
    this.onScanComplete = config.onScanComplete || this.defaultScanHandler;
    this.onError = config.onError || this.defaultErrorHandler;
    this.onStatusChange = config.onStatusChange || null;
    this.previousFileCount = 0;
  }

  async checkConnection() {
    try {
      const response = await fetch(`${this.API_BASE}/status`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        if (this.onStatusChange) {
          this.onStatusChange('connected', data);
        }
        return { success: true, data };
      } else {
        throw new Error('Server not responding');
      }
    } catch (error) {
      if (this.onStatusChange) {
        this.onStatusChange('disconnected', null);
      }
      return { success: false, error: error.message };
    }
  }

  async startScan(settings = {}) {
    if (this.isScanning) {
      return { success: false, error: 'Scan already in progress' };
    }

    const connectionCheck = await this.checkConnection();
    if (!connectionCheck.success) {
      this.onError('Cannot connect to scanner service. Please ensure scanner_service.py is running.');
      return { success: false, error: 'Backend server not available' };
    }

    this.isScanning = true;

    try {
      // Get current file count before scanning
      const filesResponse = await fetch(`${this.API_BASE}/files`);
      if (filesResponse.ok) {
        const filesData = await filesResponse.json();
        this.previousFileCount = filesData.files ? filesData.files.length : 0;
      }

      // Settings are HARDCODED in scanner_service.py - don't send any
      const scanSettings = {}; // Empty - backend will use hardcoded values

      if (this.onStatusChange) {
        this.onStatusChange('scanning', { message: 'Starting automated scan...' });
      }

      const response = await fetch(`${this.API_BASE}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scanSettings)
      });

      if (response.ok) {
        const data = await response.json();

        if (data.success) {
          console.log('✅ Scan completed:', data.file.filename);

          // Directly process the completed scan
          await this.processScannedFile(data.file);

          this.stopScanning();

          return {
            success: true,
            message: 'Scan completed successfully '
          };
        } else {
          throw new Error(data.error || 'Scan failed');
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Scan request failed');
      }
    } catch (error) {
      this.isScanning = false;
      this.onError(`Failed to scan: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  async processScannedFile(file) {
    try {
      // Use absolute URL with full Python backend address
      const imageUrl = `http://127.0.0.1:8080/api/scanner/file/${file.filename}`;

      const response = await fetch(imageUrl);

      if (response.ok) {
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);

        this.onScanComplete({
          filename: file.filename,
          url: objectUrl,
          blob: blob,
          size: file.size || blob.size,
          timestamp: new Date(),
          settings: file.settings
        });
      } else {
        console.error('Failed to fetch image, status:', response.status);
        this.onError('Failed to load scanned image from server');
      }
    } catch (error) {
      console.error('Error processing scanned file:', error);
      this.onError(`Error loading scanned image: ${error.message}`);
    }
  }

  stopScanning() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.isScanning = false;

    if (this.onStatusChange) {
      this.onStatusChange('idle', null);
    }
  }

  async cancelScan() {
    this.stopScanning();
    return { success: true };
  }

  defaultScanHandler(imageData) {
    // console.log('Scan completed:', imageData);
  }

  defaultErrorHandler(error) {
    console.error('Scanner error:', error);
  }
}

const Upload = () => {
  const [preview, setPreview] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scannerReady, setScannerReady] = useState(false);
  const [initError, setInitError] = useState(null);
  const [scannerInstance, setScannerInstance] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [riceVariety, setRiceVariety] = useState('sella');
  const [buttonMode, setButtonMode] = useState('scan'); // 'scan', 'cancel', 'analyze'
  const [varieties, setVarieties] = useState([]);
  const [selectedVariety, setSelectedVariety] = useState('');
  const [selectedSubVariety, setSelectedSubVariety] = useState('');
  const [chalkyPercentage, setChalkyPercentage] = useState(30);

  const setRiceData = useRiceStore((state) => state.setRiceData);

  // Update button mode based on state changes
  useEffect(() => {
    if (loading) {
      // Loading is handled in render
    } else if (scanning) {
      setButtonMode('cancel');
    } else if (selectedFile) {
      setButtonMode('analyze');
    } else {
      setButtonMode('scan');
    }
  }, [selectedFile, scanning, loading]);

  // Load varieties data
  useEffect(() => {
    const loadVarieties = async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/varieties`);
        if (response.ok) {
          const data = await response.json();
          setVarieties(data.varieties || []);
        } else {
          console.error('Failed to load varieties');
        }
      } catch (error) {
        console.error('Error loading varieties:', error);
      }
    };
    loadVarieties();
  }, []);

  // Initialize EPSON Scanner
  useEffect(() => {
    console.log("=== Initializing Scanner ===");

    const scanner = new EpsonScanner({
      apiBase: 'http://localhost:8080/api/scanner',

      onScanComplete: (imageData) => {
        setStatusMessage(`✅ Scan completed: ${imageData.filename}`);
        setPreview(imageData.url);

        // Convert blob to File object
        const file = new File([imageData.blob], imageData.filename, {
          type: imageData.blob.type,
        });
        setSelectedFile(file);
        setScanning(false);
        setButtonMode('analyze'); // Switch to analyze mode after scan completes
      },

      onError: (error) => {
        console.error('Scanner error:', error);
        setInitError(error);
        setScanning(false);
        setStatusMessage('❌ Error: ' + error);
        alert('Scanner Error: ' + error);
      },

      onStatusChange: (status, data) => {
        if (status === 'connected') {
          setScannerReady(true);
          setInitError(null);
          setStatusMessage('✅ Scanner ready (Automated Mode - Fixed Settings: 400 DPI, Color, JPEG 85%)');
          // Don't override button mode if file is already selected
          if (!selectedFile) {
            setButtonMode('scan');
          }
        } else if (status === 'disconnected') {
          setScannerReady(false);
          setInitError('Scanner service not connected');
          setStatusMessage('❌ Disconnected');
          // Don't override button mode if file is already selected
          if (!selectedFile) {
            setButtonMode('scan');
          }
        } else if (status === 'scanning') {
          setScanning(true);
          setStatusMessage('⏳ Scanning... ');
          setButtonMode('cancel');
        } else if (status === 'idle') {
          setScanning(false);
          setStatusMessage('Ready');
          // Don't override button mode here - let useEffect handle it
        }
      }
    });

    setScannerInstance(scanner);

    // Check connection on mount
    scanner.checkConnection().then(result => {
      if (result.success) {
        setStatusMessage('✅ Scanner service connected');
      }
    });

    // Cleanup on unmount
    return () => {
      if (scanner) {
        scanner.stopScanning();
      }
    };
  }, []);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
        setSelectedFile(file);
        setStatusMessage(`✅ File selected: ${file.name}`);
        setButtonMode('analyze'); // Switch to analyze mode when file is selected
      };
      reader.readAsDataURL(file);
    } else {
      alert("Please select a valid image file (JPG, JPEG, or PNG)");
      setPreview(null);
      setSelectedFile(null);
      setButtonMode('scan'); // Reset to scan mode if invalid file
    }
  };

  const startScanning = async () => {
    console.log('=== Start Scanning ===');

    if (!scannerInstance) {
      alert("Scanner not initialized. Please refresh the page.");
      return;
    }

    if (!scannerReady) {
      alert("Scanner service is not running.\n\nPlease start it by running:\npython scanner_service.py");
      return;
    }

    setScanning(true);
    setStatusMessage('⏳ Starting automated scan...');

    const result = await scannerInstance.startScan();

    if (result.success) {
      console.log('✅ Scan completed');
    } else {
      console.error('❌ Failed to scan:', result.error);
      setScanning(false);
      setStatusMessage('❌ Failed to scan');
    }
  };

  const cancelScanning = async () => {
    if (scannerInstance) {
      await scannerInstance.cancelScan();
      setScanning(false);
      setStatusMessage('Scan cancelled');
      alert('Scan cancelled');
    }
  };

  const handleVarietyChange = (e) => {
    const varietyName = e.target.value;
    setSelectedVariety(varietyName);
    setSelectedSubVariety('');
  };

  const handleSubVarietyChange = (e) => {
    const subVarietyName = e.target.value;
    setSelectedSubVariety(subVarietyName);
  };

  const uploadToAPI = async () => {
    if (!selectedFile) {
      alert("Please scan an image first.");
      return;
    }

    setLoading(true);
    setStatusMessage('⏳ Analyzing image...');

    // Get the selected variety and subvariety data
    const selectedVarietyData = varieties.find(v => v.name === selectedVariety);
    const selectedSubVarietyData = selectedVarietyData?.subVarieties.find(s => s.name === selectedSubVariety);

    // Use default parameters since we're not selecting quality anymore
    const parameters = { minlen: 5.0, chalky_percentage: chalkyPercentage };

    // *** RETRIEVE CORRECTION VALUES FROM LOCALSTORAGE ***
    const lengthCorrection = parseFloat(localStorage.getItem('length_correction') || '0');
    const wiCorrection = parseFloat(localStorage.getItem('wi_correction') || '0');
    const wwCorrection = parseFloat(localStorage.getItem('ww_correction') || '1');

    console.log('📊 Applying corrections:', { 
      lengthCorrection, 
      wiCorrection, 
      wwCorrection 
    });

    // Set analysis status to loading and navigate to details page immediately
    setRiceData({
      previewImage: preview,
      fileName: selectedFile.name,
      selectedFile: selectedFile,
      analysisStatus: 'loading',
      parameters,
      selectedVariety: selectedVariety || null,
      selectedSubVariety: selectedSubVariety || null,
      selectedVarietyData: selectedVarietyData || null,
      selectedSubVarietyData: selectedSubVarietyData || null,
    });

    navigate("/details");

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("rice_variety", riceVariety);
    
    // *** ADD CORRECTION VALUES TO FORMDATA ***
    formData.append("length_correction", lengthCorrection);
    formData.append("wi_correction", wiCorrection);
    formData.append("ww_correction", wwCorrection);

    try {
      const res = await fetch(`${getApiBaseUrl()}/predict`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Server responded with status " + res.status);
      }

      const result = await res.json();

      // Store scan result
      await fetch(`${getApiBaseUrl()}/store_scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });

      const stats = result?.result?.statistics;
      const grains = result?.result?.grain;

      if (!stats || !grains) {
        throw new Error("Invalid API response format.");
      }

      // Compute class statistics from grains
      const class_counts = {};
      grains.forEach((grain) => {
        const category = grain.category || "Unknown";
        class_counts[category] = (class_counts[category] || 0) + 1;
      });

      const all_class = Object.entries(class_counts).map(([variety, count]) => {
        const percentage = (count / grains.length) * 100;
        return {
          count,
          variety,
          percentage: Math.round(percentage * 100) / 100
        };
      });

      const majorityClass = Object.keys(class_counts).reduce(
        (a, b) => (class_counts[a] > class_counts[b] ? a : b),
        "Unknown"
      );

      const mixture = Object.keys(class_counts).length > 1;

      // *** USE VALUES DIRECTLY (ALREADY CORRECTED IN BACKEND) ***
      const report = {
        avgLength: stats.avg_length,
        avgWidth: stats.avg_breadth || stats.average_width,
        majorityClass: majorityClass,
        mixture: mixture,
        grainCount: stats.total_grains || stats.no_of_grains,
        brokenCount: stats.broken_count,
        chalkyCount: stats.chalky_count,
        discolorCount: stats.discolored_count || stats.discolor_count,
        kettValue: stats.kett_value,
      };

      console.log('✅ Analysis completed:', {
        avgLength: stats.avg_length,
        kettValue: stats.kett_value
      });

      const date = new Date();
      const chartData = all_class
        .map((item) => ({
          count: item.count,
          name: item.variety,
          percentage: item.percentage,
        }))
        .sort((a, b) => b.count - a.count);

      // Update store with completed analysis data
      setRiceData({
        grains: result.result.grain,
        reportData: report,
        chartData: chartData,
        previewImage: preview,
        croppedImageUrl: result.cropped_url || result.local_cropped_url || null,
        fileName: selectedFile.name,
        date: date.toDateString(),
        selectedFile: selectedFile,
        parameters: parameters,
        analysisStatus: 'completed',
        analysisError: null,
        selectedVariety: selectedVariety || null,
        selectedSubVariety: selectedSubVariety || null,
        selectedVarietyData: selectedVarietyData || null,
        selectedSubVarietyData: selectedSubVarietyData || null,
      });

      setStatusMessage('✅ Analysis completed');
    } catch (err) {
      console.error("Upload failed:", err);
      setRiceData({
        analysisStatus: 'error',
        analysisError: err.message,
      });
      setStatusMessage('❌ Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-wrapper">
      <div className="main-upload-area">
        <div className="upload-header">
          <h2 className="upload-title">Scan Rice Grains </h2>

          {/* Status Message */}
          {statusMessage && (
            <div style={{
              background: statusMessage.includes('✅') ? '#d4edda' : statusMessage.includes('❌') ? '#f8d7da' : '#d1ecf1',
              border: `1px solid ${statusMessage.includes('✅') ? '#c3e6cb' : statusMessage.includes('❌') ? '#f5c6cb' : '#bee5eb'}`,
              color: statusMessage.includes('✅') ? '#155724' : statusMessage.includes('❌') ? '#721c24' : '#0c5460',
              padding: '10px',
              marginTop: '10px',
              borderRadius: '4px',
              fontSize: '14px',
              fontWeight: '500'
            }}>
              {statusMessage}
            </div>
          )}

          {initError && !scannerReady && (
            <div style={{
              background: '#fee',
              border: '1px solid #c00',
              padding: '10px',
              marginTop: '10px',
              borderRadius: '4px',
              fontSize: '14px'
            }}>
              <strong>Scanner Error:</strong>
              <div style={{ marginTop: '5px' }}>{initError}</div>
              <div style={{ marginTop: '10px', fontSize: '12px' }}>
                <strong>To fix:</strong>
                <ol style={{ marginLeft: '20px', marginTop: '5px' }}>
                  <li>Ensure scanner is connected </li>
                  <li>Ensure scanner is powered on</li>
                  <li>Refresh this page</li>
                </ol>
              </div>
            </div>
          )}
        </div>

        <div className="upload-instructions">
          <div className="scanner-section">
            <div className="scanner-preview">
              {preview ? (
                <img src={preview} alt="Preview" className="preview-image" />
              ) : (
                <div className="placeholder">
                  <p>📄 No image scanned yet</p>
                  <small>Click "Scan" </small>
                </div>
              )}
            </div>

            <div className="scanner-controls">
              {/* <label htmlFor="file-upload" style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                Or upload an existing image:
              </label>

              <input
                type="file"
                id="file-upload"
                accept=".jpg, .jpeg, .png"
                onChange={handleFileChange}
                style={{ display: 'block', marginBottom: '15px' }}
              /> */}
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap' }}>
                <label htmlFor="rice-type" style={{ marginRight: '10px', fontWeight: '500' }}>
                  Rice Type:
                </label>
                <select
                  id="rice-type"
                  value={riceVariety}
                  onChange={(e) => setRiceVariety(e.target.value)}
                  style={{
                    padding: '5px 10px',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    fontSize: '14px',
                    minWidth: '100px'
                  }}
                >
                  <option value="sella">Sella</option>
                  <option value="non_sella">Non Sella</option>
                </select>
                <label htmlFor="chalky-percentage" style={{ marginLeft: '20px', marginRight: '10px', fontWeight: '500' }}>
                  Chalky Percentage:
                </label>
                <input
                  type="range"
                  id="chalky-percentage"
                  min="0"
                  max="100"
                  step="1"
                  value={chalkyPercentage}
                  onChange={(e) => setChalkyPercentage(Number(e.target.value))}
                  style={{
                    marginRight: '10px',
                    width: '120px'
                  }}
                />
                <span style={{ fontSize: '14px', fontWeight: '500' }}>{chalkyPercentage}%</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px' }}>
                <label htmlFor="variety" style={{ marginRight: '10px', fontWeight: '500' }}>
                  Variety:
                </label>
                <select
                  id="variety"
                  value={selectedVariety}
                  onChange={handleVarietyChange}
                  style={{
                    padding: '5px 10px',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    fontSize: '14px',
                    minWidth: '100px'
                  }}
                >
                  <option value="">Select Variety</option>
                  {varieties.map((variety) => (
                    <option key={variety.name} value={variety.name}>
                      {variety.name}
                    </option>
                  ))}
                </select>
              </div>
              {selectedVariety && (
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px' }}>
                  <label htmlFor="sub-variety" style={{ marginRight: '10px', fontWeight: '500' }}>
                    Sub-Variety:
                  </label>
                  <select
                    id="sub-variety"
                    value={selectedSubVariety}
                    onChange={handleSubVarietyChange}
                    style={{
                      padding: '5px 10px',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                      fontSize: '14px',
                      minWidth: '100px'
                    }}
                  >
                    <option value="">Select Sub-Variety</option>
                    {varieties.find(v => v.name === selectedVariety)?.subVarieties.map((subVariety) => (
                      <option key={subVariety.name} value={subVariety.name}>
                        {subVariety.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {loading ? (
                <div className="loader-container">
                  <div className="loader-text">
                    <span>Analyzing rice grains</span>
                    <span className="dots">
                      <span>.</span>
                      <span>.</span>
                      <span>.</span>
                    </span>
                  </div>
                  <div className="loader-spinner"></div>
                </div>
              ) : buttonMode === 'scan' ? (
                <button
                  className="btn-scan"
                  onClick={startScanning}
                  disabled={scanning || !scannerReady}
                  title={!scannerReady ? "Scanner service not connected" : "Start scan"}
                  style={{ width: '100%' }}
                >
                  {scanning ? "⏳ Scanning..." : "📄 Scan Rice Grains"}
                </button>
              ) : buttonMode === 'cancel' ? (
                <button
                  className="btn-scan"
                  onClick={cancelScanning}
                  style={{ background: '#dc3545', width: '100%' }}
                >
                  ✕ Cancel Scan
                </button>
              ) : buttonMode === 'analyze' ? (
                <button
                  className="btn-scan"
                  onClick={uploadToAPI}
                  disabled={!selectedFile}
                  title={!selectedFile ? "Please select or scan an image first" : "Start analysis"}
                  style={{ width: '100%' }}
                >
                  🔬 Start Analysis
                </button>
              ) : null}
            </div>
          </div>

          {/* Instructions Panel */}
          <InstructionPanel />
        </div>
      </div>
    </div>
  );
};

export default Upload;