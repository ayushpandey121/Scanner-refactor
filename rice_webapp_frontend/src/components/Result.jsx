import React, { useRef, useEffect, useState, useMemo } from "react";
import "../styles/Result.css";
import useRiceStore from "../zustand/store";
import { useNavigate } from "react-router-dom";
import Histogram from "./Histogram";
import { getApiBaseUrl } from "../utils/axiosConfig";
import { CiCircleInfo } from "react-icons/ci";
import { generateGrainQualityReportPDF } from "../utils/pdfGenerator";
import Details from "./Details";
import SampleDetailsDisplay from './SampleDetailsDisplay';

const reanalyzeImage = async (file, minlen, chalky_percentage) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("minlen", minlen.toString());
  formData.append("chalky_percentage", chalky_percentage.toString());

  try {
    const baseUrl = getApiBaseUrl();
    // Construct URL properly - handle empty string for dev proxy
    const url = baseUrl ? `${baseUrl}/predict` : '/predict';

    console.log('Reanalyzing image...');
    console.log('URL:', url);
    console.log('File:', { name: file.name, size: file.size, type: file.type });
    console.log('Parameters:', { minlen, chalky_percentage });

    const res = await fetch(url, {
      method: "POST",
      body: formData,
      // Don't set Content-Type - browser will set it with boundary for FormData
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error('Server error:', res.status, errorText);
      throw new Error(`Server error (${res.status}): ${errorText || 'Unknown error'}`);
    }

    return await res.json();
  } catch (error) {
    console.error('Reanalysis fetch error:', error);

    // Provide more specific error messages
    if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
      const baseUrl = getApiBaseUrl();
      const url = baseUrl || 'http://localhost:5000';
      throw new Error(
        `Could not connect to the backend server at ${url}/predict. ` +
        `Please ensure the backend service is running. ` +
        `Error: ${error.message}`
      );
    }

    // Re-throw with original message if it's already a formatted error
    if (error.message && !error.message.includes('Could not connect')) {
      throw error;
    }

    throw new Error(`Reanalysis failed: ${error.message || 'Unknown error'}`);
  }
};

// Helper function to convert data URL to File
const dataURLtoFile = (dataurl, filename) => {
  const arr = dataurl.split(',');
  const mime = arr[0].match(/:(.*?);/)[1];
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new File([u8arr], filename, { type: mime });
};

// Helper function to convert blob URL to File
const blobURLtoFile = async (blobUrl, filename) => {
  const response = await fetch(blobUrl);
  const blob = await response.blob();
  return new File([blob], filename, { type: blob.type || 'image/jpeg' });
};

// Helper function to clone a File object to ensure it has fresh data
const cloneFile = async (file) => {
  try {
    // Read the file into an ArrayBuffer
    const arrayBuffer = await file.arrayBuffer();
    // Create a new Blob and File from the ArrayBuffer
    const blob = new Blob([arrayBuffer], { type: file.type });
    return new File([blob], file.name, { type: file.type, lastModified: file.lastModified });
  } catch (error) {
    console.error('Error cloning file:', error);
    throw error;
  }
};

