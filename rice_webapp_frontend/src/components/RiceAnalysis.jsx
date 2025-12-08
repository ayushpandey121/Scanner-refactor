import "../styles/RiceAnalysis.css";
import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import useRiceStore from "../zustand/store";
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

const discolorColorMap = {
  Red: "#ff0000",
  Yellow: "#ffff00",
  Brown: "#8b4513",
  No: "#00ff00", // healthy
};

const RiceAnalysis = () => {
  const canvasRef = useRef(null);
  const imageRef = useRef(new Image());
  const scaledGrainsRef = useRef([]);
  const navigate = useNavigate();

  const {
    grains,
    chartData,
    previewImage,
    selectedGrainId,
    setSelectedGrainId,
    hoveredGrainId,
    setHoveredGrainId,
  } = useRiceStore();

  // Find the selected grain
  const selectedGrain =
    grains?.find((grain) => grain.id === selectedGrainId) || grains?.[0];

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

  useEffect(() => {
    if (!canvasRef.current || !previewImage) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const img = imageRef.current;

    img.onload = () => {
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
        const [x, y, w, h] = grain.grain_coordinates.map((v) => v * scale);
        const discolor = grain.discolor || "No";
        const boxColor = discolorColorMap[discolor] || "#4caf50";

        const isSelected = grain.id === selectedGrainId;
        const isHovered = grain.id === hoveredGrainId;

        // Only draw bounding box if grain is selected or hovered
        if (isSelected || isHovered) {
          ctx.strokeStyle = isSelected ? "#ff0000" : "#ffff00";
          ctx.lineWidth = isSelected ? 2 : 1;
          ctx.strokeRect(x, y, w, h);
        }

        scaledGrainsRef.current.push({
          x,
          y,
          width: w,
          height: h,
          grain,
        });
      });
    };

    img.src = previewImage;
  }, [previewImage, grains, chartData, selectedGrainId, hoveredGrainId]);

  const handleExportPDF = () => {
    const doc = new jsPDF();
    doc.setFont("helvetica", "bold");
    doc.setFontSize(18);
    doc.setTextColor("#3b82f6");
    doc.text(`Grain #${id} Analysis Report`, 14, 18);

    // No image section

    doc.setFontSize(12);
    doc.setTextColor("#222");
    doc.text("Defect Analysis", 14, 32);
    autoTable(doc, {
      startY: 36,
      head: [["Property", "Value"]],
      body: [
        ["Category", category ?? "N/A"],
        ["Chalky", chalky ? "Yes" : "No"],
        ["Broken", broken ? "Yes" : "No"],
        ["Discolour", displayDiscolour],
        ["Colour", displayColour ?? "N/A"],
      ],
      theme: "grid",
      styles: { fontSize: 11, cellPadding: 2 },
      headStyles: {
        fillColor: [59, 130, 246],
        textColor: 255,
        fontStyle: "bold",
      },
      alternateRowStyles: { fillColor: [240, 248, 255] },
    });

    const afterDefectY = doc.lastAutoTable.finalY + 8;
    doc.setTextColor("#16a34a");
    doc.text("Grain Metrics", 14, afterDefectY);
    autoTable(doc, {
      startY: afterDefectY + 4,
      head: [["Metric", "Value"]],
      body: [
        ["Length", `${length?.toFixed(2)} mm`],
        ["Width", `${width?.toFixed(2)} mm`],
        ["Area", `${(length * width)?.toFixed(2)} mm²`],
        ["L/B Ratio", `${(length / width)?.toFixed(2)}`],
      ],
      theme: "grid",
      styles: { fontSize: 11, cellPadding: 2 },
      headStyles: {
        fillColor: [22, 163, 74],
        textColor: 255,
        fontStyle: "bold",
      },
      alternateRowStyles: { fillColor: [240, 255, 244] },
    });

    const afterMetricsY = doc.lastAutoTable.finalY + 8;
    doc.setTextColor("#a78bfa");
    doc.text("Variety Prediction Confidence", 14, afterMetricsY);
    autoTable(doc, {
      startY: afterMetricsY + 4,
      head: [["Variety", "Confidence"]],
      body: sortedConf.map(([label, value]) => [
        label,
        `${((value / totalConfidence) * 100).toFixed(1)}%`,
      ]),
      theme: "grid",
      styles: { fontSize: 11, cellPadding: 2 },
      headStyles: {
        fillColor: [167, 139, 250],
        textColor: 255,
        fontStyle: "bold",
      },
      alternateRowStyles: { fillColor: [245, 236, 255] },
    });

    doc.setFontSize(10);
    doc.setTextColor("#888");
    doc.text(
      "Prediction based on model v20250715",
      14,
      doc.lastAutoTable.finalY + 10
    );

    doc.save(`grain-${id}-analysis.pdf`);
  };

  if (!selectedGrain || !grains) {
    return (
      <div className="no-grain-selected">
        <p>No grain selected or data available</p>
        <button onClick={() => navigate("/results")}>Back to Results</button>
      </div>
    );
  }

  const {
    all_confidences,
    length,
    width,
    grain_url,
    id,
    category,
    chalky,
    broken,
    discolor,
    colour,
  } = selectedGrain;

  // Handle discolor and colour logic
  const displayDiscolour =
    !discolor || discolor === 0 || discolor.toLowerCase() === "no" ? "No" : "Yes";
  const displayColour =
    !discolor || discolor === 0 || discolor.toLowerCase() === "no" ? "white" : discolor;

  // Debug logging
  console.log("Grain data:", {
    id,
    discolor,
    colour,
    displayDiscolour,
    displayColour,
  });

  const totalConfidence = all_confidences ? Object.values(all_confidences).reduce(
    (a, b) => a + b,
    0
  ) : 0;
  const sortedConf = all_confidences ? Object.entries(all_confidences).sort(
    (a, b) => b[1] - a[1]
  ) : [];

  return (
    <div className="rice-analysis-container">
      {/* <Sidebar /> */}

      <div className="analysis-main">
        <div className="header-bar">
          <div className="header-left">
          <p className="back-link" onClick={() => navigate("/results")}>
            ← Back to Scan Results
          </p>
            <h2>Rice Grain Analysis</h2>
            </div>
          <button className="export-btn" onClick={handleExportPDF}>
            Export Results
          </button>
        </div>

        <div className="analysis-content">
          <div className="scan-image-container">
            <p className="grain-id-title">Click a grain to analyze</p>
            <div className="result-image-container">
              <canvas
                ref={canvasRef}
                onClick={handleCanvasClick}
                onMouseMove={handleMouseMove}
                className="result-image"
              />
            </div>

            <div className="view-switch">
              <button className="active-tab">Scanner View</button>
              <button className="tab" onClick={() => navigate("/gallery")}>
                Filmstrip View
              </button>
            </div>

            <div className="metrics-section">
              <div className="metric">
                <span>Length</span>
                <strong>{length?.toFixed(2)} mm</strong>
              </div>
              <div className="metric">
                <span>Width</span>
                <strong>{width?.toFixed(2)} mm</strong>
              </div>
              {/* <div className="metric">
                <span>Area</span>
                <strong>{(length * width)?.toFixed(2)} mm²</strong>
              </div> */}
              <div className="metric">
                <span>L/B Ratio</span>
                <strong>{(length / width)?.toFixed(2)}</strong>
              </div>
            </div>
          </div>

          <div className="selected-grain-panel">
            <div className="grain-image-frame">
              <div className="grain-id-header">Grain #{id}</div>
              <img
                className="grain-main-image"
                src={grain_url}
                alt={`Grain ${id}`}
              />
            </div>

            <div className="grain-details">
              <div className="grain-characteristics">
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
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiceAnalysis;
