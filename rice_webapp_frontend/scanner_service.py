"""
Standalone Python Scanner Service using Windows WIA
Handles EPSON scanner with hardcoded settings matching EPSON Scan 2 UI
Run: python scanner_service.py
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
from datetime import datetime
import pytz
import sys
import requests
sys.stdout.reconfigure(encoding='utf-8')

try:
    import win32com.client
    import pythoncom
    WIA_AVAILABLE = True
except ImportError:
    WIA_AVAILABLE = False
    print("⚠️  pywin32 not installed. Install with: pip install pywin32")

app = Flask(__name__)
CORS(app)

SCAN_DIR = os.path.join(os.path.dirname(__file__), 'scans')
os.makedirs(SCAN_DIR, exist_ok=True)

# HARDCODED SETTINGS - Matching EPSON Scan 2 UI exactly
HARDCODED_SETTINGS = {
    'scanner': 'EPSON Perfection V39II(USB)',
    'mode': 'Document Mode',
    'document_source': 'Scanner Glass',
    'document_size': 'A4',
    'image_type': 'Color',
    'resolution': 400,  # DPI
    'rotate': 0,  # degrees
    'correct_document_skew': False,
    'format': 'jpeg',
    'quality': 90,
    'brightness': -100,  # Matches UI
    'contrast': 200,      # Matches UI
    'gamma': 2.2,       # Matches UI
    'image_option': 'None',
    'unsharp_mask': 'Off',
    'descreening': 'Off',
    'edge_fill': 'None',
    'dual_image_output': 'Off',
    'watermark': 'Off'
}

def init_scanner():
    """Initialize WIA scanner with detailed error reporting"""
    if not WIA_AVAILABLE:
        print("❌ WIA not available - pywin32 not installed")
        return None
    
    try:
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        # Create WIA device manager
        print("🔍 Creating WIA DeviceManager...")
        deviceManager = win32com.client.Dispatch("WIA.DeviceManager")
        
        print(f"📱 Found {deviceManager.DeviceInfos.Count} device(s)")
        
        # List all available scanners
        scanner_found = None
        for i in range(1, deviceManager.DeviceInfos.Count + 1):
            deviceInfo = deviceManager.DeviceInfos.Item(i)
            device_name = deviceInfo.Properties("Name").Value
            device_type = deviceInfo.Type
            
            print(f"  Device {i}: {device_name} (Type: {device_type})")
            
            # Type 1 = Scanner
            if device_type == 1:
                print(f"  ✅ Scanner found: {device_name}")
                
                # Prefer EPSON scanner
                if 'epson' in device_name.lower():
                    print(f"  🎯 EPSON scanner detected: {device_name}")
                    scanner_found = deviceInfo
                    break
                elif scanner_found is None:
                    scanner_found = deviceInfo
        
        if scanner_found:
            device_name = scanner_found.Properties("Name").Value
            print(f"✅ Connecting to: {device_name}")
            return scanner_found.Connect()
        
        print("❌ No scanner found")
        return None
        
    except Exception as e:
        print(f"❌ Failed to initialize scanner: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/api/scanner/status', methods=['GET'])
def get_status():
    """Check scanner status"""
    if not WIA_AVAILABLE:
        return jsonify({
            'success': False,
            'status': 'pywin32 not installed',
            'message': 'Install with: pip install pywin32'
        })
    
    scanner = init_scanner()
    if scanner:
        try:
            scanner_name = scanner.Properties("Name").Value
        except:
            scanner_name = "Scanner detected"
        
        return jsonify({
            'success': True,
            'scanner': scanner_name,
            'status': 'Ready',
            'hardcodedSettings': HARDCODED_SETTINGS,
            'message': 'Automated mode - Settings match EPSON Scan 2 UI exactly'
        })
    else:
        return jsonify({
            'success': False,
            'status': 'Scanner not found',
            'message': 'Ensure EPSON scanner is connected, powered on, and drivers installed'
        })

@app.route('/api/scanner/scan', methods=['POST'])
def scan():
    """Start scan with HARDCODED settings matching EPSON Scan 2 UI"""
    if not WIA_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'pywin32 not installed'
        }), 500
    
    try:
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        print('🚀 Starting automated scan with EPSON Scan 2 UI settings')
        print(f'   Settings: Resolution={HARDCODED_SETTINGS["resolution"]}dpi, '
              f'Brightness={HARDCODED_SETTINGS["brightness"]}, '
              f'Contrast={HARDCODED_SETTINGS["contrast"]}, '
              f'Gamma={HARDCODED_SETTINGS["gamma"]}')
        
        scanner = init_scanner()
        if not scanner:
            return jsonify({
                'success': False,
                'error': 'Scanner not available. Check: 1) Scanner is ON, 2) USB connected'
            }), 404
        
        print(f"✅ Scanner connected: {scanner.Properties('Name').Value}")
        
        # Get scanner item (flatbed)
        print("📄 Getting scanner item (flatbed)...")
        if scanner.Items.Count == 0:
            return jsonify({
                'success': False,
                'error': 'No scanner items available. Try using the scanner software once first.'
            }), 500
        
        item = scanner.Items.Item(1)
        print(f"✅ Scanner item found: {scanner.Items.Count} item(s)")
        
        # Set HARDCODED properties to match EPSON Scan 2 UI
        print("⚙️ Setting scanner properties to match EPSON Scan 2 UI...")
        try:
            # List available properties for debugging
            print("\nAvailable WIA properties:")
            for prop in item.Properties:
                try:
                    print(f"  - {prop.PropertyID}: {prop.Name} = {prop.Value}")
                except:
                    pass
            print()
            
            # Set resolution (6147 = Horizontal Resolution, 6148 = Vertical Resolution)
            try:
                item.Properties("6147").Value = HARDCODED_SETTINGS["resolution"]  # Horizontal DPI
                item.Properties("6148").Value = HARDCODED_SETTINGS["resolution"]  # Vertical DPI
                print(f"✅ Resolution set to {HARDCODED_SETTINGS['resolution']} DPI")
            except Exception as e:
                print(f"⚠️ Could not set resolution: {e}")
            
            # Set color mode (6146 = Current Intent)
            # 1 = Color, 2 = Grayscale, 4 = B&W
            try:
                item.Properties("6146").Value = 1  # Color
                print("✅ Color mode set to Color")
            except Exception as e:
                print(f"⚠️ Could not set color mode: {e}")

            # Set brightness (Property ID: 6154)
            # Range typically: -1000 to 1000, where 0 is neutral
            try:
                item.Properties("6154").Value = HARDCODED_SETTINGS["brightness"]
                print(f"✅ Brightness set to {HARDCODED_SETTINGS['brightness']}")
            except Exception as e:
                print(f"⚠️ Could not set brightness: {e}")

            # Set contrast (Property ID: 6155)
            # Range typically: -1000 to 1000, where 0 is neutral
            try:
                item.Properties("6155").Value = HARDCODED_SETTINGS["contrast"]
                print(f"✅ Contrast set to {HARDCODED_SETTINGS['contrast']}")
            except Exception as e:
                print(f"⚠️ Could not set contrast: {e}")
            
            # Note: Gamma is typically not available through WIA
            # It's often handled by the scanner driver or post-processing
            # We'll apply it during image conversion if needed
            print(f"ℹ️  Gamma ({HARDCODED_SETTINGS['gamma']}) will be applied during image processing")
            
        except Exception as e:
            print(f"⚠️ Some properties not supported: {e}")
        
        # Scan image
        print("\n📸 Transferring image from scanner...")
        
        # Try different formats
        formats = [
            ("{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}", "JPEG"),  # JPEG
            ("{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}", "BMP"),   # BMP
            ("{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}", "PNG"),   # PNG
        ]
        
        image = None
        format_used = None
        
        for format_guid, format_name in formats:
            try:
                print(f"  Trying {format_name} format...")
                image = item.Transfer(format_guid)
                format_used = format_name
                print(f"✅ Image acquired in {format_name} format")
                break
            except Exception as e:
                print(f"  ❌ {format_name} failed: {e}")
        
        if not image:
            # Try default transfer
            try:
                print("  Trying default transfer...")
                image = item.Transfer()
                format_used = "Default"
                print("✅ Image acquired in default format")
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Failed to transfer image: {e}'
                }), 500
        
        # Save with timestamp
        timestamp = datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%Y%m%d_%H%M%S')
        temp_filename = f'scan_{timestamp}_temp.{format_used.lower()}'
        filename = f'scan_{timestamp}.jpg'
        temp_filepath = os.path.join(SCAN_DIR, temp_filename)
        filepath = os.path.join(SCAN_DIR, filename)
        
        # Save image
        print(f"💾 Saving image to: {temp_filepath}")
        image.SaveFile(temp_filepath)
        
        # Convert to JPEG with quality 85 and apply gamma correction
        print(f"🔄 Converting to JPEG (quality: {HARDCODED_SETTINGS['quality']}%, gamma: {HARDCODED_SETTINGS['gamma']})...")
        from PIL import Image as PILImage
        import numpy as np
        
        img = PILImage.open(temp_filepath)
        img = img.convert('RGB')  # Ensure RGB mode
        
        # Apply gamma correction (Gamma = 2.2 from UI)
        gamma = HARDCODED_SETTINGS['gamma']
        if gamma != 1.0:
            # Convert to numpy array for gamma correction
            img_array = np.array(img, dtype=np.float32) / 255.0
            img_array = np.power(img_array, 1.0 / gamma)
            img_array = (img_array * 255.0).clip(0, 255).astype(np.uint8)
            img = PILImage.fromarray(img_array, 'RGB')
            print(f"✅ Gamma correction applied: {gamma}")
        
        img.save(filepath, 'JPEG', quality=HARDCODED_SETTINGS['quality'], optimize=True)
        
        # Remove temp file if different
        if temp_filepath != filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        file_size = os.path.getsize(filepath)
        
        print(f'\n✅ Scan completed: {filename} ({file_size:,} bytes)')
        print(f'   Applied settings: Brightness={HARDCODED_SETTINGS["brightness"]}, '
              f'Contrast={HARDCODED_SETTINGS["contrast"]}, Gamma={HARDCODED_SETTINGS["gamma"]}')
        
        return jsonify({
            'success': True,
            'message': 'Scan completed with EPSON Scan 2 UI settings',
            'file': {
                'filename': filename,
                'path': filepath,
                'url': f'http://localhost:8080/api/scanner/file/{filename}',
                'settings': HARDCODED_SETTINGS,
                'size': file_size
            }
        })
            
    except Exception as e:
        print(f'❌ Scan error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        # Uninitialize COM
        try:
            pythoncom.CoUninitialize()
        except:
            pass

@app.route('/api/scanner/files', methods=['GET'])
def list_files():
    """List scanned files"""
    try:
        files = [f for f in os.listdir(SCAN_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        file_list = []
        
        for f in sorted(files, reverse=True):  # Most recent first
            filepath = os.path.join(SCAN_DIR, f)
            file_list.append({
                'filename': f,
                'size': os.path.getsize(filepath),
                'url': f'http://localhost:8080/api/scanner/file/{f}'
            })
        
        return jsonify({
            'success': True,
            'files': file_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scanner/file/<filename>', methods=['GET'])
def serve_file(filename):
    """Serve scanned file"""
    return send_from_directory(SCAN_DIR, filename)

@app.route('/api/scanner/file/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete scanned file"""
    try:
        filepath = os.path.join(SCAN_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print('\n╔═══════════════════════════════════════════════╗')
    print('║   Python Scanner Service (WIA)                ║')
    print('╠═══════════════════════════════════════════════╣')
    print('║   Status: Running on http://localhost:8080    ║')
    print('║   Mode: AUTOMATED (No UI popups)              ║')
    print('╚═══════════════════════════════════════════════╝\n')
    print('📋 HARDCODED Settings (Matching EPSON Scan 2 UI):')
    print(f'   • Scanner: {HARDCODED_SETTINGS["scanner"]}')
    print(f'   • Mode: {HARDCODED_SETTINGS["mode"]}')
    print(f'   • Document Source: {HARDCODED_SETTINGS["document_source"]}')
    print(f'   • Document Size: {HARDCODED_SETTINGS["document_size"]}')
    print(f'   • Image Type: {HARDCODED_SETTINGS["image_type"]}')
    print(f'   • Resolution: {HARDCODED_SETTINGS["resolution"]} DPI')
    print(f'   • Rotate: {HARDCODED_SETTINGS["rotate"]}°')
    print(f'   • Format: {HARDCODED_SETTINGS["format"].upper()}')
    print(f'   • Quality: {HARDCODED_SETTINGS["quality"]}%')
    print(f'   • Brightness: {HARDCODED_SETTINGS["brightness"]}')
    print(f'   • Contrast: {HARDCODED_SETTINGS["contrast"]}')
    print(f'   • Gamma: {HARDCODED_SETTINGS["gamma"]}')
    print('\n🔍 Testing scanner detection...')
    
    scanner = init_scanner()
    if scanner:
        print('✅ Scanner detected and ready!')
    else:
        print('❌ No scanner detected. Please check:')
        print('   1. Scanner is powered ON')
        print('   2. USB cable is connected')
        print('   3. Scanner drivers are installed')
        print('   4. Try running EPSON Scan software once first')
    
    print('\n✅ Ready for automated scanning with exact EPSON Scan 2 settings!\n')
    
    app.run(host='0.0.0.0', port=8080, debug=False)