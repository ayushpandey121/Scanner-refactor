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

    const [formData, setFormData] = useState({
        sellerName: '',
        sellerCode: '',
        variety: '',
        type: '',
        sampleName: '',
        sampleSource: '',
        lotSize: '',
        lotUnit: ''
    });
    const [savingDetails, setSavingDetails] = useState(false);
    const [saveError, setSaveError] = useState(null);
    const [isFormStarted, setIsFormStarted] = useState(false);

    useEffect(() => {
        const storedDetails = localStorage.getItem('sampleDetails');
        if (!storedDetails) return;
        try {
            const parsed = JSON.parse(storedDetails);
            setFormData((prev) => ({ ...prev, ...parsed }));
        } catch (err) {
            console.warn('Failed to parse stored sample details', err);
        }
    }, []);

    const getLogFileName = () => {
        const currentName = fileName || selectedFile?.name;
        if (!currentName) return null;
        const baseName = currentName.replace(/\.[^/.]+$/, '');
        return `${baseName}.json`;
    };

    const saveDetailsToBackend = async (details, attempt = 0) => {
        const logFile = getLogFileName();
        if (!logFile) {
            console.warn('No associated log file detected; skipping backend details save.');
            return;
        }

        setSavingDetails(true);
        setSaveError(null);
        try {
            const baseUrl = getApiBaseUrl();
            const resolvedBase = baseUrl && baseUrl.trim().length > 0 ? baseUrl : 'http://localhost:5000';
            const endpoint = `${resolvedBase.replace(/\/$/, '')}/logs/${encodeURIComponent(logFile)}/details`;

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    seller_name: details.sellerName,
                    seller_code: details.sellerCode,
                    variety: details.variety,
                    type: details.type,
                    sample_name: details.sampleName,
                    sample_source: details.sampleSource,
                    lot_size: details.lotSize,
                    lot_unit: details.lotUnit,
                }),
            });

            if (!response.ok) {
                if (response.status === 404 && attempt < 3) {
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    return saveDetailsToBackend(details, attempt + 1);
                }
                const errorText = await response.text();
                throw new Error(`Failed to save details (${response.status}): ${errorText}`);
            }
            setSaveError(null);
        } catch (err) {
            console.error('Failed to save details to backend:', err);
            setSaveError('Unable to save details to backend. They have been stored locally.');
        } finally {
            setSavingDetails(false);
        }
    };

    const handleChange = (e) => {
        if (!isFormStarted) {
            setIsFormStarted(true);
        }
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const saveDetailsToFile = (data) => {
        const dataStr = JSON.stringify(data, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);

        const exportFileDefaultName = `sample-details-${data.sampleName || data.sampleCode || 'unknown'}-${new Date().toISOString().split('T')[0]}.json`;

        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('Form Data:', formData);
        // Store form data in localStorage for PDF generation
        localStorage.setItem('sampleDetails', JSON.stringify(formData));

        await saveDetailsToBackend(formData);

        // Check if analysis is complete before navigating
        if (analysisStatus === 'completed' && reportData) {
            // Analysis is complete, navigate to results
            navigate('/results');
        } else if (analysisStatus === 'error') {
            // Analysis failed, show error but allow navigation anyway
            alert('Analysis failed: ' + (analysisError || 'Unknown error') + '\nYou can still view the form data.');
            navigate('/results');
        } else {
            // Analysis still in progress, navigate anyway (Results page will handle loading)
            navigate('/results');
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
                    <label htmlFor="variety">Variety <span className="required">*</span></label>
                    <input
                        type="text"
                        id="variety"
                        name="variety"
                        value={formData.variety}
                        onChange={handleChange}
                        required
                    />
                </div>
                <div className="form-row">
                    <label htmlFor="type">Type <span className="required">*</span></label>
                    <select
                        id="type"
                        name="type"
                        value={formData.type}
                        onChange={handleChange}
                        required
                    >
                        <option value="">Select Type</option>
                        <option value="Sella">Sella</option>
                        <option value="Steam">Steam</option>
                        <option value="Raw">Raw</option>
                    </select>
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
                {isFormStarted && (
                    <div className="form-row">
                        <button type="submit" className="submit-button">Submit</button>
                    </div>
                )}
                {savingDetails && (
                    <div className="status-content" style={{ marginTop: '8px' }}>
                        <span>Saving details...</span>
                    </div>
                )}
                </form>
            </div>
        </div>
    );
};

export default Details;
