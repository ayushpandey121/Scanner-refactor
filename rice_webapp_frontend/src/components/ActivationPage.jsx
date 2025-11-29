import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { generateHardwareId } from '../utils/hardwareId';
import '../styles/ActivationPage.css';

const ActivationPage = () => {
  const [key, setKey] = useState('');
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState('');
  const navigate = useNavigate();

  const downloadModelFile = async (deviceId, modelType, fileName) => {
    const response = await fetch(`http://43.205.7.195:8083/download-model/${deviceId}/${modelType}`);
    
    if (!response.ok) {
      throw new Error(`Failed to download ${modelType} model`);
    }
    
    const blob = await response.blob();
    const arrayBuffer = await blob.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    
    // Save to local backend's file system
    const saveResponse = await fetch('http://localhost:5000/api/save-model', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        fileName: fileName,
        data: Array.from(uint8Array)
      })
    });
    
    if (!saveResponse.ok) {
      throw new Error(`Failed to save ${modelType} model locally`);
    }
    
    return await saveResponse.json();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setProgress('Generating hardware ID...');

    try {
      // Step 1: Generate hardware ID
      const hardwareId = await generateHardwareId();
      console.log('Generated Hardware ID:', hardwareId);

      // Step 2: Activate with remote server (which updates S3 with loggedIn: true)
      setProgress('Validating activation key...');
      const activationUrl = 'http://43.205.7.195:8083/activate';
      const response = await fetch(activationUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          key, 
          username,
          hardwareId
        }),
      });

      const data = await response.json();

      if (!data.success) {
        // Check if it's an expiration error (HTTP 403)
        if (response.status === 403) {
          setError('Your activation key has expired');
        } else {
          setError(data.message || 'Activation failed');
        }
        setLoading(false);
        return;
      }

      console.log('✅ Activation validated by EC2 and S3 updated with loggedIn: true');
      
      // Log expiration date if available
      // if (data.expirationDate) {
      //   console.log('Expiration date:', data.expirationDate);
      // }

      // Check if modelFiles exist and have required keys
      if (!data.modelFiles || !data.modelFiles.sella || !data.modelFiles.nonSella) {
        setError('Activation data missing required model files');
        setLoading(false);
        return;
      }

      // Step 3: Download model files in parallel
      setProgress('Downloading model files...');
      const { deviceId, modelFiles } = data;
      
      await Promise.all([
        downloadModelFile(deviceId, 'sella', modelFiles.sella)
          .then(() => setProgress('Downloaded sella model...')),
        downloadModelFile(deviceId, 'non-sella', modelFiles.nonSella)
          .then(() => setProgress('Downloaded non-sella model...'))
      ]);

      console.log('✅ Model files downloaded');

      // Step 4: Cache data in localStorage (for quick reference only - NOT source of truth)
      localStorage.setItem('isActivated', 'true');
      localStorage.setItem('hardwareId', hardwareId);
      localStorage.setItem('deviceId', deviceId);
      localStorage.setItem('username', username);
      
      // // Store expiration date if available
      // if (data.expirationDate) {
      //   localStorage.setItem('expirationDate', data.expirationDate);
      // }
      
      // console.log('✅ Cached to localStorage (S3 is source of truth)');

      setProgress('Activation complete!');
      
      // Reload to trigger secure S3 check
      setTimeout(() => {
        window.location.reload();
      }, 500);

    } catch (err) {
      console.error('Activation error:', err);
      setError(err.message || 'Network error. Please try again.');
      
      // Clear any partial localStorage data on error
      localStorage.removeItem('isActivated');
      localStorage.removeItem('hardwareId');
      localStorage.removeItem('deviceId');
      localStorage.removeItem('username');
      // localStorage.removeItem('expirationDate');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="activation-container">
      <div className="activation-form-wrapper">
        <h2>Activate Your Account</h2>
        <form onSubmit={handleSubmit} className="activation-form">
          <div className="form-group">
            <label htmlFor="key">Activation Key</label>
            <input
              type="text"
              id="key"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              required
              placeholder="Enter your activation key"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Enter your username"
              disabled={loading}
            />
          </div>
          {progress && !error && (
            <div className="progress-message">{progress}</div>
          )}
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading} className="activate-btn">
            {loading ? 'Activating...' : 'Activate'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ActivationPage;