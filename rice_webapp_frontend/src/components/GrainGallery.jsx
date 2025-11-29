import React, { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import "../styles/Constant.css";
import "../styles/GrainGallery.css";
import useRiceStore from "../zustand/store";

// Lazy loading component for thumbnails
const LazyThumbnail = ({ grain, idx, isActive, onClick }) => {
  const [isVisible, setIsVisible] = useState(false);
  const imgRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <img
      ref={imgRef}
      className={`thumbnail ${isActive ? "active-thumbnail" : ""}`}
      src={isVisible ? grain.grain_url : ""}
      alt={`Grain ${idx + 1}`}
      onClick={onClick}
      loading="lazy"
    />
  );
};

const GrainGallery = () => {
  const navigate = useNavigate();
  const imageContainerRef = useRef(null);
  const thumbnailStripRef = useRef(null);

  const { grains, reportData } = useRiceStore();

  // Compute available filters based on grains data
  const availableFilters = useMemo(() => {
    if (!grains) return ["All"];
    const filters = ["All"];
    if (grains.some(grain => grain.broken)) filters.push("Broken");
    if (grains.some(grain => grain.chalky === "Yes")) filters.push("Chalky");
    if (grains.some(grain => grain.discolor.toLowerCase() !== "no")) filters.push("Discolor");
    return filters;
  }, [grains]);

  const [currentFilter, setCurrentFilter] = useState("All");

  // Ensure currentFilter is valid when grains change
  useEffect(() => {
    if (!availableFilters.includes(currentFilter)) {
      setCurrentFilter("All");
    }
  }, [availableFilters, currentFilter]);

  // Filter grains based on current filter
  const filteredGrains = useMemo(() => {
    if (!grains) return [];
    if (currentFilter === "All") return grains;
    if (currentFilter === "Broken") return grains.filter(grain => grain.broken);
    if (currentFilter === "Chalky") return grains.filter(grain => grain.chalky === "Yes");
    if (currentFilter === "Discolor") return grains.filter(grain => grain.discolor.toLowerCase() !== "no");
    return grains;
  }, [grains, currentFilter]);

  const [selectedGrainIndex, setSelectedGrainIndex] = useState(0);
  const selectedGrain = filteredGrains[selectedGrainIndex];

  // Handle discolor and colour logic
  const displayDiscolour =
    !selectedGrain?.discolor ||
    selectedGrain?.discolor === 0 ||
    selectedGrain?.discolor.toLowerCase() === "no"
      ? "No"
      : "Yes";
  const displayColour =
    !selectedGrain?.discolor ||
    selectedGrain?.discolor === 0 ||
    selectedGrain?.discolor.toLowerCase() === "no"
      ? "white"
      : selectedGrain?.discolor;

  const navigateToNextGrain = () => {
    if (selectedGrainIndex < filteredGrains.length - 1) {
      setSelectedGrainIndex(selectedGrainIndex + 1);
    }
  };

  const navigateToPrevGrain = () => {
    if (selectedGrainIndex > 0) {
      setSelectedGrainIndex(selectedGrainIndex - 1);
    }
  };

  const cycleFilter = () => {
    const currentIndex = availableFilters.indexOf(currentFilter);
    const nextIndex = (currentIndex + 1) % availableFilters.length;
    setCurrentFilter(availableFilters[nextIndex]);
    setSelectedGrainIndex(0); // Reset to first grain when filter changes
  };

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "ArrowRight") {
        navigateToNextGrain();
      } else if (event.key === "ArrowLeft") {
        navigateToPrevGrain();
      } else if (event.key === "/") {
        cycleFilter();
      } else if (event.key.toLowerCase() === "f") {
        if (imageContainerRef.current) {
          if (document.fullscreenElement) {
            document.exitFullscreen();
          } else {
            imageContainerRef.current.requestFullscreen();
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedGrainIndex, filteredGrains, selectedGrain, currentFilter]);

  useEffect(() => {
    if (thumbnailStripRef.current) {
      const activeThumbnail =
        thumbnailStripRef.current.querySelector(".active-thumbnail");
      if (activeThumbnail) {
        const strip = thumbnailStripRef.current;
        const stripRect = strip.getBoundingClientRect();
        const thumbRect = activeThumbnail.getBoundingClientRect();
        // Center the thumbnail in the strip
        strip.scrollLeft +=
          thumbRect.left +
          thumbRect.width / 2 -
          (stripRect.left + stripRect.width / 2);
      }
    }
  }, [selectedGrainIndex]);



  return (
    <div className="grain-gallery">
      <div className="grain-gallery-container">
        <div className="grain-gallery-content">
          <div className="grain-gallery-header">
            <div className="grain-gallery-title">
              <p className="back-btn" onClick={() => navigate("/results")}>
                ← Back to Scan Results
              </p>
              <h2 className="title">Rice Grain Analysis - Filmstrip View</h2>
            </div>
            <button className="export-btn">Export Results</button>
          </div>

          <div className="grain-gallery-body">
            <div className="grain-main-panel">
              <div className="grain-image-section">
                {/* <p className="grain-id">
                  Grain #
                  {selectedGrain?.grain_id ?? selectedGrain?.id ?? "Unknown ID"}
                </p> */}

                <p className="grain-count">
                  Grain {selectedGrainIndex + 1} of {filteredGrains.length} ({currentFilter})
                </p>

                <div className="filter-cards">
                  {availableFilters.map((filter) => (
                    <button
                      key={filter}
                      className={`filter-card ${currentFilter === filter ? "active-filter" : ""}`}
                      onClick={() => {
                        setCurrentFilter(filter);
                        setSelectedGrainIndex(0);
                      }}
                    >
                      {filter}
                    </button>
                  ))}
                </div>

                <div className="grain-image-frame" ref={imageContainerRef}>
                  <span
                    className={`nav-arrow left-arrow ${
                      selectedGrainIndex === 0 ? "disabled" : ""
                    }`}
                    onClick={navigateToPrevGrain}
                  >
                    ❮
                  </span>

                  <img
                    src={selectedGrain?.grain_url}
                    alt={`Grain ${selectedGrain?.id}`}
                    className="grain-main-image"
                  />

                  <span
                    className={`nav-arrow right-arrow ${
                      selectedGrainIndex === filteredGrains.length - 1
                        ? "disabled"
                        : ""
                    }`}
                    onClick={navigateToNextGrain}
                  >
                    ❯
                  </span>
                </div>

                <div className="filmstrip-section">
                  <div className="thumbnail-strip" ref={thumbnailStripRef}>
                    {filteredGrains.map((grain, idx) => (
                      <LazyThumbnail
                        key={idx}
                        grain={grain}
                        idx={idx}
                        isActive={idx === selectedGrainIndex}
                        onClick={() => setSelectedGrainIndex(idx)}
                      />
                    ))}
                  </div>
                </div>

                <div className="image-view-tabs">
                  <button className="tab" onClick={() => navigate(-1)}>
                    Scanner View
                  </button>
                  <button className="active-tab">Filmstrip View</button>
                </div>

                <div className="physical-characteristics">
                  <div className="character-box">
                    <span>Average Length</span>
                    <strong>{reportData.avgLength ?? "N/A"} mm</strong>
                  </div>
                  <div className="character-box">
                    <span>Average Width</span>
                    <strong>{reportData.avgWidth ?? "N/A"} mm</strong>
                  </div>
                  <div className="character-box">
                    <span>Whiteness</span>
                    <strong>
                      {reportData.kettValue?.toFixed(1) ?? "N/A"}
                    </strong>
                  </div>
                  <div className="character-box">
                    <span>L/B ratio</span>
                    <strong>
                      {(
                        reportData.avgLength / reportData.avgWidth || 0
                      ).toFixed(2)}
                    </strong>
                  </div>
                </div>
              </div>

              <div className="grain-details-section">
                <div className="defect-analysis">
                  <h4>Defect Analysis</h4>
                  <ul>
                    <li>
                      <strong>Chalky:</strong>{" "}
                      <span
                        className={
                          selectedGrain?.chalky === "Yes"
                            ? "defect-yes"
                            : "defect-no"
                        }
                      >
                        {selectedGrain?.chalky ?? "N/A"}
                      </span>
                    </li>
                    <li>
                      <strong>Broken:</strong>{" "}
                      <span
                        className={
                          selectedGrain?.broken ? "defect-yes" : "defect-no"
                        }
                      >
                        {selectedGrain?.broken ? "Yes" : "No"}
                      </span>
                    </li>
                    <li>
                      <strong>Discolour:</strong>{" "}
                      <span
                        className={
                          displayDiscolour === "Yes"
                            ? "defect-yes"
                            : "defect-no"
                        }
                      >
                        {displayDiscolour}
                      </span>
                    </li>
                    <li>
                      <strong>Colour:</strong> {displayColour ?? "N/A"}
                    </li>
                  </ul>
                </div>

                <div className="shortcuts">
                  <h4>Keyboard Shortcuts</h4>
                  <ul>
                    <li>← Previous Grain</li>
                    <li>→ Next Grain</li>
                    <li>f &nbsp;Fullscreen View</li>
                    <li>/ &nbsp;Cycle Filter ({availableFilters.join(", ")})</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GrainGallery;
