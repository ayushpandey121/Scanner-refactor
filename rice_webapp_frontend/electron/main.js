const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const { spawn, execSync } = require('child_process');
const waitOn = require('wait-on');
const fs = require('fs');
const crypto = require('crypto');

let mainWindow;
let backendProcess;
let scannerProcess;

// Determine if we're in development or production
const isDev = process.env.NODE_ENV === 'development';
const isPackaged = app.isPackaged;

// Configure auto-updater
autoUpdater.autoDownload = false;
autoUpdater.autoInstallOnAppQuit = true;

// IMPORTANT: Store update check result globally
let lastUpdateCheckResult = null;
let isCheckingForUpdate = false;

// Auto-updater event handlers
autoUpdater.on('checking-for-update', () => {
  console.log('[UPDATE] Checking for updates...');
  isCheckingForUpdate = true;
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('update-status', { 
      status: 'checking',
      message: 'Checking for updates...' 
    });
  }
});

autoUpdater.on('update-available', (info) => {
  console.log('[UPDATE] ✅ Update available:', info.version);
  console.log('[UPDATE] Release notes:', info.releaseNotes);
  console.log('[UPDATE] Release date:', info.releaseDate);
  
  isCheckingForUpdate = false;
  lastUpdateCheckResult = {
    available: true,
    info: info
  };
  
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('update-available', {
      version: info.version,
      releaseNotes: info.releaseNotes,
      releaseDate: info.releaseDate
    });
  }
});

autoUpdater.on('update-not-available', (info) => {
  console.log('[UPDATE] ℹ️ No update available. Current version:', info.version);
  
  isCheckingForUpdate = false;
  lastUpdateCheckResult = {
    available: false,
    currentVersion: info.version
  };
  
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('update-status', { 
      status: 'not-available',
      message: 'You are using the latest version.',
      currentVersion: info.version
    });
  }
});

autoUpdater.on('error', (err) => {
  console.error('[UPDATE] ❌ Error:', err);
  isCheckingForUpdate = false;
  
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('update-error', { 
      error: err.message 
    });
  }
});

autoUpdater.on('download-progress', (progressObj) => {
  console.log(`[UPDATE] Download progress: ${Math.round(progressObj.percent)}%`);
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('download-progress', {
      percent: progressObj.percent,
      transferred: progressObj.transferred,
      total: progressObj.total,
      bytesPerSecond: progressObj.bytesPerSecond
    });
  }
});

autoUpdater.on('update-downloaded', (info) => {
  console.log('[UPDATE] ✅ Update downloaded:', info.version);
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('update-downloaded', {
      version: info.version
    });
  }
});

// Robust update check function
async function checkForUpdates() {
  if (!isPackaged) {
    console.log('[UPDATE] Skipping - not in production build');
    return { available: false, message: 'Development mode' };
  }

  if (isCheckingForUpdate) {
    console.log('[UPDATE] Check already in progress, skipping...');
    return { available: false, message: 'Check in progress' };
  }

  try {
    console.log('[UPDATE] 🚀 Starting update check...');
    console.log('[UPDATE] Current version:', app.getVersion());
    
    const result = await autoUpdater.checkForUpdates();
    
    console.log('[UPDATE] Check completed');
    console.log('[UPDATE] Latest version from server:', result.updateInfo.version);
    console.log('[UPDATE] Update available:', result.updateInfo.version !== app.getVersion());
    
    return { 
      available: result.updateInfo.version !== app.getVersion(),
      updateInfo: result.updateInfo 
    };
  } catch (error) {
    console.error('[UPDATE] Check failed:', error.message);
    throw error;
  }
}

// ---------- Hardware Fingerprint (UUID + Baseboard Serial + MAC) ----------
function getHardwareInfo() {
  let uuid = '';
  let baseboard = '';
  let mac = '';
  
  try {
    const raw = execSync('wmic csproduct get uuid').toString();
    uuid = raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean)[1] || '';
  } catch (e) {
    console.warn('Failed to get UUID:', e.message);
  }
  
  try {
    const raw = execSync('wmic baseboard get serialnumber').toString();
    baseboard = raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean)[1] || '';
  } catch (e) {
    console.warn('Failed to get baseboard:', e.message);
  }
  
  try {
    const raw = execSync('wmic nic where NetEnabled=true get MACAddress').toString();
    const lines = raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    mac = lines[1] || '';
  } catch (e) {
    console.warn('Failed to get MAC:', e.message);
  }
  
  const fingerprint = `${uuid}|${baseboard}|${mac}`;
  const fpHash = crypto.createHash('sha256').update(fingerprint).digest('hex');
  
  return { uuid, baseboard, mac, fingerprint, fpHash };
}

function getBackendPath() {
  if (isPackaged) {
    if (process.platform === 'win32') {
      return path.join(process.resourcesPath, 'backend', 'app.exe');
    } else if (process.platform === 'darwin') {
      return path.join(process.resourcesPath, 'backend', 'app');
    } else {
      return path.join(process.resourcesPath, 'backend', 'app');
    }
  } else {
    return 'python';
  }
}

