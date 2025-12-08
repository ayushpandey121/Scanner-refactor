// SampleDetailsDisplay.jsx
import React, { useState, useEffect } from 'react';
import { getApiBaseUrl } from '../utils/axiosConfig';
import useRiceStore from '../zustand/store';
import '../styles/SampleDetailsDisplay.css';

const SampleDetailsDisplay = ({ onClose }) => {
    const fileName = useRiceStore((state) => state.fileName);
    const selectedFile = useRiceStore((state) => state.selectedFile);
    const storedSampleDetails = useRiceStore((state) => state.sampleDetails);
    const selectedVariety = useRiceStore((state) => state.selectedVariety);
    const selectedSubVariety = useRiceStore((state) => state.selectedSubVariety);
    
    const [details, setDetails] = useState(null);
    const [varietyInfo, setVarietyInfo] = useState({ variety: null, subVariety: null });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchDetails = async () => {
            // Set variety info from store
            setVarietyInfo({
                variety: selectedVariety || null,
                subVariety: selectedSubVariety || null
            });

            // Priority 1: Check if sample details are stored in the Zustand store with meaningful data
            const hasStoreData = storedSampleDetails && (
                (storedSampleDetails.sellerName && storedSampleDetails.sellerName.trim()) || 
                (storedSampleDetails.sellerCode && storedSampleDetails.sellerCode.trim()) || 
                (storedSampleDetails.sampleName && storedSampleDetails.sampleName.trim()) ||
                (storedSampleDetails.sampleSource && storedSampleDetails.sampleSource.trim()) ||
                (storedSampleDetails.lotSize && storedSampleDetails.lotSize.toString().trim())
            );
            
            if (hasStoreData) {
                setDetails({
                    sellerName: storedSampleDetails.sellerName?.trim() || 'N/A',
                    sellerCode: storedSampleDetails.sellerCode?.trim() || 'N/A',
                    sampleName: storedSampleDetails.sampleName?.trim() || 'N/A',
                    sampleSource: storedSampleDetails.sampleSource?.trim() || 'N/A',
                    lotSize: storedSampleDetails.lotSize?.toString().trim() || 'N/A',
                    lotUnit: storedSampleDetails.lotUnit?.trim() || 'N/A',
                });
                setLoading(false);
                return;
            }

            const currentName = fileName || selectedFile?.name;
            if (!currentName) {
                // Try localStorage as last resort before showing error
                const storedDetails = localStorage.getItem('sampleDetails');
                if (storedDetails) {
                    try {
                        const parsed = JSON.parse(storedDetails);
                        const hasLocalData = (
                            (parsed.sellerName && parsed.sellerName.trim()) ||
                            (parsed.sellerCode && parsed.sellerCode.trim()) ||
                            (parsed.sampleName && parsed.sampleName.trim()) ||
                            (parsed.sampleSource && parsed.sampleSource.trim()) ||
                            (parsed.lotSize && parsed.lotSize.toString().trim())
                        );
                        if (hasLocalData) {
                            setDetails({
                                sellerName: parsed.sellerName?.trim() || 'N/A',
                                sellerCode: parsed.sellerCode?.trim() || 'N/A',
                                sampleName: parsed.sampleName?.trim() || 'N/A',
                                sampleSource: parsed.sampleSource?.trim() || 'N/A',
                                lotSize: parsed.lotSize?.toString().trim() || 'N/A',
                                lotUnit: parsed.lotUnit?.trim() || 'N/A',
                            });
                            useRiceStore.setState({ sampleDetails: parsed });
                            setLoading(false);
                            return;
                        }
                    } catch (err) {
                        console.error('Error parsing localStorage data:', err);
                    }
                }
                setError('No sample file available');
                setLoading(false);
                return;
            }

            const baseName = currentName.replace(/\.[^/.]+$/, '');
            const logFile = `${baseName}.json`;

            try {
                const baseUrl = getApiBaseUrl();
                const resolvedBase = baseUrl && baseUrl.trim().length > 0 ? baseUrl : 'http://localhost:5000';
                const endpoint = `${resolvedBase.replace(/\/$/, '')}/logs/${encodeURIComponent(logFile)}/details`;

                console.log('Fetching sample details from:', endpoint);
                const response = await fetch(endpoint);
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('Sample details API response:', data);
                    
                    // Check if we have meaningful data
                    const hasData = (
                        (data.seller_name && data.seller_name.trim()) ||
                        (data.seller_code && data.seller_code.trim()) ||
                        (data.sample_name && data.sample_name.trim()) ||
                        (data.sample_source && data.sample_source.trim()) ||
                        (data.lot_size && data.lot_size.toString().trim())
                    );
                    
                    if (hasData) {
                        const detailsData = {
                            sellerName: (data.seller_name && data.seller_name.trim()) || 'N/A',
                            sellerCode: (data.seller_code && data.seller_code.trim()) || 'N/A',
                            sampleName: (data.sample_name && data.sample_name.trim()) || 'N/A',
                            sampleSource: (data.sample_source && data.sample_source.trim()) || 'N/A',
                            lotSize: (data.lot_size && data.lot_size.toString().trim()) || 'N/A',
                            lotUnit: (data.lot_unit && data.lot_unit.trim()) || 'N/A',
                        };
                        setDetails(detailsData);
                        
                        // Update variety info if available in backend
                        if (data.variety || data.sub_variety) {
                            setVarietyInfo({
                                variety: data.variety || null,
                                subVariety: data.sub_variety || null
                            });
                        }
                        
                        setLoading(false);
                        return;
                    }
                }
                
                // Fallback to localStorage
                const storedDetails = localStorage.getItem('sampleDetails');
                if (storedDetails) {
                    try {
                        const parsed = JSON.parse(storedDetails);
                        const hasLocalData = (
                            (parsed.sellerName && parsed.sellerName.trim()) ||
                            (parsed.sellerCode && parsed.sellerCode.trim()) ||
                            (parsed.sampleName && parsed.sampleName.trim()) ||
                            (parsed.sampleSource && parsed.sampleSource.trim()) ||
                            (parsed.lotSize && parsed.lotSize.toString().trim())
                        );
                        if (hasLocalData) {
                            const detailsData = {
                                sellerName: parsed.sellerName?.trim() || 'N/A',
                                sellerCode: parsed.sellerCode?.trim() || 'N/A',
                                sampleName: parsed.sampleName?.trim() || 'N/A',
                                sampleSource: parsed.sampleSource?.trim() || 'N/A',
                                lotSize: parsed.lotSize?.toString().trim() || 'N/A',
                                lotUnit: parsed.lotUnit?.trim() || 'N/A',
                            };
                            setDetails(detailsData);
                            setLoading(false);
                            return;
                        }
                    } catch (parseErr) {
                        console.error('Error parsing localStorage:', parseErr);
                    }
                }
                
                // If we reach here, no data was found
                setError('No sample details found. Please fill the details form first.');
                setLoading(false);
            } catch (err) {
                console.error('Error fetching details:', err);
                setError('Error loading sample details');
                setLoading(false);
            }
        };

        fetchDetails();
    }, [fileName, selectedFile, storedSampleDetails, selectedVariety, selectedSubVariety]);

    if (loading) {
        return (
            <div className="details-display-container">
                <div className="details-display-header">
                    <h2>Sample Details</h2>
                    <button className="close-button" onClick={onClose}>✕</button>
                </div>
                <div className="details-display-loading">Loading details...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="details-display-container">
                <div className="details-display-header">
                    <h2>Sample Details</h2>
                    <button className="close-button" onClick={onClose}>✕</button>
                </div>
                <div className="details-display-error">{error}</div>
            </div>
        );
    }

    return (
        <div className="details-display-container">
            <div className="details-display-header">
                <h2>Sample Details</h2>
                <button className="close-button" onClick={onClose}>✕</button>
            </div>
            
            <div className="details-display-content">
                <div className="details-grid">
                    <div className="detail-item">
                        <span className="detail-label">Seller Name:</span>
                        <span className="detail-value">{details.sellerName}</span>
                    </div>
                    
                    <div className="detail-item">
                        <span className="detail-label">Seller Code:</span>
                        <span className="detail-value">{details.sellerCode}</span>
                    </div>
                    
                    <div className="detail-item">
                        <span className="detail-label">Sample Name:</span>
                        <span className="detail-value">{details.sampleName}</span>
                    </div>
                    
                    <div className="detail-item">
                        <span className="detail-label">Sample Source:</span>
                        <span className="detail-value">{details.sampleSource}</span>
                    </div>
                    
                    <div className="detail-item">
                        <span className="detail-label">Lot Size:</span>
                        <span className="detail-value">
                            {details.lotSize} {details.lotUnit !== 'N/A' ? details.lotUnit : ''}
                        </span>
                    </div>
                    
                    {/* Show variety info if available */}
                    {varietyInfo.variety && (
                        <div className="detail-item">
                            <span className="detail-label">Variety:</span>
                            <span className="detail-value">{varietyInfo.variety}</span>
                        </div>
                    )}
                    
                    {varietyInfo.subVariety && (
                        <div className="detail-item">
                            <span className="detail-label">Sub-Variety:</span>
                            <span className="detail-value">{varietyInfo.subVariety}</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SampleDetailsDisplay;