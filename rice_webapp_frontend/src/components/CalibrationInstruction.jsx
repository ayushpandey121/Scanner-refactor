import React, { useState } from 'react';
import { MdTune, MdCheckCircle, MdWarning } from 'react-icons/md';
import '../styles/CalibrationInstruction.css';

const CalibrationInstruction = () => {
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [calibrationComplete, setCalibrationComplete] = useState(false);

  const handleCalibrate = async () => {
    setIsCalibrating(true);

    // Simulate calibration process
    setTimeout(() => {
      setIsCalibrating(false);
      setCalibrationComplete(true);

      // Reset after showing success
      setTimeout(() => {
        setCalibrationComplete(false);
      }, 3000);
    }, 2000);
  };

  return (
    <div className="calibration-container">
      <div className="calibration-header">
        <MdTune className="calibration-header-icon" />
        <h2 className="calibration-title">Scanner Calibration Instructions</h2>
      </div>

      <div className="calibration-content">
        <div className="instruction-section">
          <h3 className="instruction-title">Preparation Steps:</h3>
          <ul className="instruction-list">
            <li className="instruction-item">
              <MdCheckCircle className="instruction-icon" />
              <span>Clean the scanner bed and glass sheet with a microfiber cloth to remove dust, fingerprints, or any debris.</span>
            </li>
            <li className="instruction-item">
              <MdCheckCircle className="instruction-icon" />
              <span>Ensure the scanner lid is closed completely before starting calibration.</span>
            </li>
            <li className="instruction-item">
              <MdCheckCircle className="instruction-icon" />
              <span>Make sure the scanner is powered on and connected to the computer.</span>
            </li>
            <li className="instruction-item">
              <MdCheckCircle className="instruction-icon" />
              <span>Remove any objects from the scanner bed - it should be completely empty.</span>
            </li>
          </ul>
        </div>

        <div className="instruction-section">
          <h3 className="instruction-title">Calibration Process:</h3>
          <ol className="instruction-list numbered">
            <li className="instruction-item">
              <span>Click the "Calibrate" button below to start the calibration process.</span>
            </li>
            <li className="instruction-item">
              <span>The scanner will perform automatic calibration (this may take a few seconds).</span>
            </li>
            <li className="instruction-item">
              <span>Wait for the calibration to complete - do not open the scanner lid during this process.</span>
            </li>
            <li className="instruction-item">
              <span>Once calibration is complete, you will see a success message.</span>
            </li>
          </ol>
        </div>

        <div className="warning-section">
          <MdWarning className="warning-icon" />
          <div className="warning-content">
            <h4 className="warning-title">Important Notes:</h4>
            <ul className="warning-list">
              <li>Do not place any grain or objects on the scanner bed during calibration.</li>
              <li>Avoid touching the scanner glass during the calibration process.</li>
              <li>If calibration fails, clean the scanner and try again.</li>
            </ul>
          </div>
        </div>

        <div className="calibration-action">
          <button
            className={`calibrate-btn ${isCalibrating ? 'calibrating' : ''} ${calibrationComplete ? 'complete' : ''}`}
            onClick={handleCalibrate}
            disabled={isCalibrating}
          >
            {isCalibrating ? (
              <>
                <div className="spinner"></div>
                Calibrating...
              </>
            ) : calibrationComplete ? (
              <>
                <MdCheckCircle className="success-icon" />
                Calibration Complete!
              </>
            ) : (
              <>
                <MdTune className="btn-icon" />
                Calibrate Scanner
              </>
            )}
          </button>
        </div>

        {calibrationComplete && (
          <div className="success-message">
            <MdCheckCircle className="success-icon-large" />
            <p>Scanner calibration completed successfully! You can now proceed with scanning.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CalibrationInstruction;