function getBackendArgs() {
  if (isPackaged) {
    return [];
  } else {
    return [path.join(__dirname, '../../rice_webapp_backend/app.py')];
  }
}

function getBackendDataDir() {
  const dir = path.join(app.getPath('userData'), 'backend-data');
  try {
    fs.mkdirSync(dir, { recursive: true });
  } catch (e) {
    console.warn('Failed to create backend data dir:', dir, e.message);
  }
  return dir;
}

// ---------- PROPER PROCESS CLEANUP FUNCTION ----------
function killProcessTree(pid) {
  if (!pid) return;
  
  try {
    if (process.platform === 'win32') {
      execSync(`taskkill /pid ${pid} /T /F`, { stdio: 'ignore' });
      console.log(`Killed process tree for PID ${pid}`);
    } else {
      process.kill(pid, 'SIGTERM');
      console.log(`Sent SIGTERM to PID ${pid}`);
    }
  } catch (e) {
    console.warn(`Failed to kill process ${pid}:`, e.message);
    try {
      process.kill(pid, 'SIGKILL');
    } catch (err) {
      console.warn(`Failed to SIGKILL process ${pid}:`, err.message);
    }
  }
}

function cleanupProcesses() {
  console.log('Cleaning up backend and scanner processes...');
  
  if (backendProcess && backendProcess.pid) {
    killProcessTree(backendProcess.pid);
    backendProcess = null;
  }
  
  if (scannerProcess && scannerProcess.pid) {
    killProcessTree(scannerProcess.pid);
    scannerProcess = null;
  }
}

