import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import logo from "../assets/logo.png";
import logoqr from "../assets/agsure.in.png";
import useRiceStore from "../zustand/store";

// Helper function to load image element
const loadImageElement = (src) =>
  new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });

/**
 * Generates a PDF report for grain quality analysis
 * @param {Object} reportData - The analysis report data
 * @param {Array} lengthHistogramData - Histogram data for grain lengths
 * @returns {Promise<void>}
 */
export const generateGrainQualityReportPDF = async ({
  avgLength,
  avgWidth,
  totalGrains,
  brokenCount,
  chalkyCount,
  discolorCount,
  lengthHistogramData,
}) => {
  try {
    // Read details saved from Details.jsx
    const stored = localStorage.getItem("sampleDetails");
    const details = stored ? JSON.parse(stored) : {};

    // Analysis summary values from report data
    const avgLen = Number(avgLength || 0);
    const avgWid = Number(avgWidth || 0);
    const lbRatio = avgWid ? (avgLen / avgWid).toFixed(2) : "0";
    const total = Number(totalGrains || 0);
    const brokenPct = total > 0 ? ((Number(brokenCount || 0) / total) * 100).toFixed(2) : "0";
    const chalkyCnt = Number(chalkyCount || 0);
    const chalkyPct = total > 0 ? ((chalkyCnt / total) * 100).toFixed(2) : "0";
    const discolorCnt = Number(discolorCount || 0);
    const discolorPct = total > 0 ? ((discolorCnt / total) * 100).toFixed(2) : "0";

    const now = new Date();
    const formatted =
      `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")} ` +
      `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

    const doc = new jsPDF({ unit: "pt", format: "a4", compress: false });
    const pageWidth = doc.internal.pageSize.getWidth();

    // Green banner - using explicit RGB values
    doc.setFillColor(98, 160, 64); // RGB for green #62A040
    doc.setDrawColor(98, 160, 64);
    doc.rect(40, 50, pageWidth - 80, 56, "F");

    // Logo
    try {
      const logoImg = await loadImageElement(logo);
      doc.addImage(logoImg, "PNG", 60, 120, 120, 48);
    } catch (_) {
      // ignore logo load failure
    }

    // Title
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(28);
    doc.text("Grain Quality Report", pageWidth / 2, 215, { align: "center" });

    // Details table
    const leftColWidth = 210;
    const startY = 250;
    autoTable(doc, {
      startY,
      head: [],
      body: [
        ["Sample Code", details.sampleCode || details.sampleName || "—"],
        ["Seller Code", details.sellerCode || "—"],
        ["Variety", details.variety || "—"],
        ["Date", formatted],
        ["Device", localStorage.getItem("deviceId") || "—"],
      ],
      theme: "grid",
      styles: {
        font: "helvetica",
        fontSize: 12,
        cellPadding: 10,
        halign: "left",
        valign: "middle",
      },
      columnStyles: {
        0: { fillColor: [242, 242, 242], cellWidth: leftColWidth, fontStyle: "bold" },
        1: { cellWidth: pageWidth - 80 - leftColWidth },
      },
      tableWidth: pageWidth - 80,
      margin: { left: 40, right: 40 },
      headStyles: { fillColor: [255, 255, 255] },
    });

    // Analysis Summary Section
    const afterDetailsY = doc.lastAutoTable.finalY + 24;
    doc.setFontSize(16);
    doc.setTextColor(0, 0, 0);
    doc.text("Analysis Summary", 40, afterDetailsY);

    autoTable(doc, {
      startY: afterDetailsY + 8,
      head: [],
      body: [
        ["Average Length (without broken)", avgLen ? avgLen.toFixed(2) : "0"],
        ["Average Breadth (without broken)", avgWid ? avgWid.toFixed(2) : "0"],
        ["L/B Ratio", lbRatio],
        ["No. of Grains", total.toString()],
        ["Broken Percentage", `${brokenPct}`],
        ["Chalky Grains", chalkyCnt.toString()],
        ["Chalkiness Percentage", `${chalkyPct}`],
        ["No. of Discolored Grains", discolorCnt.toString()],
        ["Discolored Grains %", `${discolorPct}`],
      ],
      theme: "grid",
      styles: {
        font: "helvetica",
        fontSize: 12,
        cellPadding: 10,
        halign: "left",
        valign: "middle",
      },
      columnStyles: {
        0: { fillColor: [242, 242, 242], cellWidth: leftColWidth, fontStyle: "bold" },
        1: { cellWidth: pageWidth - 80 - leftColWidth },
      },
      tableWidth: pageWidth - 80,
      margin: { left: 40, right: 40 },
      headStyles: { fillColor: [255, 255, 255] },
    });

    // Histogram of Rice Grain Length - draw on canvas first to ensure correct colors
    const pageHeight = doc.internal.pageSize.getHeight();
    const bottomMargin = 60;
    let chartStartY = doc.lastAutoTable.finalY + 28;
    const plannedHeight = 16 /*title*/ + 200 /*chart with axis labels*/ + 30 /*gap before table*/;
    if (chartStartY + plannedHeight > pageHeight - bottomMargin) {
      doc.addPage();
      chartStartY = 80;
    }

    doc.setFontSize(14);
    const title = "Histogram of Rice Grain Length";
    doc.text(title, 40, chartStartY);

    const chartX = 40;
    const chartY = chartStartY + 16;
    const chartWidth = pageWidth - 80;
    const chartHeight = 180;

    // Create canvas to draw histogram with correct green color, grid lines, and axis labels
    const bars = lengthHistogramData || [];
    if (bars.length > 0) {
      const canvas = document.createElement("canvas");
      const dpi = 2; // Higher resolution for better quality
      
      // Chart dimensions with padding for axes
      const paddingLeft = 50; // Space for Y-axis labels
      const paddingBottom = 40; // Space for X-axis labels and title
      const paddingTop = 10;
      const paddingRight = 10;
      const chartAreaWidth = chartWidth - paddingLeft - paddingRight;
      const chartAreaHeight = chartHeight - paddingTop - paddingBottom;
      const actualChartHeight = chartHeight + 20; // Extra space for axis labels
      
      canvas.width = chartWidth * dpi;
      canvas.height = actualChartHeight * dpi;
      const ctx = canvas.getContext("2d");
      
      // Scale context for higher DPI
      ctx.scale(dpi, dpi);
      
      // Draw white background
      ctx.fillStyle = "#FFFFFF";
      ctx.fillRect(0, 0, chartWidth, actualChartHeight);
      
      // Calculate max count for Y-axis
      const maxCount = Math.max(1, ...bars.map((b) => b.count));
      const roundedMax = Math.ceil(maxCount / 5) * 5; // Round up to nearest 5 for cleaner ticks
      
      // Chart area coordinates
      const chartAreaX = paddingLeft;
      const chartAreaY = paddingTop;
      
      // Draw chart border
      ctx.strokeStyle = "#D2D2D2";
      ctx.lineWidth = 1;
      ctx.strokeRect(chartAreaX, chartAreaY, chartAreaWidth, chartAreaHeight);
      
      // Draw grid lines (horizontal and vertical)
      ctx.strokeStyle = "#E5E5E5";
      ctx.lineWidth = 0.5;
      ctx.setLineDash([]);
      
      // Horizontal grid lines (Y-axis ticks)
      const numYTicks = 5;
      for (let i = 0; i <= numYTicks; i++) {
        const y = chartAreaY + (chartAreaHeight / numYTicks) * (numYTicks - i);
        ctx.beginPath();
        ctx.moveTo(chartAreaX, y);
        ctx.lineTo(chartAreaX + chartAreaWidth, y);
        ctx.stroke();
      }
      
      // Vertical grid lines (aligned with bars)
      const barGap = 20;
      const barWidth = (chartAreaWidth - barGap * (bars.length - 1)) / Math.max(1, bars.length);
      let cursorX = chartAreaX;
      bars.forEach((b, idx) => {
        const x = cursorX + barWidth / 2;
        ctx.beginPath();
        ctx.moveTo(x, chartAreaY);
        ctx.lineTo(x, chartAreaY + chartAreaHeight);
        ctx.stroke();
        cursorX += barWidth + barGap;
      });
      
      // Draw Y-axis labels (Grain Count)
      ctx.fillStyle = "#000000";
      ctx.font = "9px Helvetica";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      for (let i = 0; i <= numYTicks; i++) {
        const value = (roundedMax / numYTicks) * i;
        const y = chartAreaY + (chartAreaHeight / numYTicks) * (numYTicks - i);
        ctx.fillText(Math.round(value).toString(), chartAreaX - 8, y);
      }
      
      // Draw Y-axis label "Grain Count"
      ctx.save();
      ctx.translate(15, chartAreaY + chartAreaHeight / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = "center";
      ctx.font = "10px Helvetica";
      ctx.fillText("Grain Count", 0, 0);
      ctx.restore();
      
      // Draw bars in green
      cursorX = chartAreaX;
      ctx.fillStyle = "#62A040";

      bars.forEach((b) => {
        const barHeight = Math.max(2, (b.count / roundedMax) * chartAreaHeight);
        const barTop = chartAreaY + chartAreaHeight - barHeight;

        // Draw green bar
        ctx.fillRect(cursorX, barTop, barWidth, barHeight);

        // Draw X-axis label (length value)
        ctx.fillStyle = "#000000";
        ctx.font = "9px Helvetica";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillText(String(b.length), cursorX + barWidth / 2, chartAreaY + chartAreaHeight + 8);

        // Reset to green for next bar
        ctx.fillStyle = "#62A040";

        cursorX += barWidth + barGap;
      });
      
      // Draw X-axis label "Length (mm)"
      ctx.fillStyle = "#000000";
      ctx.font = "10px Helvetica";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText("Length (mm)", chartAreaX + chartAreaWidth / 2, actualChartHeight - 5);
      
      // Convert canvas to image and add to PDF
      try {
        const chartImageData = canvas.toDataURL("image/png");
        const chartImg = await loadImageElement(chartImageData);
        doc.addImage(chartImg, "PNG", chartX, chartY, chartWidth, actualChartHeight);
      } catch (err) {
        console.error("Failed to add histogram image:", err);
        // Fallback to drawing directly in PDF (simplified version)
        doc.setDrawColor(210, 210, 210);
        doc.setLineWidth(0.5);
        doc.setFillColor(255, 255, 255);
        doc.rect(chartX, chartY, chartWidth, chartHeight, "FD");
        
        const maxCount = Math.max(1, ...bars.map((b) => b.count));
        const barGap = 8;
        const barWidth = Math.max(4, Math.min(26, (chartWidth - barGap * (bars.length + 1)) / Math.max(1, bars.length)));
        let cursorX = chartX + barGap;
        bars.forEach((b) => {
          const h = Math.max(2, (b.count / maxCount) * (chartHeight - 20));
          doc.setFillColor(98, 160, 64);
          doc.rect(cursorX, chartY + chartHeight - h, barWidth, h, "F");
          doc.setTextColor(0, 0, 0);
          doc.text(String(b.length), cursorX + barWidth / 2, chartY + chartHeight + 12, { align: "center" });
          cursorX += barWidth + barGap;
        });
      }
    } else {
      // No data
      doc.setDrawColor(210, 210, 210);
      doc.setLineWidth(0.5);
      doc.setFillColor(255, 255, 255);
      doc.rect(chartX, chartY, chartWidth, chartHeight, "FD");
      doc.setFontSize(10);
      doc.setTextColor(100, 100, 100);
      doc.text("No data available", chartX + chartWidth / 2, chartY + chartHeight / 2, { align: "center" });
    }

    // Legend (top-right of chart, avoids title overlap)
    doc.setFillColor(98, 160, 64);
    const legendX = chartX + chartWidth - 120;
    const legendY = chartStartY - 6;
    doc.rect(legendX, legendY, 14, 10, "F");
    doc.setFontSize(10);
    doc.setTextColor(0, 0, 0);
    doc.text("Grains Count", legendX + 18, chartStartY + 2);

    // Rice Grain Length Table
    // Adjust Y position based on whether we have bars (with increased height for labels) or not
    const chartFinalHeight = bars.length > 0 ? chartHeight + 20 : chartHeight;
    let tableTitleY = chartY + chartFinalHeight + 30;
    // If the length table would overflow, move it to a new page
    const estimatedRows = Math.max(1, (lengthHistogramData || []).length);
    const estimatedTableHeight = 24 /*header*/ + estimatedRows * 20 + 24;
    if (tableTitleY + estimatedTableHeight > pageHeight - bottomMargin) {
      doc.addPage();
      tableTitleY = 80;
    }
    doc.setFontSize(14);
    doc.text("Rice Grain Length Table", 40, tableTitleY);

    // Build rows with cumulative percent
    let cumulative = 0;
    const lengthTableRows = bars.map((b, idx) => {
      const pct = total > 0 ? (b.count * 100) / total : 0;
      cumulative += pct;
      return [
        String(idx + 1),
        String(b.length),
        String(b.count),
        pct.toFixed(2),
        cumulative.toFixed(2),
      ];
    });

    autoTable(doc, {
      startY: tableTitleY + 8,
      head: [["S. No.", "Range", "No. of Grains", "Percentage", "Cumulative Percent"]],
      body: lengthTableRows,
      theme: "grid",
      styles: { font: "helvetica", fontSize: 11, cellPadding: 8 },
      headStyles: { fillColor: [230, 230, 230], textColor: 0, fontStyle: "bold" },
      margin: { left: 40, right: 40 },
      tableWidth: pageWidth - 80,
    });

    // Footer section - check if we need a new page
    let footerStartY = doc.lastAutoTable.finalY + 40;
    const footerHeight = 200; // Approximate height needed for footer
    if (footerStartY + footerHeight > pageHeight - 60) {
      doc.addPage();
      footerStartY = 60;
    }

    // Footer background (white rectangle with border)
    const footerBgY = footerStartY - 10;
    const footerBgHeight = 180;
    doc.setFillColor(255, 255, 255);
    doc.setDrawColor(200, 200, 200);
    doc.setLineWidth(0.5);
    doc.rect(40, footerBgY, pageWidth - 80, footerBgHeight, "FD");

    // Note text
    doc.setFontSize(10);
    doc.setTextColor(0, 0, 0);
    doc.setFont("helvetica", "normal");
    doc.text("Note: This report is generated by Agsure Grain Quality Analyzer.", 50, footerBgY + 20);

    // Company information (left side)
    const companyInfoX = 50;
    let companyInfoY = footerBgY + 40;
    
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text("Agsure Innovations Pvt Ltd", companyInfoX, companyInfoY);
    
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    companyInfoY += 15;
    doc.text("B-1/I-1, Second Floor, Phase -B, Mohan Cooperative Industrial Estate,", companyInfoX, companyInfoY);
    companyInfoY += 12;
    doc.text("Mathura Road, New Delhi, Delhi 110044", companyInfoX, companyInfoY);
    companyInfoY += 15;
    doc.text("Email: contact@agsure.in", companyInfoX, companyInfoY);
    companyInfoY += 12;
    doc.text("Contact Number: +919888355355", companyInfoX, companyInfoY);
    companyInfoY += 12;
    doc.setTextColor(0, 0, 255); // Blue for link
    doc.text("Website: www.agsure.in", companyInfoX, companyInfoY);
    doc.setTextColor(0, 0, 0); // Reset to black

    // QR code (right side) - use local image from assets
    const qrCodeSize = 60;
    const qrCodeX = pageWidth - 40 - qrCodeSize - 20;
    const qrCodeY = footerBgY + 35;
    
    try {
      // Use the local QR code image from assets
      const qrImg = await loadImageElement(logoqr);
      doc.addImage(qrImg, "PNG", qrCodeX, qrCodeY, qrCodeSize, qrCodeSize);
    } catch (err) {
      // Fallback: draw QR code placeholder if image load fails
      console.warn("QR code image load failed, using placeholder:", err);
      doc.setFillColor(255, 255, 255);
      doc.setDrawColor(180, 180, 180);
      doc.setLineWidth(1);
      doc.rect(qrCodeX, qrCodeY, qrCodeSize, qrCodeSize, "FD");
      doc.setFontSize(7);
      doc.setTextColor(150, 150, 150);
      doc.text("QR", qrCodeX + qrCodeSize / 2, qrCodeY + qrCodeSize / 2 - 3, { align: "center" });
      doc.text("Code", qrCodeX + qrCodeSize / 2, qrCodeY + qrCodeSize / 2 + 3, { align: "center" });
    }

    // Yellow banner at the bottom
    const yellowBannerY = footerBgY + footerBgHeight - 15;
    const yellowBannerHeight = 15;
    doc.setFillColor(255, 255, 0); // Yellow
    doc.rect(40, yellowBannerY, pageWidth - 80, yellowBannerHeight, "F");

    // Get timestamp from store for filename
    const storeState = useRiceStore.getState();
    const scanTimestamp = storeState.date;

    // Format timestamp for filename (YYYY-MM-DD_HH-MM-SS)
    let timestampForName = "report";
    if (scanTimestamp) {
      try {
        const date = new Date(scanTimestamp);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        timestampForName = `${year}-${month}-${day}_${hours}-${minutes}-${seconds}`;
      } catch (error) {
        console.warn("Failed to format timestamp for filename:", error);
        timestampForName = "report";
      }
    }

    doc.save(`${timestampForName}-quality-report.pdf`);
  } catch (err) {
    console.error("PDF export failed:", err);
    throw err;
  }
};

