import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useRiceStore from '../zustand/store';
import { getApiBaseUrl } from '../utils/axiosConfig';
import '../styles/Details.css';

const Details = () => {
    const navigate = useNavigate();
    const analysisStatus = useRiceStore((state) => state.analysisStatus);
    const analysisError = useRiceStore((state) => state.analysisError);
    const reportData = useRiceStore((state) => state.reportData);
    const fileName = useRiceStore((state) => state.fileName);
    const selectedFile = useRiceStore((state) => state.selectedFile);
    const selectedVariety = useRiceStore((state) => state.selectedVariety);
    const selectedSubVariety = useRiceStore((state) => state.selectedSubVariety);

    const [formData, setFormData] = useState({
        sellerName: '',
        sellerCode: '',
        sampleName: '',
        sampleSource: '',
        lotSize: '',
        lotUnit: ''
    });
    const [savingDetails, setSavingDetails] = useState(false);
    const [saveError, setSaveError] = useState(null);
    const [saveSuccess, setSaveSuccess] = useState(false);
    const [isFormStarted, setIsFormStarted] = useState(false);

    useEffect(() => {
        const fetchDetails = async () => {
            const logFile = getLogFileName();
            if (!logFile) {
                setFormData({
                    sellerName: '',
                    sellerCode: '',
                    sampleName: '',
                    sampleSource: '',
                    lotSize: '',
                    lotUnit: ''
                });
                return;
            }

            try {
                const baseUrl = getApiBaseUrl();
                const resolvedBase = baseUrl && baseUrl.trim().length > 0 ? baseUrl : 'http://localhost:5000';
                const endpoint = `${resolvedBase.replace(/\/$/, '')}/logs/${encodeURIComponent(logFile)}/details`;

                const response = await fetch(endpoint);
                if (response.ok) {
                    const details = await response.json();
                    const transformedDetails = {
                        sellerName: details.seller_name || '',
                        sellerCode: details.seller_code || '',
                        sampleName: details.sample_name || '',
                        sampleSource: details.sample_source || '',
                        lotSize: details.lot_size || '',
                        lotUnit: details.lot_unit || ''
                    };
                    setFormData((prev) => ({ ...prev, ...transformedDetails }));
                } else if (response.status === 404) {
                    console.log('Log file not found, showing blank form for new sample');
                    setFormData({
                        sellerName: '',
                        sellerCode: '',
                        sampleName: '',
                        sampleSource: '',
                        lotSize: '',
                        lotUnit: ''
                    });
                } else {
                    console.warn('Failed to fetch details from backend:', response.status);
                }
            } catch (err) {
                console.warn('Failed to fetch details from backend:', err);
            }
        };

        fetchDetails();
    }, []);

    const getLogFileName = () => {
        const currentName = fileName || selectedFile?.name;
        if (!currentName) return null;
        const baseName = currentName.replace(/\.[^/.]+$/, '');
        return `${baseName}.json`;
    };

    const saveDetailsToBackend = async (details, attempt = 0) => {
        const logFile = getLogFileName();
        console.log('[saveDetailsToBackend] Log file:', logFile);
        
        if (!logFile) {
            console.warn('No associated log file detected; skipping backend details save.');
            setSaveError('No log file associated. Please upload an image first.');
            return false;
        }

        setSavingDetails(true);
        setSaveError(null);
        setSaveSuccess(false);
        
        try {
            const baseUrl = getApiBaseUrl();
            const resolvedBase = baseUrl && baseUrl.trim().length > 0 ? baseUrl : 'http://localhost:5000';
            const endpoint = `${resolvedBase.replace(/\/$/, '')}/logs/${encodeURIComponent(logFile)}/details`;
            
            console.log('[saveDetailsToBackend] Endpoint:', endpoint);
            console.log('[saveDetailsToBackend] Sending data:', details);

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    seller_name: details.sellerName,
                    seller_code: details.sellerCode,
                    sample_name: details.sampleName,
                    sample_source: details.sampleSource,
                    lot_size: details.lotSize,
                    lot_unit: details.lotUnit,
                    variety: selectedVariety || '',
                    sub_variety: selectedSubVariety || '',
                    timestamp: new Date().toISOString()
                }),
            });

            console.log('[saveDetailsToBackend] Response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[saveDetailsToBackend] Error response:', errorText);
                
                if (response.status === 404 && attempt < 3) {
                    console.log(`[saveDetailsToBackend] Retrying... Attempt ${attempt + 1}/3`);
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    return saveDetailsToBackend(details, attempt + 1);
                }
                throw new Error(`Failed to save details (${response.status}): ${errorText}`);
            }
            
            const result = await response.json();
            console.log('[saveDetailsToBackend] Success response:', result);
            setSaveSuccess(true);
            setSaveError(null);
            
            // Clear success message after 3 seconds
            setTimeout(() => setSaveSuccess(false), 3000);
            
            return true;
        } catch (err) {
            console.error('[saveDetailsToBackend] Exception:', err);
            setSaveError(`Unable to save: ${err.message}`);
            return false;
        } finally {
            setSavingDetails(false);
        }
    };

    const handleChange = (e) => {
        if (!isFormStarted) {
            setIsFormStarted(true);
        }
        setFormData({ ...formData, [e.target.name]: e.target.value });
        // Clear any previous errors when user starts typing
        setSaveError(null);
        setSaveSuccess(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('Form Data:', formData);

        // Save details to backend (stored in static folder as JSON)
        const saved = await saveDetailsToBackend(formData);

        // Update Zustand store with sample details
        useRiceStore.setState({ sampleDetails: formData });

        // Only navigate if save was successful or if user wants to proceed anyway
        if (saved || window.confirm('Failed to save to backend. Do you want to continue anyway?')) {
            if (analysisStatus === 'completed' && reportData) {
                navigate('/results');
            } else if (analysisStatus === 'error') {
                alert('Analysis failed: ' + (analysisError || 'Unknown error') + '\nYou can still view the form data.');
                navigate('/results');
            } else {
                navigate('/results');
            }
        }
    };

    return (
        <div className="form-wrapper">
            <div className="form-container">
                {/* Analysis Status Indicator */}
                {analysisStatus && analysisStatus !== 'completed' && (
                    <div className={`analysis-status ${analysisStatus}`}>
                        {analysisStatus === 'loading' && (
                            <div className="status-content">
                                <div className="spinner"></div>
                                <span>Analysis in progress... Please fill in the details while we process your image.</span>
                            </div>
                        )}

                        {analysisStatus === 'error' && (
                            <div className="status-content">
                                <span className="status-icon">❌</span>
                                <span>Analysis failed: {analysisError || 'Unknown error'}</span>
                            </div>
                        )}
                    </div>
                )}
                
                {/* Save Success Message */}
                {saveSuccess && (
                    <div className="status-content success" style={{ marginBottom: '16px', color: '#10b981' }}>
                        <span>✓ Details saved successfully to backend!</span>
                    </div>
                )}
                
                {/* Save Error Message */}
                {saveError && (
                    <div className="status-content error" style={{ marginBottom: '16px' }}>
                        <span>⚠️ {saveError}</span>
                    </div>
                )}
                
                <form className="form" onSubmit={handleSubmit}>
                    <div className="form-row">
                        <label htmlFor="sellerName">Seller Name</label>
                        <input
                            type="text"
                            id="sellerName"
                            name="sellerName"
                            value={formData.sellerName}
                            onChange={handleChange}
                        />
                    </div>
                    <div className="form-row">
                        <label htmlFor="sellerCode">Seller Code <span className="required">*</span></label>
                        <input
                            type="text"
                            id="sellerCode"
                            name="sellerCode"
                            value={formData.sellerCode}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-row">
                        <label htmlFor="sampleName">Sample Name</label>
                        <input
                            type="text"
                            id="sampleName"
                            name="sampleName"
                            value={formData.sampleName}
                            onChange={handleChange}
                        />
                    </div>
                    <div className="form-row">
                        <label htmlFor="sampleSource">Sample Source</label>
                        <input
                            type="text"
                            id="sampleSource"
                            name="sampleSource"
                            value={formData.sampleSource}
                            onChange={handleChange}
                        />
                    </div>
                    <div className="form-row">
                        <label htmlFor="lotSize">Lot Size</label>
                        <input
                            type="text"
                            id="lotSize"
                            name="lotSize"
                            value={formData.lotSize}
                            onChange={handleChange}
                        />
                    </div>
                    <div className="form-row">
                        <label htmlFor="lotUnit">Lot Size Unit</label>
                        <select
                            id="lotUnit"
                            name="lotUnit"
                            value={formData.lotUnit}
                            onChange={handleChange}
                        >
                            <option value="">Select Unit</option>
                            <option value="Kg">Kg</option>
                            <option value="Quintal">Quintal</option>
                            <option value="Ton">Ton</option>
                        </select>
                    </div>
                    
                    {/* Display selected variety (read-only) */}
                    {(selectedVariety || selectedSubVariety) && (
                        <>
                            <div className="form-row">
                                <label>Selected Variety</label>
                                <input
                                    type="text"
                                    value={selectedVariety || 'Not selected'}
                                    disabled
                                    style={{ background: '#f5f5f5', cursor: 'not-allowed' }}
                                />
                            </div>
                            {selectedSubVariety && (
                                <div className="form-row">
                                    <label>Selected Sub-Variety</label>
                                    <input
                                        type="text"
                                        value={selectedSubVariety}
                                        disabled
                                        style={{ background: '#f5f5f5', cursor: 'not-allowed' }}
                                    />
                                </div>
                            )}
                        </>
                    )}
                    
                    {isFormStarted && (
                        <div className="form-row">
                            <button 
                                type="submit" 
                                className="submit-button"
                                disabled={savingDetails}
                            >
                                {savingDetails ? 'Saving...' : 'Submit'}
                            </button>
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
};

export default Details;