async function startBackend() {
  return new Promise((resolve, reject) => {
    const backendPath = getBackendPath();
    const backendArgs = getBackendArgs();
    const backendDataDir = getBackendDataDir();

    console.log('Starting backend:', backendPath, backendArgs);
    console.log('Backend data directory:', backendDataDir);

    backendProcess = spawn(backendPath, backendArgs, {
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        AGSURE_DATA_DIR: backendDataDir,
      },
      cwd: isPackaged 
        ? path.join(process.resourcesPath, 'backend')
        : path.join(__dirname, '../../rice_webapp_backend'),
      detached: false
    });

    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data}`);
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`Backend Error: ${data}`);
    });

    backendProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
      backendProcess = null;
    });

    backendProcess.on('error', (err) => {
      console.error('Backend process error:', err);
      backendProcess = null;
    });

    setTimeout(() => resolve(), 3000);
  });
}

function getScannerEntrypoint() {
  if (isPackaged) {
    const scannerDir = path.join(process.resourcesPath, 'scanner', 'scanner_service');
    const exePath = path.join(scannerDir, 'scanner_service.exe');
    const pyPath = path.join(process.resourcesPath, 'scanner_service.py');

    if (fs.existsSync(exePath)) {
      return { type: 'exe', path: exePath };
    }
    if (fs.existsSync(pyPath)) {
      return { type: 'py', path: pyPath };
    }
    return null;
  }
  return { type: 'py', path: path.join(__dirname, '..', 'scanner_service.py') };
}

async function startScannerService() {
  return new Promise((resolve) => {
    const entry = getScannerEntrypoint();
    if (!entry) {
      console.warn('Scanner service not bundled. Skipping auto-start.');
      return resolve();
    }
    const pythonExe = process.platform === 'win32' ? 'python' : 'python3';

    let command;
    let args;
    let cwd;

    if (entry.type === 'exe') {
      command = entry.path;
      args = [];
      cwd = path.dirname(entry.path);
      console.log('Starting scanner EXE:', command);
    } else {
      command = pythonExe;
      args = [entry.path];
      cwd = path.dirname(entry.path);
      console.log('Starting scanner PY:', command, args.join(' '));
    }

    try {
      scannerProcess = spawn(command, args, {
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
        cwd,
        detached: false
      });
    } catch (err) {
      console.warn('Failed to start scanner service:', err.message);
      return resolve();
    }

    scannerProcess.stdout.on('data', (data) => {
      console.log(`Scanner: ${data}`);
    });

    scannerProcess.stderr.on('data', (data) => {
      console.error(`Scanner Error: ${data}`);
    });

    scannerProcess.on('error', (err) => {
      console.warn('Scanner process error:', err.message);
      scannerProcess = null;
      resolve();
    });

    scannerProcess.on('close', (code) => {
      console.log(`Scanner service exited with code ${code}`);
      scannerProcess = null;
    });

    setTimeout(() => resolve(), 1500);
  });
}

async function createWindow() {
  try {
    await startBackend();
    
    try {
      await startScannerService();
      await waitOn({
        resources: ['http://127.0.0.1:8080/api/scanner/status'],
        timeout: 15000,
        interval: 1000,
        validateStatus: (status) => status === 200
      });
      console.log('Scanner service is ready!');
    } catch (e) {
      console.warn('Scanner service did not start automatically.', e?.message || e);
    }
    
    await waitOn({
      resources: ['http://localhost:5000/health'],
      timeout: 30000,
      interval: 1000,
    });

    console.log('Backend is ready!');
  } catch (error) {
    console.error('Failed to start backend:', error);
    dialog.showErrorBox(
      'Backend Error',
      'Failed to start the application backend. Please try again.'
    );
    app.quit();
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    icon: path.join(__dirname, '../public/icon.png'),
  });

  if (isDev && !isPackaged) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // CRITICAL: Multiple update checks with retry logic
  mainWindow.webContents.once('did-finish-load', () => {
    console.log('[UPDATE] Window loaded - initiating update checks');
    
    // First check after 2 seconds
    setTimeout(() => {
      console.log('[UPDATE] Running first check (2s delay)');
      checkForUpdates().catch(err => {
        console.error('[UPDATE] First check failed:', err.message);
      });
    }, 2000);
    
    // Second check after 5 seconds (in case first fails)
    setTimeout(() => {
      console.log('[UPDATE] Running second check (5s delay)');
      checkForUpdates().catch(err => {
        console.error('[UPDATE] Second check failed:', err.message);
      });
    }, 5000);
    
    // Third check after 10 seconds (final retry)
    setTimeout(() => {
      console.log('[UPDATE] Running third check (10s delay)');
      checkForUpdates().catch(err => {
        console.error('[UPDATE] Third check failed:', err.message);
      });
    }, 10000);
  });
}

app.whenReady().then(() => {
  cleanupTempFolders();
  createWindow();
});

app.on('window-all-closed', () => {
  cleanupProcesses();
  cleanupTempFolders();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', (event) => {
  console.log('App is quitting, cleaning up processes...');
  cleanupProcesses();
  cleanupTempFolders();
});

// ---------- CLEANUP TEMP FOLDERS ----------
function cleanupTempFolders() {
  try {
    const tempDir = app.getPath('temp');
    console.log('Cleaning up temp folders in:', tempDir);
    
    const items = fs.readdirSync(tempDir);
    
    items.forEach(item => {
      if (item.startsWith('_MEI')) {
        const fullPath = path.join(tempDir, item);
        try {
          const stats = fs.statSync(fullPath);
          if (stats.isDirectory()) {
            console.log('Deleting temp folder:', item);
            fs.rmSync(fullPath, { recursive: true, force: true });
          }
        } catch (err) {
          console.warn(`Failed to delete ${item}:`, err.message);
        }
      }
    });
  } catch (err) {
    console.warn('Error cleaning temp folders:', err.message);
  }
}

process.on('exit', () => {
  cleanupProcesses();
  cleanupTempFolders();
});

process.on('SIGINT', () => {
  console.log('Received SIGINT, cleaning up...');
  cleanupProcesses();
  cleanupTempFolders();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM, cleaning up...');
  cleanupProcesses();
  cleanupTempFolders();
  process.exit(0);
});

// ============ IPC HANDLERS FOR HARDWARE ID ============

ipcMain.handle('hardware:getInfo', () => {
  const hwInfo = getHardwareInfo();
  console.log('Hardware info requested:', {
    uuid: hwInfo.uuid,
    baseboard: hwInfo.baseboard ? '***' : 'none',
    mac: hwInfo.mac ? '***' : 'none',
    fpHash: hwInfo.fpHash.substring(0, 16)
  });
  return hwInfo;
});

ipcMain.handle('hardware:getId', () => {
  const hwInfo = getHardwareInfo();
  return hwInfo.fpHash.substring(0, 16).toUpperCase();
});

// ============ IPC HANDLERS FOR AUTO-UPDATE ============

ipcMain.handle('update:check', async () => {
  console.log('[UPDATE] Manual check requested via IPC');
  return await checkForUpdates();
});

ipcMain.handle('update:download', async () => {
  if (!isPackaged || isDev) {
    throw new Error('Updates only available in production');
  }
  
  try {
    console.log('[UPDATE] Starting download...');
    await autoUpdater.downloadUpdate();
    return { success: true };
  } catch (error) {
    console.error('[UPDATE] Download error:', error);
    throw error;
  }
});

ipcMain.handle('update:install', () => {
  if (!isPackaged || isDev) {
    throw new Error('Updates only available in production');
  }
  
  console.log('[UPDATE] Installing update and restarting...');
  autoUpdater.quitAndInstall(false, true);
});

ipcMain.handle('update:getVersion', () => {
  return app.getVersion();
});

// NEW: Get last check result (for React component to query on mount)
ipcMain.handle('update:getLastCheckResult', () => {
  console.log('[UPDATE] Last check result requested:', lastUpdateCheckResult);
  return lastUpdateCheckResult;
});