"""
Standalone Python Scanner Service using TWAIN
Handles EPSON scanner with hardcoded settings matching EPSON Scan 2 UI
Run: python scanner_service.py
Requires: pip install pytwain pillow flask flask-cors pytz numpy
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
from datetime import datetime
import pytz
import sys

sys.stdout.reconfigure(encoding='utf-8')

try:
    import twain
    TWAIN_AVAILABLE = True
except ImportError:
    TWAIN_AVAILABLE = False
    print("⚠️  pytwain not installed. Install with: pip install pytwain")

app = Flask(__name__)
CORS(app)

SCAN_DIR = os.path.join(os.path.dirname(__file__), 'scans')
os.makedirs(SCAN_DIR, exist_ok=True)

# HARDCODED SETTINGS - Matching EPSON Scan 2 UI exactly
HARDCODED_SETTINGS = {
    'scanner': 'EPSON Perfection V39II',
    'mode': 'Document Mode',
    'document_source': 'Scanner Glass',
    'document_size': 'A4',
    'image_type': 'Color',
    'resolution': 400,  # DPI
    'rotate': 0,  # degrees
    'correct_document_skew': False,
    'format': 'jpeg',
    'quality': 85,
    'brightness': 0,
    'contrast': 220,
    'gamma': 2.2,
    'image_option': 'None',
    'unsharp_mask': 'Off',
    'descreening': 'Off',
    'edge_fill': 'None',
    'dual_image_output': 'Off',
    'watermark': 'Off'
}

# Global TWAIN source manager and scanner source
sm = None
ss = None
scanner_initialized = False

def init_twain():
    """Initialize TWAIN and return source manager"""
    global sm
    if not TWAIN_AVAILABLE:
        print("❌ TWAIN not available - pytwain not installed")
        return None
    
    try:
        if sm is None:
            # print("🔍 Creating TWAIN Source Manager...")
            sm = twain.SourceManager(0)
        return sm
    except Exception as e:
        # print(f"❌ Failed to initialize TWAIN: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_scanner():
    """Get TWAIN scanner source (reuses existing connection)"""
    global ss, scanner_initialized
    
    try:
        # Return existing scanner if already initialized
        if scanner_initialized and ss is not None:
            return ss
        
        sm = init_twain()
        if not sm:
            return None
        
        # Get list of available sources
        sources = sm.GetSourceList()
        # print(f"📱 Found {len(sources)} TWAIN source(s):")
        # for i, source in enumerate(sources):
        #     print(f"  {i+1}. {source}")
        
        # Prefer EPSON scanner
        epson_source = None
        for source in sources:
            if 'epson' in source.lower():
                # print(f"  🎯 EPSON scanner detected: {source}")
                epson_source = source
                break
        
        # Open the source (only once)
        if epson_source:
            # print(f"✅ Opening: {epson_source}")
            ss = sm.OpenSource(epson_source)
        elif len(sources) > 0:
            # print(f"✅ Opening: {sources[0]}")
            ss = sm.OpenSource(sources[0])
        else:
            # print("❌ No scanner sources available")
            return None
        
        scanner_initialized = True
        return ss
        
    except Exception as e:
        # print(f"❌ Failed to get scanner: {e}")
        import traceback
        traceback.print_exc()
        scanner_initialized = False
        ss = None
        return None

def close_scanner():
    """Close scanner source (keeps source manager alive)"""
    global ss, scanner_initialized
    try:
        if ss is not None:
            ss.destroy()
            ss = None
            scanner_initialized = False
            # print("✅ Scanner closed")
    except Exception as e:
        print(f"Error closing scanner: {e}")

def reset_scanner_state():
    """Reset scanner state after scan without closing source manager"""
    global ss, scanner_initialized
    try:
        if ss is not None:
            ss = None
            scanner_initialized = False
            # print("✅ Scanner state reset for next scan")
    except Exception as e:
        print(f"Error resetting scanner state: {e}")

def configure_scanner(ss):
    """Configure scanner with hardcoded settings"""
    try:
        # print("⚙️ Configuring scanner with EPSON Scan 2 UI settings...")
        
        # Set pixel type (color mode)
        # 0 = B&W, 1 = Grayscale, 2 = RGB Color
        try:
            ss.SetCapability(twain.ICAP_PIXELTYPE, twain.TWTY_UINT16, 2)  # RGB Color
            # print("✅ Color mode set to RGB Color")
        except Exception as e:
            print(f"Could not set color mode: {e}")
        
        # Set resolution
        try:
            resolution = HARDCODED_SETTINGS["resolution"]
            ss.SetCapability(twain.ICAP_XRESOLUTION, twain.TWTY_FIX32, resolution)
            ss.SetCapability(twain.ICAP_YRESOLUTION, twain.TWTY_FIX32, resolution)
            # print(f"✅ Resolution set to {resolution} DPI")
        except Exception as e:
            print(f"Could not set resolution: {e}")
        
        # Set brightness (range typically -1000 to 1000)
        try:
            brightness = HARDCODED_SETTINGS["brightness"]
            ss.SetCapability(twain.ICAP_BRIGHTNESS, twain.TWTY_FIX32, brightness)
            # print(f"✅ Brightness set to {brightness}")
        except Exception as e:
            print(f" Could not set brightness: {e}")
        
        # Set contrast (range typically -1000 to 1000)
        try:
            contrast = HARDCODED_SETTINGS["contrast"]
            ss.SetCapability(twain.ICAP_CONTRAST, twain.TWTY_FIX32, contrast)
            # print(f"✅ Contrast set to {contrast}")
        except Exception as e:
            print(f"Could not set contrast: {e}")
        
        # Set gamma (note: TWAIN gamma is typically 1.0-3.0)
        try:
            gamma = HARDCODED_SETTINGS["gamma"]
            ss.SetCapability(twain.ICAP_GAMMA, twain.TWTY_FIX32, gamma)
            # print(f"✅ Gamma set to {gamma}")
        except Exception as e:
            print(f" Could not set gamma {e}")
        
        # Disable UI (automated scanning)
        try:
            ss.SetCapability(twain.CAP_INDICATORS, twain.TWTY_BOOL, False)
            # print("✅ UI indicators disabled (automated mode)")
        except Exception as e:
            print(f"Could not disable UI indicators: {e}")
        
        # print("✅ Scanner configuration complete")
        return True
        
    except Exception as e:
        print(f"Error during configuration: {e}")
        return False

@app.route('/api/scanner/status', methods=['GET'])
def get_status():
    """Check scanner status"""
    if not TWAIN_AVAILABLE:
        return jsonify({
            'success': False,
            'status': 'pytwain not installed',
            'message': 'Install with: pip install pytwain'
        })
    
    try:
        ss = get_scanner()
        if ss:
            scanner_name = ss.GetSourceName()
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
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'Error',
            'message': str(e)
        })

@app.route('/api/scanner/scan', methods=['POST'])
def scan():
    """Start scan with HARDCODED settings matching EPSON Scan 2 UI"""
    if not TWAIN_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'pytwain not installed'
        }), 500
    
    try:
        # print('🚀 Starting automated scan with EPSON Scan 2 UI settings')
        # print(f'   Settings: Resolution={HARDCODED_SETTINGS["resolution"]}dpi, '
        #       f'Brightness={HARDCODED_SETTINGS["brightness"]}, '
        #       f'Contrast={HARDCODED_SETTINGS["contrast"]}, '
        #       f'Gamma={HARDCODED_SETTINGS["gamma"]}')
        
        ss = get_scanner()
        if not ss:
            return jsonify({
                'success': False,
                'error': 'Scanner not available. Check: 1) Scanner is ON, 2) USB connected, 3) TWAIN driver installed'
            }), 404
        
        scanner_name = ss.GetSourceName()
        # print(f"✅ Scanner connected: {scanner_name}")
        
        # Configure scanner
        configure_scanner(ss)
        
        # Request scan without showing UI
        # print("📸 Starting image acquisition...")
        try:
            ss.RequestAcquire(0, 0)  # (ShowUI=0, ModalUI=0) for automated scanning
        except (twain.exceptions.SequenceError, AttributeError) as e:
            # Scanner state issue - reset and get fresh scanner instance
            # print(f"⚠️ Scanner state error ({type(e).__name__}) - reinitializing...")
            reset_scanner_state()
            ss = get_scanner()
            if not ss:
                return jsonify({
                    'success': False,
                    'error': 'Failed to reinitialize scanner'
                }), 500
            configure_scanner(ss)
            ss.RequestAcquire(0, 0)
        
        # Get the scanned image
        rv = ss.XferImageNatively()
        if rv:
            (handle, count) = rv
            # print(f"✅ Image acquired (handle: {handle}, count: {count})")
            
            # Convert DIB to PIL Image
            from PIL import Image as PILImage
            from PIL import ImageEnhance
            import numpy as np
            
            # Save temp BMP
            temp_bmp = os.path.join(SCAN_DIR, 'temp_scan.bmp')
            twain.DIBToBMFile(handle, temp_bmp)
            
            # Open image (no conversion)
            img = PILImage.open(temp_bmp)
            # print(f"ℹ️  Image mode: {img.mode}, Size: {img.size}")
            
            # Apply gamma correction if not applied by scanner
            gamma = HARDCODED_SETTINGS['gamma']
            if gamma != 1.0:
                img_array = np.array(img, dtype=np.float32) / 255.0
                img_array = np.power(img_array, 1.0 / gamma)
                img_array = (img_array * 255.0).clip(0, 255).astype(np.uint8)
                img = PILImage.fromarray(img_array, 'RGB')
                # print(f"✅ Gamma correction applied: {gamma}")
            
            # # Fine-tune exposure - Additional 20% brightness boost
            # enhancer = ImageEnhance.Brightness(img)
            # img = enhancer.enhance(1.2)
            # print("✅ Additional 20% brightness boost applied")
            
            # Save with timestamp
            timestamp = datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%Y%m%d_%H%M%S')
            filename = f'scan_{timestamp}.jpg'
            filepath = os.path.join(SCAN_DIR, filename)
            
            # Save as JPEG
            # print(f"💾 Saving image: {filepath}")
            img.save(filepath, 'JPEG', quality=HARDCODED_SETTINGS['quality'], optimize=True)
            
            # Clean up temp file
            try:
                os.remove(temp_bmp)
            except:
                pass
            
            # Reset scanner state after successful scan (don't destroy, just reset flag)
            reset_scanner_state()
            
            file_size = os.path.getsize(filepath)
            
            # print(f'\n✅ Scan completed: {filename} ({file_size:,} bytes)')
            # print(f'   Applied settings: Brightness={HARDCODED_SETTINGS["brightness"]}, '
            #       f'Contrast={HARDCODED_SETTINGS["contrast"]}, Gamma={HARDCODED_SETTINGS["gamma"]}')
            # print(f'   Post-processing: 20% brightness enhancement\n')
            
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
        else:
            return jsonify({
                'success': False,
                'error': 'No image acquired from scanner'
            }), 500
            
    except Exception as e:
        # print(f'❌ Scan error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
    # print('\n╔═══════════════════════════════════════════════╗')
    # print('║   Python Scanner Service (TWAIN)             ║')
    # print('╠═══════════════════════════════════════════════╣')
    # print('║   Status: Running on http://localhost:8080   ║')
    # print('║   Mode: AUTOMATED (No UI popups)             ║')
    # print('╚═══════════════════════════════════════════════╝\n')
    # print('📋 HARDCODED Settings (Matching EPSON Scan 2 UI):')
    # print(f'   • Scanner: {HARDCODED_SETTINGS["scanner"]}')
    # print(f'   • Mode: {HARDCODED_SETTINGS["mode"]}')
    # print(f'   • Document Source: {HARDCODED_SETTINGS["document_source"]}')
    # print(f'   • Document Size: {HARDCODED_SETTINGS["document_size"]}')
    # print(f'   • Image Type: {HARDCODED_SETTINGS["image_type"]}')
    # print(f'   • Resolution: {HARDCODED_SETTINGS["resolution"]} DPI')
    # print(f'   • Rotate: {HARDCODED_SETTINGS["rotate"]}°')
    # print(f'   • Format: {HARDCODED_SETTINGS["format"].upper()}')
    # print(f'   • Quality: {HARDCODED_SETTINGS["quality"]}%')
    # print(f'   • Brightness: {HARDCODED_SETTINGS["brightness"]}')
    # print(f'   • Contrast: {HARDCODED_SETTINGS["contrast"]}')
    # print(f'   • Gamma: {HARDCODED_SETTINGS["gamma"]}')
    # print(f'   • Post-processing: Additional 20% brightness boost')
    # print('\n🔍 Testing scanner detection...')
    
    try:
        ss = get_scanner()
        # if ss:
        #     # print('✅ Scanner detected and ready!')
        # else:
        #     print('❌ No scanner detected. Please check:')
        #     print('   1. Scanner is powered ON')
        #     print('   2. USB cable is connected')
        #     print('   3. TWAIN driver is installed')
        #     print('   4. Try running EPSON Scan software once first')
    except Exception as e:
        print(f'❌ Error detecting scanner: {e}')
    
    # print('\n✅ Ready for automated scanning with TWAIN!\n')
    
    app.run(host='0.0.0.0', port=8080, debug=False)