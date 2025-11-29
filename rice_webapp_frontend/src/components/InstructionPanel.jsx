import React from "react";
import "../styles/InstructionPanel.css";

const InstructionPanel = () => {
  return (
    <div className="instructions-panel">
      <div className="scan-instructions">
        <h4>Scanning Instructions</h4>
        <ul>
          <li>Clean scanner bed with microfiber cloth</li>
          <li>Place rice grains with at least 5mm spacing</li>
          <li>Ensure no grains are touching each other</li>
          <li>Close scanner lid completely before scanning</li>
          <li>
            <li>
              Click "Scan Rice Grains" - Image appears automatically!
            </li>
          </li>
          {/* <li>
            <strong>NO UI popups - Scans with fixed settings</strong>
          </li> */}
        </ul>
      </div>
    </div>
  );
};

export default InstructionPanel;
