import React from "react";
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

const Histogram = ({ data, onBarClick, selectedLengthRange }) => {
  return (
    <div className="result-detected-section">
      <div className="result-detected-header">
        <h3>Grain Length Distribution</h3>
        {selectedLengthRange && (
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
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="length"
              label={{
                value: "Length (mm)",
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
              formatter={(value) => [value, "Count"]}
              labelFormatter={(label) => `Length: ${label} mm`}
            />
            <Bar 
              dataKey="count" 
              onClick={onBarClick}
              style={{ cursor: 'pointer' }}
            >
              {data.map((entry, index) => {
                const isSelected = selectedLengthRange && 
                  entry.length >= selectedLengthRange.min && 
                  entry.length <= selectedLengthRange.max;
                return (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={isSelected ? "#4a7c25" : "#7bb241"} 
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