const Result = () => {
  const [selectedLengthRange, setSelectedLengthRange] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const navigate = useNavigate();
  const {
    grains,
    reportData,
    previewImage,
    croppedImageUrl,
    selectedGrainId,
    setSelectedGrainId,
    hoveredGrainId,
    setHoveredGrainId,
    updateChartDataFromGrains,
    selectedFile,
    parameters,
    fileName,
    analysisStatus,
    analysisError,
    selectedVariety,
    selectedSubVariety,
    selectedVarietyData,
    selectedSubVarietyData,
  } = useRiceStore();

  // console.log("Report Data:", reportData);
  // console.log("Discolor Count from reportData:", reportData?.discolorCount);

  const canvasRef = useRef(null);
  const imageRef = useRef(new Image());
  const scaledGrainsRef = useRef([]);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [selectedDefect, setSelectedDefect] = useState(null); // default to show all grains
  const [selectedDiscolorType, setSelectedDiscolorType] = useState(null);
  const [imageError, setImageError] = useState(false);
  const [minlen, setMinlen] = useState(parameters?.minlen || 5.0);
  const [chalkyThreshold, setChalkyThreshold] = useState(
    parameters?.chalky_percentage || 30.0
  );

  // Update slider values when parameters change (e.g., from dropdown selection)
  useEffect(() => {
    if (parameters?.minlen !== undefined) {
      setMinlen(parameters.minlen);
    }
  }, [parameters?.minlen]);

  useEffect(() => {
    if (parameters?.chalky_percentage !== undefined) {
      setChalkyThreshold(parameters.chalky_percentage);
    }
  }, [parameters?.chalky_percentage]);
  const [loadingBroken, setLoadingBroken] = useState(false);
  const [loadingChalky, setLoadingChalky] = useState(false);
  const backendFileBaseUrl = useMemo(() => {
    const base = getApiBaseUrl();
    if (base && base.trim().length > 0) {
      return base;
    }
    return "http://localhost:5000";
  }, []);

  // Use cropped image as primary since grain coordinates are relative to it, fallback to original
  const displayImage = croppedImageUrl || previewImage;

  // Get file for reanalysis - handles both uploaded and scanned images
  const resolveToBackendUrl = (url) => {
    if (!url) return null;
    if (/^(data:|blob:|https?:)/i.test(url)) {
      return url;
    }
    if (url.startsWith("/")) {
      return `${backendFileBaseUrl}${url}`;
    }
    return `${backendFileBaseUrl}/${url}`;
  };

  const createFileFromSource = async (source, filenameHint) => {
    const resolvedSource = resolveToBackendUrl(source);
    if (!resolvedSource) {
      return null;
    }
    const targetName = filenameHint || fileName || "reanalyze.jpg";

    if (resolvedSource.startsWith("data:")) {
      return dataURLtoFile(resolvedSource, targetName);
    }

    if (resolvedSource.startsWith("blob:")) {
      return await blobURLtoFile(resolvedSource, targetName);
    }

    const response = await fetch(resolvedSource);
    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.status} ${response.statusText}`);
    }
    const blob = await response.blob();
    if (!blob || blob.size === 0) {
      throw new Error("Fetched image blob is empty");
    }
    return new File([blob], targetName, { type: blob.type || "image/jpeg" });
  };

  const getFileForReanalysis = async () => {
    // First, try to use selectedFile if it exists and is valid
    if (selectedFile && selectedFile instanceof File) {
      // Verify the file is still valid by checking if it has a name and size
      if (selectedFile.name && selectedFile.size > 0) {
        try {
          // Clone the file to ensure we have fresh data that won't be affected by blob URL revocation
          const clonedFile = await cloneFile(selectedFile);
          console.log('Using cloned selectedFile:', { name: clonedFile.name, size: clonedFile.size });
          return clonedFile;
        } catch (error) {
          console.warn('Failed to clone selectedFile, will try to reconstruct:', error);
          // Fall through to reconstruction
        }
      }
    }

    const candidateSources = Array.from(
      new Set(
        [
          previewImage,
          fileName ? `/upload/${fileName}` : null,
          croppedImageUrl,
        ].filter(Boolean)
      )
    );

    for (const source of candidateSources) {
      try {
        const reconstructedFile = await createFileFromSource(source, fileName || "reanalyze.jpg");
        if (reconstructedFile && reconstructedFile.size > 0) {
          console.log("File reconstructed successfully from source:", source, {
            name: reconstructedFile.name,
            size: reconstructedFile.size,
            type: reconstructedFile.type,
          });
          return reconstructedFile;
        }
      } catch (error) {
        console.warn(`Failed to reconstruct file from source ${source}:`, error);
      }
    }

    console.error("No file sources available for reanalysis");
    return null;
  };

  const discolorColorMap = {
    yellow: "#FFD700",
    red: "#FF0000",
    black: "#000000",
    brown: "#A0522D",
    blue: "#0000FF",
    green: "#008000",
    purple: "#800080",
    orange: "#FFA500",
    pink: "#FFC0CB",
    gray: "#808080",
    no: "#83f4a3ff",
  };

  const defectColorMap = {
    chalky: "#1001ebff",
    broken: "#a7ec12ff",
    discolor: "#f59e0b",
  };

  const discolorTypes = useMemo(() => {
    if (!grains) return [];
    const types = grains
      .map((g) => g.discolor)
      .filter((v, i, a) => a.indexOf(v) === i);
    return types;
  }, [grains]);

  const discolorCount = reportData?.discolorCount || 0;
  const avgLength = reportData?.avgLength || 0;
  const brokenCount = reportData?.brokenCount;
  const chalkyCount = reportData?.chalkyCount;
  const avgWidth = reportData?.avgWidth || 1;
  const totalGrains = reportData?.grainCount || 0;
  const kettValue = reportData?.kettValue || 0;

  // Compute longest and shortest length using useMemo
  const { longestLength, shortestLength } = useMemo(() => {
    if (!grains || grains.length === 0) {
      return { longestLength: 0, shortestLength: 0 };
    }

    const lengths = grains.map((g) => g.length || 0);
    const longestLength = Math.max(...lengths).toFixed(2);
    const shortestLength = Math.min(...lengths).toFixed(2);

    return { longestLength, shortestLength };
  }, [grains]);

  // Compute defect percentages
  const brokenPercentage =
    totalGrains > 0 ? ((brokenCount / totalGrains) * 100).toFixed(1) : 0;
  const chalkyPercentage =
    totalGrains > 0 ? ((chalkyCount / totalGrains) * 100).toFixed(1) : 0;
  const discolorPercentage =
    totalGrains > 0 ? ((discolorCount / totalGrains) * 100).toFixed(1) : 0;

  // Compute length histogram data
  const lengthHistogramData = useMemo(() => {
    if (!grains || grains.length === 0) return [];

    const lengths = grains.map((g) => g.length || 0).filter((l) => l > 0);
    if (lengths.length === 0) return [];

    const minLength = Math.floor(Math.min(...lengths));
    const maxLength = Math.ceil(Math.max(...lengths));

    const bins = {};
    for (let i = minLength; i <= maxLength; i += 0.5) {
      bins[i] = 0;
    }

    lengths.forEach((length) => {
      const bin = Math.ceil(length * 2) / 2;
      if (bins[bin] !== undefined) {
        bins[bin]++;
      }
    });

    return Object.entries(bins)
      .map(([length, count]) => ({
        length: parseFloat(length),
        count,
      }))
      .filter((item) => item.count > 0)
      .sort((a, b) => a.length - b.length);
  }, [grains]);

  useEffect(() => {
    const handleResize = () => {
      if (canvasRef.current?.parentElement) {
        setContainerSize({
          width: canvasRef.current.parentElement.clientWidth,
          height: canvasRef.current.parentElement.clientHeight,
        });
      }
    };

    const observer = new ResizeObserver(handleResize);
    if (canvasRef.current?.parentElement) {
      observer.observe(canvasRef.current.parentElement);
    }

    handleResize();
    return () => observer.disconnect();
  }, []);

  const hasDefect = (grain, defectType) => {
    switch (defectType) {
      case "chalky":
        return grain.chalky === "Yes";
      case "broken":
        return grain.broken === true;
      case "discolor":
        return grain.discolor && grain.discolor.toLowerCase() !== "no";
      default:
        return true; // Show all if no filter
    }
  };


  useEffect(() => {
    const displayImage = croppedImageUrl || previewImage;
    if (!canvasRef.current || !displayImage) return;

    setImageError(false);

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const img = new Image();
    imageRef.current = img;

    const drawCanvas = () => {
      const container = canvas.parentElement;
      const scale = container.clientWidth / img.width;
      const scaledWidth = img.width * scale;
      const scaledHeight = img.height * scale;

      canvas.width = scaledWidth;
      canvas.height = scaledHeight;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, scaledWidth, scaledHeight);

      scaledGrainsRef.current = [];

      grains?.forEach((grain) => {
        // PRIORITY 1: Length filter (if active, ONLY check this)
        if (selectedLengthRange && grain.length !== undefined) {
          // If length filter is active, show ONLY grains within range
          if (grain.length <= selectedLengthRange.min || grain.length > selectedLengthRange.max) {
            return; // Skip grains outside range
          }
          // If we reach here, grain is in range - don't check other filters
        }
        // PRIORITY 2: Defect filters (only check if NO length filter)
        else if (selectedDefect) {
          // Filter by defect type
          if (selectedDefect !== "discolor" && !hasDefect(grain, selectedDefect)) {
            return;
          }

          // If discolor is selected, check discolor type filter
          if (selectedDefect === "discolor") {
            // Skip "no" discolor grains
            if (grain.discolor && grain.discolor.toLowerCase() === "no") {
              return;
            }
            // If specific discolor type is selected, filter by it
            if (selectedDiscolorType && grain.discolor !== selectedDiscolorType) {
              return;
            }
          }
        }

        // Skip grains with invalid coordinates
        if (!grain.grain_coordinates || grain.grain_coordinates.length !== 4) {
          return;
        }

        const [x, y, width, height] = grain.grain_coordinates;

        const scaledX = x * scale;
        const scaledY = y * scale;
        const scaledW = width * scale;
        const scaledH = height * scale;

        const isSelected = grain.id === selectedGrainId;
        const isHovered = grain.id === hoveredGrainId;
        const hasActiveFilter = selectedLengthRange || selectedDefect;

        // Only draw bounding box if there's an active filter or grain is selected/hovered
        if (hasActiveFilter || isSelected || isHovered) {
          let color;
          if (selectedLengthRange) {
            color = "#FF1493";
          } else if (selectedDefect) {
            color = defectColorMap[selectedDefect] || "#f43f5e";
          } else {
            color = "#008000";
          }

          ctx.strokeStyle = isSelected
            ? "#ff0000"
            : isHovered
              ? "#ffff00"
              : color;
          ctx.lineWidth = isSelected ? 3 : isHovered ? 2 : 1;
          ctx.strokeRect(scaledX, scaledY, scaledW, scaledH);
        }

        scaledGrainsRef.current.push({
          x: scaledX,
          y: scaledY,
          width: scaledW,
          height: scaledH,
          grain,
        });
      });
    };

    img.onerror = () => {
      setImageError(true);
    };

    img.onload = drawCanvas;

    img.src = `${displayImage.split("?")[0]}?t=${Date.now()}`;

    if (img.complete) {
      drawCanvas();
    }
  }, [
    croppedImageUrl,
    previewImage,
    grains,
    selectedGrainId,
    // hoveredGrainId,
    containerSize,
    selectedDefect,
    selectedDiscolorType,
    selectedLengthRange
  ]);
  // Update chart data from grains on change
  useEffect(() => {
    updateChartDataFromGrains();
  }, [grains]);

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    for (const box of scaledGrainsRef.current) {
      if (
        clickX >= box.x &&
        clickX <= box.x + box.width &&
        clickY >= box.y &&
        clickY <= box.y + box.height
      ) {
        setSelectedGrainId(box.grain.id);
        navigate("/analysis");
        break;
      }
    }
  };

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    let foundHover = false;
    for (const box of scaledGrainsRef.current) {
      if (
        mouseX >= box.x &&
        mouseX <= box.x + box.width &&
        mouseY >= box.y &&
        mouseY <= box.y + box.height
      ) {
        canvas.style.cursor = "pointer";
        setHoveredGrainId(box.grain.id);
        foundHover = true;
        break;
      }
    }

    if (!foundHover) {
      canvas.style.cursor = "default";
      setHoveredGrainId(null);
    }
  };

  // Replace the existing handleDefectClick function in Result.jsx with this:

  const handleDefectClick = (defectType) => {
    if (selectedDefect === defectType) {
      // Toggle off - clear ALL filters
      setSelectedDefect(null);
      setSelectedDiscolorType(null);
      setSelectedLengthRange(null);
    } else {
      // Toggle on - clear other filters and set this defect
      setSelectedLengthRange(null); // Clear length filter
      setSelectedDefect(defectType);
      setSelectedDiscolorType(null);
    }
  };
  const handleHistogramBarClick = (data) => {
    const clickedEntry =
      data?.activePayload?.[0]?.payload ||
      data?.payload ||
      (typeof data?.length === "number" ? data : null);

    if (!clickedEntry || typeof clickedEntry.length !== "number") {
      return;
    }

    const clickedLength = clickedEntry.length;
    const binSize = 0.5;

    const minLength = clickedLength - binSize;
    const maxLength = clickedLength;

    if (
      selectedLengthRange &&
      Math.abs(selectedLengthRange.min - minLength) < 0.01 &&
      Math.abs(selectedLengthRange.max - maxLength) < 0.01
    ) {
      setSelectedLengthRange(null);
    } else {
      setSelectedLengthRange({ min: minLength, max: maxLength });
    }
  };
  const handleReanalyzeBroken = async () => {
    // For data loaded from logs, recalculate broken grains locally using saved lengths
    const current = useRiceStore.getState();
    const currentGrains = current.grains || [];

    if (currentGrains.length > 0 && currentGrains[0].length !== undefined) {
      // Recalculate broken status locally using saved grain lengths
      setLoadingBroken(true);
      try {
        const updatedGrains = currentGrains.map(grain => ({
          ...grain,
          broken: grain.length < minlen
        }));

        const newBrokenCount = updatedGrains.filter(grain => grain.broken).length;

        const updatedParameters = {
          ...current.parameters,
          minlen,
        };

        useRiceStore.setState({
          grains: updatedGrains,
          reportData: {
            ...current.reportData,
            brokenCount: newBrokenCount,
          },
          parameters: updatedParameters,
        });
      } catch (error) {
        console.error("Local recalculation failed:", error);
        alert("Recalculation failed: " + error.message);
      } finally {
        setLoadingBroken(false);
      }
    } else {
      // Fallback to reanalysis for fresh uploads/scans
      const file = await getFileForReanalysis();
      if (!file) {
        console.error("Cannot reanalyze: No valid file available");
        alert("Cannot reanalyze: No valid file available. Please go back and upload/scan the image again.");
        return;
      }

      setLoadingBroken(true);
      try {
        const data = await reanalyzeImage(file, minlen, chalkyThreshold);
        // Update grains, chalky and broken counts
        const updatedParameters = {
          ...current.parameters,
          minlen,
        };

        useRiceStore.setState({
          grains: data.result.grain,
          reportData: {
            ...current.reportData,
            brokenCount: data.result.statistics.broken_count,
          },
          croppedImageUrl: `${data.cropped_url}?t=${Date.now()}`, // Force reload by adding timestamp
          parameters: updatedParameters,
        });
      } catch (error) {
        console.error("Reanalysis failed:", error);
        alert("Reanalysis failed: " + error.message);
      } finally {
        setLoadingBroken(false);
      }
    }
  };

  const handleReanalyzeChalky = async () => {
    const file = await getFileForReanalysis();
    if (!file) {
      console.error("Cannot reanalyze: No valid file available");
      alert("Cannot reanalyze: No valid file available. Please go back and upload/scan the image again.");
      return;
    }

    setLoadingChalky(true);
    try {
      console.log('Starting reanalysis with:', { minlen, chalkyThreshold });
      const data = await reanalyzeImage(file, minlen, chalkyThreshold);
      if (!data) {
        throw new Error('Received empty response from server');
      }
      // Update grains, chalky and broken counts
      const current = useRiceStore.getState();
      const updatedParameters = {
        ...current.parameters,
        chalky_percentage: chalkyThreshold,
      };

      useRiceStore.setState({
        grains: data.result.grain,
        reportData: {
          ...current.reportData,
          chalkyCount: data.result.statistics.chalky_count,
        },
        croppedImageUrl: `${data.cropped_url}?t=${Date.now()}`, // Force reload by adding timestamp
        parameters: updatedParameters,
      });
    } catch (error) {
      console.error("Reanalysis failed:", error);
      alert("Reanalysis failed: " + error.message);
    } finally {
      setLoadingChalky(false);
    }
  };

  const handleExport = async () => {
    try {
      await generateGrainQualityReportPDF({
        avgLength,
        avgWidth,
        totalGrains,
        brokenCount,
        chalkyCount,
        discolorCount,
        lengthHistogramData,
      });
    } catch (error) {
      console.error("PDF export failed:", error);
      alert("PDF export failed: " + error.message);
    }
  };

  useEffect(() => {
    setSelectedGrainId(null);
  }, []);

  // Handle different analysis states
  if (analysisStatus === 'loading') {
    return (
      <div className="result-dashboard">
        <main className="result-main">
          <section className="result-section">
            <div className="result-section-header">
              <div className="left-section">
                <h2>Scan Results</h2>
                <p>More info <CiCircleInfo /></p>
              </div>
            </div>
            <div className="analysis-loading">
              <div className="loading-spinner"></div>
              <h3>Analysing Result...</h3>
              <p>Please wait while we process your image.</p>
            </div>
          </section>
        </main>
      </div>
    );
  }

  if (analysisStatus === 'error') {
    return (
      <div className="result-dashboard">
        <main className="result-main">
          <section className="result-section">
            <div className="result-section-header">
              <div className="left-section">
                <h2>Scan Results</h2>
                <p>More info <CiCircleInfo /></p>
              </div>
            </div>
            <div className="analysis-error">
              <h3>Analysis Failed</h3>
              <p>{analysisError || 'An unknown error occurred during analysis.'}</p>
              <button onClick={() => navigate('/upload')} className="retry-button">
                Try Again
              </button>
            </div>
          </section>
        </main>
      </div>
    );
  }

  if (!reportData && analysisStatus !== 'loading') {
    return (
      <div className="result-no-data">
        No report data available. Go back and upload an image.
      </div>
    );
  }

  return (
    <div className="result-dashboard">
      <main className="result-main">
        <section className="result-section">
          <div className="result-section-header">
            <div className="left-section">
              <h2>Scan Results</h2>
              <p>More info <CiCircleInfo className="info" onClick={() => setShowDetailsModal(true)} /></p>
            </div>
            <div className="right-section">
              <button className="result-export" onClick={handleExport}>Export Results</button>
            </div>
          </div>

          <div className="result-stats">
            <div className="statistics">
              <div className="result-stats-cards">
                <div className="result-stats-card">
                  <div className="result-stats-label">Average Length</div>
                  <div className="result-stats-value">{avgLength} mm</div>
                </div>
                <div className="result-stats-card">
                  <div className="result-stats-label">Average Width</div>
                  <div className="result-stats-value">{avgWidth} mm</div>
                </div>
                <div className="result-stats-card">
                  <div className="result-stats-label">L/B Ratio</div>
                  <div className="result-stats-value">
                    {(avgLength / avgWidth).toFixed(2)}
                  </div>
                </div>
                <div className="result-stats-card">
                  <div className="result-stats-label">Longest Grain</div>
                  <div className="result-stats-value">{longestLength} mm</div>
                </div>
                <div className="result-stats-card">
                  <div className="result-stats-label">Shortest Grain</div>
                  <div className="result-stats-value">{shortestLength} mm</div>
                </div>
                <div className="result-stats-card">
                  <div className="result-stats-label">Whiteness</div>
                  <div className="result-stats-value">{kettValue.toFixed(1)}</div>
                </div>
                <div
                  className={`result-stats-card ${selectedDefect === "broken" && !selectedLengthRange ? "selected" : ""
                    } ${loadingBroken ? "loading" : ""}`}
                  onClick={() => handleDefectClick("broken")}
                  style={{ cursor: "pointer" }}
                >
                  <div className="card-content">
                    <div className="defect-title">
                      <span className="defect-dot broken-dot"></span>
                      <div className="result-stats-label">Broken</div>
                    </div>
                    <label
                      style={{ display: "flex", flexDirection: "column", alignItems: "center" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      Min Length: {minlen} mm
                      <input
                        type="range"
                        min="0"
                        max="10"
                        step="0.1"
                        value={minlen}
                        onChange={(e) => setMinlen(parseFloat(e.target.value))}
                        onMouseUp={handleReanalyzeBroken}
                        disabled={loadingBroken}
                        style={{ width: "100%" }}
                      />
                    </label>
                    <div className="result-stats-value">{brokenCount} grains</div>
                    <div className="progress-percentage">{brokenPercentage}%</div>
                  </div>
                  {loadingBroken && <div className="card-loader-overlay"><div className="card-loader"></div></div>}
                </div>
                <div
                  className={`result-stats-card ${selectedDefect === "chalky" && !selectedLengthRange ? "selected" : ""
                    } ${loadingChalky ? "loading" : ""}`}
                  onClick={() => handleDefectClick("chalky")}
                  style={{ cursor: "pointer" }}
                >
                  <div className="card-content">
                    <div className="defect-title">
                      <span className="defect-dot chalky-dot"></span>
                      <div className="result-stats-label">Chalky</div>
                    </div>
                    <label
                      style={{ display: "flex", flexDirection: "column", alignItems: "center" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      Threshold : {chalkyThreshold}%
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="1"
                        value={chalkyThreshold}
                        onChange={(e) => setChalkyThreshold(parseFloat(e.target.value))}
                        onMouseUp={handleReanalyzeChalky}
                        disabled={loadingChalky}
                        style={{ width: "100%" }}
                      />
                    </label>
                    <div className="result-stats-value">{chalkyCount} grains</div>
                    <div className="progress-percentage">{chalkyPercentage}%</div>
                  </div>
                  {loadingChalky && <div className="card-loader-overlay"><div className="card-loader"></div></div>}
                </div>
                <div
                  className={`result-stats-card ${selectedDefect === "discolor" && !selectedLengthRange ? "selected" : ""
                    }`}
                  onClick={() => handleDefectClick("discolor")}
                  style={{ cursor: "pointer" }}
                >
                  <div className="defect-title">
                    <span className="defect-dot discolor-dot"></span>
                    <div className="result-stats-label">Discolor</div>
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill discolor-fill"
                      style={{ width: `${discolorPercentage}%` }}
                    ></div>
                  </div>
                  <div className="result-stats-value">
                    {discolorCount} grains
                  </div>
                  <div className="progress-percentage">
                    {discolorPercentage}%
                  </div>
                </div>
              </div>

              {/* Length Histogram */}
              {lengthHistogramData.length > 0 && (
                <Histogram
                  lengthData={lengthHistogramData}
                  grains={grains}
                  onBarClick={handleHistogramBarClick}
                  selectedLengthRange={selectedLengthRange}
                  selectedSubVarietyData={selectedSubVarietyData}
                />
              )}
            </div>

            <div className="result-detected-section">
      <div className="result-detected-header">
                <h3>Detected Rice Grains: {totalGrains}</h3>
                {selectedDefect && !selectedLengthRange && (
                  <div className="result-legend">
                    <span className="result-legend-item">
                      <span
                        className="result-dot"
                        style={{
                          background:
                            defectColorMap[selectedDefect] || "#f43f5e",
                        }}
                      />
                      {selectedDefect.charAt(0).toUpperCase() +
                        selectedDefect.slice(1)}{" "}
                      Grains
                    </span>
                  </div>
                )}
                {selectedLengthRange && (
                  <div className="result-legend">
                    <span className="result-legend-item">
                      <span className="result-dot" style={{ background: "#FF1493" }}></span>
                      Length: {selectedLengthRange.min.toFixed(2)}mm - {selectedLengthRange.max.toFixed(2)}mm
                    </span>
                  </div>
                )}
              </div>

              <div className="result-image-container">
                {(croppedImageUrl || previewImage) && !imageError ? (
                  <canvas
                    key={displayImage}
                    ref={canvasRef}
                    onClick={handleCanvasClick}
                    onMouseMove={handleMouseMove}
                    style={{
                      maxWidth: "100%",
                      width: "100%",
                      borderRadius: "8px",
                    }}
                  />
                ) : (
                  <div className="result-image-placeholder">
                    {imageError ? "Image failed to load" : "No image available"}
                  </div>
                )}
              </div>

              <div className="result-view-buttons">
                <button className="scanner-button">Scanner View</button>
                <button onClick={() => navigate("/gallery")}>
                  Filmstrip View
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>

      {showDetailsModal && (
        <div className="modal-overlay" onClick={() => setShowDetailsModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <SampleDetailsDisplay onClose={() => setShowDetailsModal(false)} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Result;
