import React, { useEffect, useState } from 'react';
import '../styles/Notification.css';

const UpdateNotification = () => {
  const [updateInfo, setUpdateInfo] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [updateReady, setUpdateReady] = useState(false);
  const [currentVersion, setCurrentVersion] = useState('');
  const [error, setError] = useState(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => {
      console.log('Internet connection restored');
      setIsOnline(true);
    };
    
    const handleOffline = () => {
      console.log('Internet connection lost');
      setIsOnline(false);
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    // Check if we're in Electron environment
    if (!window.electron?.update) {
      console.log('[UPDATE UI] Not in Electron environment');
      return;
    }

    // Don't check for updates if offline
    if (!isOnline) {
      console.log('Offline - skipping update check');
      return;
    }

    console.log('Initializing update notification component');

    // Get current version
    window.electron.update.getVersion().then(version => {
      setCurrentVersion(version);
      console.log('Current version:', version);
    }).catch(err => {
      console.error('Error getting version:', err);
    });

    // CRITICAL: Query for any existing update check result on mount
    const checkForExistingUpdate = async () => {
      try {
        console.log('Checking for existing update result...');
        const lastResult = await window.electron.update.getLastCheckResult();
        
        if (lastResult && lastResult.available && lastResult.info) {
          console.log(' Found existing update:', lastResult.info.version);
          setUpdateInfo(lastResult.info);
        } else {
          console.log('No existing update found');
        }
      } catch (err) {
        console.error('Error checking existing update:', err);
      }
    };

    checkForExistingUpdate();

    // Set up update listeners
    window.electron.update.onUpdateAvailable((info) => {
      console.log('[UPDATE UI] ✅ Update available event received:', info.version);
      setUpdateInfo(info);
      setError(null);
    });

    window.electron.update.onUpdateNotAvailable((info) => {
      console.log('[UPDATE UI] ℹ️ No update available');
    });

    window.electron.update.onDownloadProgress((progress) => {
      console.log('[UPDATE UI] Download progress:', Math.round(progress.percent) + '%');
      setDownloading(true);
      setDownloadProgress(Math.round(progress.percent));
    });

    window.electron.update.onUpdateDownloaded((info) => {
      console.log('[UPDATE UI] ✅ Update downloaded:', info.version);
      setDownloading(false);
      setDownloadProgress(100);
      setUpdateReady(true);
    });

    window.electron.update.onUpdateError((error) => {
      console.error('[UPDATE UI] ❌ Update error:', error.error);
      
      // Don't show network errors when offline
      if (!isOnline) {
        console.log('[UPDATE UI] Suppressing update error - device is offline');
        return;
      }
      
      setError(error.error);
      setDownloading(false);
    });

    // Cleanup listeners on unmount
    return () => {
      console.log('[UPDATE UI] Cleaning up listeners');
      window.electron.update.removeUpdateListeners();
    };
  }, [isOnline]);

  const handleDownload = async () => {
    if (!isOnline) {
      alert('Cannot download updates while offline. Please connect to the internet.');
      return;
    }

    try {
      console.log('[UPDATE UI] User clicked download');
      setError(null);
      await window.electron.update.downloadUpdate();
    } catch (err) {
      console.error('[UPDATE UI] Download failed:', err);
      
      // Check if it's a network error
      if (err.message && err.message.toLowerCase().includes('network')) {
        setError('Network error. Please check your internet connection.');
      } else {
        setError(err.message);
      }
    }
  };

  const handleInstall = () => {
    console.log('[UPDATE UI] User clicked install');
    window.electron.update.installUpdate();
  };

  const handleDismiss = () => {
    console.log('[UPDATE UI] User dismissed notification');
    setUpdateInfo(null);
    setUpdateReady(false);
    setError(null);
  };

  // Don't render anything if offline
  if (!isOnline) {
    return null;
  }

  // Don't render anything if no update
  if (!updateInfo && !updateReady && !error) {
    return null;
  }

  console.log('[UPDATE UI] Rendering notification');

  return (
    <div className="update-notification-container">
      {/* Header */}
      <div className="update-notification-header">
        <div className="update-notification-header-content">
          <svg className="update-notification-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <h3 className="update-notification-title">
            {updateReady ? 'Update Ready!' : 'Update Available'}
          </h3>
        </div>
        <button
          onClick={handleDismiss}
          className="update-notification-close-btn"
          aria-label="Close notification"
        >
          <svg className="update-notification-close-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="update-notification-content">
        {/* Error Message */}
        {error && (
          <div className="update-notification-error">
            <div className="update-notification-error-title">Update Error</div>
            <div>{error}</div>
          </div>
        )}

        {/* Version Information */}
        {updateInfo && (
          <div className="update-notification-version-info">
            <div className="update-notification-version-row">
              <span className="update-notification-version-label">Current Version:</span>
              <span className="update-notification-version-current">{currentVersion}</span>
            </div>
            <div className="update-notification-version-row">
              <span className="update-notification-version-label">New Version:</span>
              <span className="update-notification-version-new">{updateInfo.version}</span>
            </div>
            
            {/* Release Notes */}
            {updateInfo.releaseNotes && (
              <div className="update-notification-release-notes">
                <div className="update-notification-release-notes-title">What's New:</div>
                <div className="update-notification-release-notes-content">
                  {updateInfo.releaseNotes}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Download Progress */}
        {downloading && (
          <div className="update-notification-download-progress">
            <div className="update-notification-progress-header">
              <span className="update-notification-progress-label">Downloading...</span>
              <span className="update-notification-progress-percent">{downloadProgress}%</span>
            </div>
            <div className="update-notification-progress-bar-container">
              <div
                className="update-notification-progress-bar"
                style={{ width: `${downloadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Success Message */}
        {updateReady && (
          <div className="update-notification-success">
            <div className="update-notification-success-title">✓ Update downloaded successfully!</div>
            <div>Click "Install Now" to restart and update.</div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="update-notification-actions">
          {!downloading && !updateReady && (
            <>
              <button
                onClick={handleDownload}
                className="update-notification-btn update-notification-btn-primary"
                disabled={!isOnline}
              >
                Download Update
              </button>
              <button
                onClick={handleDismiss}
                className="update-notification-btn update-notification-btn-secondary"
              >
                Later
              </button>
            </>
          )}

          {updateReady && (
            <>
              <button
                onClick={handleInstall}
                className="update-notification-btn update-notification-btn-success"
              >
                Install Now
              </button>
              <button
                onClick={handleDismiss}
                className="update-notification-btn update-notification-btn-secondary"
              >
                Later
              </button>
            </>
          )}

          {downloading && (
            <button
              disabled
              className="update-notification-btn update-notification-btn-disabled"
            >
              Downloading...
            </button>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="update-notification-footer">
        {isOnline 
          ? 'Updates are checked automatically when online' 
          : 'Connect to the internet to check for updates'}
      </div>
    </div>
  );
};

export default UpdateNotification;