"""
Hardware ID generation utilities
Generates consistent hardware fingerprints based on:
- System UUID (WMIC csproduct) - More stable than CPU ProcessorId
- Motherboard Serial Number
- MAC Address

This matches the Electron main.js implementation exactly
"""

import hashlib
import platform
import subprocess
import logging
import uuid as uuid_lib

logger = logging.getLogger(__name__)


def get_hardware_id():
    """
    Generate hardware ID based on System UUID, Motherboard Serial, and MAC address
    Returns a consistent 16-character uppercase hex string
    
    This MUST match the algorithm in Electron's main.js getHardwareInfo()
    """
    try:
        hw_info = get_hardware_info()
        # Create fingerprint string: "UUID|Baseboard|MAC"
        fingerprint = f"{hw_info['uuid']}|{hw_info['baseboard']}|{hw_info['mac']}"
        
        # SHA-256 hash of the fingerprint
        fp_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
        
        # Return first 16 characters in uppercase (matching frontend)
        return fp_hash[:16].upper()
    
    except Exception as e:
        logger.error(f"Error generating hardware ID: {e}")
        # Fallback to machine name + system info
        fallback = f"{platform.node()}-{platform.system()}-{str(uuid_lib.getnode())}"
        return hashlib.sha256(fallback.encode()).hexdigest()[:16].upper()


def get_hardware_info():
    """
    Get detailed hardware information
    Returns dict with uuid, baseboard, mac, fingerprint, and fpHash
    """
    uuid = ''
    baseboard = ''
    mac = ''
    
    system = platform.system()
    
    if system == 'Windows':
        uuid = get_windows_uuid()
        baseboard = get_windows_baseboard()
        mac = get_windows_mac()
    
    # Create fingerprint exactly like Electron's main.js
    fingerprint = f"{uuid}|{baseboard}|{mac}"
    fp_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
    
    return {
        'uuid': uuid,
        'baseboard': baseboard,
        'mac': mac,
        'fingerprint': fingerprint,
        'fpHash': fp_hash
    }


# ============ Windows Hardware Detection ============

def get_windows_uuid():
    """
    Get System UUID on Windows using WMIC csproduct
    This is MORE STABLE than CPU ProcessorId
    """
    try:
        result = subprocess.run(
            ['wmic', 'csproduct', 'get', 'uuid'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
        )
        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            if len(lines) > 1:
                return lines[1]
    except Exception as e:
        logger.warning(f"Failed to get Windows UUID: {e}")
    return ''


def get_windows_baseboard():
    """Get motherboard serial number on Windows using WMIC"""
    try:
        result = subprocess.run(
            ['wmic', 'baseboard', 'get', 'serialnumber'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
        )
        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            if len(lines) > 1:
                return lines[1]
    except Exception as e:
        logger.warning(f"Failed to get Windows baseboard: {e}")
    return ''


def get_windows_mac():
    """Get MAC address on Windows using WMIC"""
    try:
        result = subprocess.run(
            ['wmic', 'nic', 'where', 'NetEnabled=true', 'get', 'MACAddress'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
        )
        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            if len(lines) > 1:
                return lines[1]
    except Exception as e:
        logger.warning(f"Failed to get Windows MAC: {e}")
    
    # Fallback to getmac command
    try:
        result = subprocess.run(
            ['getmac'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if '-' in line and len(line.split('-')) >= 6:
                    return line.split()[0].strip()
    except Exception as e:
        logger.warning(f"Failed to get Windows MAC (getmac): {e}")
    
    return ''

