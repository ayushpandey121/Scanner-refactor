/**
 * Generate a unique hardware ID for Electron app
 * Uses native hardware identifiers via Electron IPC
 * NO browser fingerprinting - Electron only
 */

async function generateHardwareId() {
  try {
    // Check if running in Electron
    if (window.electron && window.electron.isElectron) {
      console.log('Running in Electron - using native hardware detection');
      
      // Try new hardware API first
      if (window.electron.hardware && window.electron.hardware.getId) {
        const hardwareId = await window.electron.hardware.getId();
        
        if (hardwareId && hardwareId.length >= 16) {
          console.log('Hardware ID from Electron (new API):', hardwareId);
          return hardwareId;
        }
      }
      
      // Fallback to legacy license API
      if (window.electron.license && window.electron.license.getHardwareInfo) {
        console.log('Using legacy hardware API');
        const hardwareInfo = await window.electron.license.getHardwareInfo();
        
        if (hardwareInfo && hardwareInfo.fpHash) {
          const hardwareId = hardwareInfo.fpHash.substring(0, 16).toUpperCase();
          console.log('Hardware ID from Electron (legacy API):', hardwareId);
          return hardwareId;
        }
      }
      
      console.error('No hardware API available');
      throw new Error('Hardware ID API not available');
      
    } else {
      // Not in Electron - this should not happen in production
      console.error('NOT running in Electron environment!');
      console.error('window.electron:', window.electron);
      throw new Error('Application must be run in Electron environment');
    }

  } catch (error) {
    console.error('CRITICAL: Failed to generate hardware ID:', error);
    
    // Show detailed error to user for debugging
    alert(`Failed to generate hardware ID: ${error.message}\n\nPlease restart the application.`);
    
    throw error; // Don't fallback - this is a critical error
  }
}

/**
 * Get full hardware information (for debugging)
 */
async function getHardwareInfo() {
  try {
    if (window.electron && window.electron.isElectron) {
      // Try new API
      if (window.electron.hardware && window.electron.hardware.getInfo) {
        return await window.electron.hardware.getInfo();
      }
      // Fallback to legacy API
      if (window.electron.license && window.electron.license.getHardwareInfo) {
        return await window.electron.license.getHardwareInfo();
      }
    }
    throw new Error('Not in Electron environment');
  } catch (error) {
    console.error('Failed to get hardware info:', error);
    return null;
  }
}

export { generateHardwareId, getHardwareInfo };