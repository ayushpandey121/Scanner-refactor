import React, { useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const Histogram = ({ 
  lengthData, 
  grains, 
  onBarClick, 
  selectedLengthRange,
  selectedSubVarietyData 
}) => {
  const [viewMode, setViewMode] = useState('length'); // 'length' or 'quality'

  // Calculate quality distribution data
  const qualityData = useMemo(() => {
    if (!selectedSubVarietyData || !selectedSubVarietyData.qualities || !grains) {
      return [];
    }

    // Sort qualities by length in descending order
    const qualities = [...selectedSubVarietyData.qualities].sort((a, b) => 
      parseFloat(b.length) - parseFloat(a.length)
    );

    const distribution = [];

    qualities.forEach((quality, index) => {
      const minLength = parseFloat(quality.length);
      // For the highest quality (index 0), maxLength is Infinity
      // For others, maxLength is the previous quality's length
      const maxLength = index === 0 ? Infinity : parseFloat(qualities[index - 1].length);

      const count = grains.filter(grain => {
        const grainLength = grain.length || 0;
        return grainLength >= minLength && grainLength < maxLength;
      }).length;

      distribution.push({
        quality: quality.quality,
        count: count,
        minLength: minLength,
        maxLength: maxLength === Infinity ? '∞' : maxLength
      });
    });

    // Add "Other" category for grains below the lowest quality threshold
    const lowestThreshold = parseFloat(qualities[qualities.length - 1].length);
    const otherCount = grains.filter(grain => {
      const grainLength = grain.length || 0;
      return grainLength < lowestThreshold;
    }).length;

    if (otherCount > 0) {
      distribution.push({
        quality: 'Other',
        count: otherCount,
        minLength: 0,
        maxLength: lowestThreshold
      });
    }

    return distribution;
  }, [selectedSubVarietyData, grains]);

  const hasQualityData = selectedSubVarietyData && 
                         selectedSubVarietyData.qualities && 
                         selectedSubVarietyData.qualities.length > 0;

  const currentData = viewMode === 'length' ? lengthData : qualityData;

  return (
    <div className="result-detected-section">
      {/* Toggle Buttons */}
      <div style={{ 
        display: 'flex', 
        gap: '10px', 
        marginBottom: '15px',
        padding: '10px',
        background: '#f5f5f5',
        borderRadius: '8px'
      }}>
        <button
          onClick={() => setViewMode('length')}
          style={{
            flex: 1,
            padding: '12px 20px',
            borderRadius: '6px',
            border: viewMode === 'length' ? '2px solid #7bb241' : '1px solid #ddd',
            background: viewMode === 'length' ? '#7bb241' : '#fff',
            color: viewMode === 'length' ? '#fff' : '#333',
            cursor: 'pointer',
            fontWeight: viewMode === 'length' ? '600' : '400',
            fontSize: '14px',
            transition: 'all 0.3s ease',
            boxShadow: viewMode === 'length' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
          }}
        >
          📏 Length Distribution
        </button>
        
        {hasQualityData && (
          <button
            onClick={() => setViewMode('quality')}
            style={{
              flex: 1,
              padding: '12px 20px',
              borderRadius: '6px',
              border: viewMode === 'quality' ? '2px solid #7bb241' : '1px solid #ddd',
              background: viewMode === 'quality' ? '#7bb241' : '#fff',
              color: viewMode === 'quality' ? '#fff' : '#333',
              cursor: 'pointer',
              fontWeight: viewMode === 'quality' ? '600' : '400',
              fontSize: '14px',
              transition: 'all 0.3s ease',
              boxShadow: viewMode === 'quality' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
            }}
          >
            ⭐ {selectedSubVarietyData?.name || 'Quality'} 
          </button>
        )}
      </div>

      <div className="result-detected-header">
        <h3>
          {viewMode === 'length' 
            ? 'Grain Length Distribution' 
            : `${selectedSubVarietyData?.name || 'Quality'} `}
        </h3>
        
        {viewMode === 'length' && selectedLengthRange && (
          <span className="result-legend-item" style={{ marginLeft: '10px', fontSize: '14px' }}>
            <span className="result-dot" style={{ background: "#FF1493" }}></span>
            Filtered: {selectedLengthRange.min.toFixed(2)}mm - {selectedLengthRange.max.toFixed(2)}mm
          </span>
        )}
      </div>
      
      <div
        style={{
          width: "100%",
          height: "320px",
          marginTop: "18px",
          marginBottom: "10px",
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={currentData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={viewMode === 'length' ? 'length' : 'quality'}
              label={{
                value: viewMode === 'length' ? "Length (mm)" : "Quality Grade",
                position: "bottom",
                offset: -10,
              }}
            />
            <YAxis
              label={{
                value: "Count",
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  if (viewMode === 'quality') {
                    return (
                      <div style={{
                        background: '#fff',
                        border: '1px solid #ccc',
                        padding: '10px',
                        borderRadius: '4px',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                      }}>
                        <p style={{ margin: 0, fontWeight: 'bold', fontSize: '14px' }}>
                          {data.quality}
                        </p>
                        <p style={{ margin: '5px 0 0 0', fontSize: '13px' }}>
                          Count: <strong>{data.count}</strong>
                        </p>
                        <p style={{ margin: '5px 0 0 0', fontSize: '12px', color: '#666' }}>
                          Range: {data.minLength}mm - {data.maxLength}mm
                        </p>
                      </div>
                    );
                  }
                  return (
                    <div style={{
                      background: '#fff',
                      border: '1px solid #ccc',
                      padding: '10px',
                      borderRadius: '4px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                    }}>
                      <p style={{ margin: 0, fontSize: '13px' }}>
                        Length: <strong>{data.length} mm</strong>
                      </p>
                      <p style={{ margin: '5px 0 0 0', fontSize: '13px' }}>
                        Count: <strong>{data.count}</strong>
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar 
              dataKey="count" 
              onClick={viewMode === 'length' ? onBarClick : undefined}
              style={{ cursor: viewMode === 'length' ? 'pointer' : 'default' }}
            >
              {currentData.map((entry, index) => {
                let fillColor = "#7bb241";
                
                if (viewMode === 'length') {
                  const isSelected = selectedLengthRange && 
                    Math.abs(entry.length - selectedLengthRange.max) < 0.01;
                  fillColor = isSelected ? "#4a7c25" : "#7bb241";
                } else {
                  fillColor = "#7bb241";
                }
                
                return (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={fillColor} 
                  />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default Histogram;