const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  isElectron: true,
  
  // Legacy license API (keep for compatibility)
  license: {
    getStatus: () => ipcRenderer.invoke('license:getStatus'),
    getHardwareInfo: () => ipcRenderer.invoke('license:getDeviceId'),
    activateOnline: (name, productKey, activationBaseUrl) => ipcRenderer.invoke('license:activateOnline', { name, productKey, activationBaseUrl }),
    importLicense: (licenseData) => ipcRenderer.invoke('license:importLicense', licenseData),
    importLicenseFile: (filePath) => ipcRenderer.invoke('license:importLicenseFile', filePath),
    showOpenDialog: () => ipcRenderer.invoke('dialog:showOpenDialog'),
  },
  
  // Hardware API for activation
  hardware: {
    getInfo: () => ipcRenderer.invoke('hardware:getInfo'),
    getId: () => ipcRenderer.invoke('hardware:getId'),
  },
  
  // Auto-Update API
  update: {
    // Check for updates
    checkForUpdates: () => ipcRenderer.invoke('update:check'),
    
    // Download update
    downloadUpdate: () => ipcRenderer.invoke('update:download'),
    
    // Install update and restart
    installUpdate: () => ipcRenderer.invoke('update:install'),
    
    // Get current app version
    getVersion: () => ipcRenderer.invoke('update:getVersion'),
    
    // NEW: Get the last check result (useful when React component mounts)
    getLastCheckResult: () => ipcRenderer.invoke('update:getLastCheckResult'),
    
    // Listen for update events
    onUpdateAvailable: (callback) => {
      ipcRenderer.on('update-available', (event, info) => callback(info));
    },
    
    onUpdateNotAvailable: (callback) => {
      ipcRenderer.on('update-status', (event, info) => {
        if (info.status === 'not-available') {
          callback(info);
        }
      });
    },
    
    onDownloadProgress: (callback) => {
      ipcRenderer.on('download-progress', (event, progress) => callback(progress));
    },
    
    onUpdateDownloaded: (callback) => {
      ipcRenderer.on('update-downloaded', (event, info) => callback(info));
    },
    
    onUpdateError: (callback) => {
      ipcRenderer.on('update-error', (event, error) => callback(error));
    },
    
    onCheckingForUpdate: (callback) => {
      ipcRenderer.on('update-status', (event, info) => {
        if (info.status === 'checking') {
          callback(info);
        }
      });
    },
    
    // Remove listeners
    removeUpdateListeners: () => {
      ipcRenderer.removeAllListeners('update-available');
      ipcRenderer.removeAllListeners('update-status');
      ipcRenderer.removeAllListeners('download-progress');
      ipcRenderer.removeAllListeners('update-downloaded');
      ipcRenderer.removeAllListeners('update-error');
    }
  }
});

console.log('Preload script loaded - Electron APIs exposed');