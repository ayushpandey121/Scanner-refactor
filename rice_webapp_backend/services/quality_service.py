# services/quality_service.py
import os
import logging
import pandas as pd
from rice_quality_utils import RiceQualityAnalysis
from services.grain_service import GrainService
from services.storage_service import StorageService
from utils.metrics import determine_sample_type, calculate_statistics
from config import Config

logger = logging.getLogger(__name__)


def get_device_id_local():
    """
    Get device ID from locally stored model files (fastest method)
    
    Returns:
        str: Device ID (e.g., "AGS-2001") or None if not found
    """
    try:
        models_folder = os.path.join(Config.BASE_DIR, 'models')
        
        if not os.path.exists(models_folder):
            logger.warning(f"Models folder does not exist: {models_folder}")
            return None
        
        # List all CSV files
        model_files = [f for f in os.listdir(models_folder) if f.endswith('.csv')]
        
        if not model_files:
            logger.warning(f"No model files found in: {models_folder}")
            return None
        
        # Extract model number from first file (e.g., "2001_1.csv" -> "2001")
        import re
        for file in model_files:
            match = re.match(r'(\d{4})_[12]\.csv', file)
            if match:
                model_number = match.group(1)
                device_id = f"AGS-{model_number}"
                logger.info(f"✅ Extracted device ID from local models: {device_id}")
                return device_id
        
        logger.warning(f"Could not extract device ID from model files: {model_files}")
        return None
        
    except Exception as e:
        logger.error(f"Error reading device ID from local storage: {e}")
        return None


class QualityService:
    """Handle quality analysis workflows"""
    
    @staticmethod
    def analyze_quality(grain_images, padded_dir, pixels_per_metric,
                       minlen, chalky_percentage, base_name,
                       exclude_flags_dict=None, rice_variety='non_sella', device_id=None):
        """
        Perform quality analysis on extracted grains
        
        Args:
            grain_images: List of grain image filenames
            padded_dir: Directory containing padded grain images
            pixels_per_metric: Pixels per metric value
            minlen: Minimum length threshold
            chalky_percentage: Chalky percentage threshold
            base_name: Base name for output files
            exclude_flags_dict: Dictionary mapping filenames to exclusion flags
            rice_variety: Rice variety for Kett prediction ('sella' or 'non_sella')
            device_id: Optional device ID (will auto-detect from local files if not provided)
        
        Returns:
            dict: Analysis results
        """
        if exclude_flags_dict is None:
            exclude_flags_dict = {}
        
        # Auto-detect device_id from LOCAL MODEL FILES if not provided (FAST!)
        if not device_id:
            logger.info("🔍 Auto-detecting device_id from local model files...")
            device_id = get_device_id_local()
            
            if device_id:
                logger.info(f"✅ Auto-detected device_id: {device_id}")
            else:
                logger.error("❌ Could not auto-detect device_id from local models!")
                logger.error("   Please ensure activation was completed and model files exist in:")
                logger.error(f"   {os.path.join(Config.BASE_DIR, 'models')}")
                
                # Try fallback to S3 (slow)
                try:
                    from utils.activation_helper import get_device_id
                    logger.info("⚠️ Trying fallback: S3 lookup...")
                    device_id = get_device_id()
                    if device_id:
                        logger.info(f"✅ Found device_id via S3: {device_id}")
                except Exception as e:
                    logger.error(f"❌ S3 fallback also failed: {e}")
        
        logger.info("Starting quality analysis")
        
        # Build grain paths and exclude flags list
        grain_paths = []
        exclude_flags = []
        for img in grain_images:
            grain_paths.append(os.path.join(padded_dir, img))
            exclude_flags.append(exclude_flags_dict.get(img, False))
        
        # Count excluded grains
        excluded_count = sum(exclude_flags)
        included_count = len(grain_images) - excluded_count
        logger.info(f"Processing {len(grain_images)} grains ({included_count} included, {excluded_count} excluded)")
        
        # FIRST PASS: Collect RGB values for sample type determination (excludes large grains)
        rgb_values, grain_features = GrainService.collect_rgb_values(
            grain_paths, pixels_per_metric, exclude_flags
        )
        
        # Determine sample type
        if rgb_values:
            avg_r = sum(r for r, b in rgb_values) / len(rgb_values)
            avg_b = sum(b for r, b in rgb_values) / len(rgb_values)
            sample_type = determine_sample_type(avg_r, avg_b)
            logger.info(f"Sample type determined: {sample_type} (avg_R={avg_r:.2f}, avg_B={avg_b:.2f})")
        else:
            sample_type = "White"
            logger.warning("No RGB values collected, defaulting to White sample type")
        
        # SECOND PASS: Process grains with classification (skip excluded ones)
        grain_quality_data = []
        excel_data = []
        chalky_indices = []
        discolor_indices = []
        broken_indices = []
        
        # For Kett calculation
        grains_for_kett = []

        # For RGB averages
        all_rgb_values = []
        chalky_rgb_values = []
        non_chalky_rgb_values = []
        
        for idx, grain_img in enumerate(grain_images):
            grain_path = os.path.join(padded_dir, grain_img)
            exclude_grain = exclude_flags_dict.get(grain_img, False)
            
            # Skip excluded grains
            if exclude_grain:
                logger.debug(f"Skipping excluded grain: {grain_img}")
                continue
            
            feature_dict = grain_features.get(grain_img, {})
            
            if not feature_dict:
                logger.warning(f"No features for grain {grain_img}, skipping")
                continue
            
            processed_grain = GrainService.process_grain_with_classification(
                grain_path, grain_img, feature_dict, sample_type,
                pixels_per_metric, minlen, chalky_percentage, exclude_grain
            )
            
            if not processed_grain:
                continue
            
            is_chalky = processed_grain['chalky_count'] > 0

            # Collect RGB values for all grains
            all_rgb_values.append({
                'R': processed_grain['R'],
                'G': processed_grain['G'],
                'B': processed_grain['B']
            })

            # Track defects
            if processed_grain['discoloration_class'] == "YES":
                discolor_indices.append(idx)
            if is_chalky:
                chalky_indices.append(idx)
                # Collect RGB values for chalky grains
                chalky_rgb_values.append({
                    'R': processed_grain['R'],
                    'G': processed_grain['G'],
                    'B': processed_grain['B']
                })
            else:
                # Collect RGB values for non-chalky grains
                non_chalky_rgb_values.append({
                    'R': processed_grain['R'],
                    'G': processed_grain['G'],
                    'B': processed_grain['B']
                })
            if processed_grain['is_broken']:
                broken_indices.append(idx)
            
            # Build quality data
            grain_quality_data.append({
                "index": idx,
                "filename": grain_img,
                "dimensions": {
                    "length": processed_grain['length'],
                    "breadth": processed_grain['breadth']
                },
                "defects": {
                    "broken": processed_grain['is_broken'],
                    "discolor": processed_grain['discoloration_class'] == "YES",
                    "chalky": is_chalky
                },
                "discolor_type": processed_grain['discolor_result'],
                "chalky_count": processed_grain['chalky_count']
            })
            
            # Collect grain data for Kett calculation
            grains_for_kett.append({
                'length': processed_grain['length'],
                'width': processed_grain['breadth'],
                'discolor': processed_grain['discoloration_class'],
                'chalky': "Yes" if is_chalky else "No",
                'broken': processed_grain['is_broken'],
                'R': processed_grain['R'],
                'G': processed_grain['G'],
                'B': processed_grain['B']
            })
            
            # Build Excel data
            excel_data.append({
                'Image Name': grain_img,
                'Length (mm)': round(processed_grain['length'], 2),
                'Breadth (mm)': round(processed_grain['breadth'], 2),
                'R': round(processed_grain['R'], 2),
                'G': round(processed_grain['G'], 2),
                'B': round(processed_grain['B'], 2),
                'Discoloration': processed_grain['discoloration_class']
            })
        
        logger.info(f"Processed {len(grain_quality_data)} included grains (excluded {excluded_count} large grains)")
        
        # Calculate and print average RGB values
        logger.info("=" * 60)
        logger.info("RGB AVERAGES SUMMARY:")
        logger.info("=" * 60)

        # All grains RGB averages
        if all_rgb_values:
            avg_all_r = sum(g['R'] for g in all_rgb_values) / len(all_rgb_values)
            avg_all_g = sum(g['G'] for g in all_rgb_values) / len(all_rgb_values)
            avg_all_b = sum(g['B'] for g in all_rgb_values) / len(all_rgb_values)

            logger.info(f"ALL GRAINS RGB AVERAGES ({len(all_rgb_values)} grains):")
            logger.info(f"  Average R: {avg_all_r:.2f}")
            logger.info(f"  Average G: {avg_all_g:.2f}")
            logger.info(f"  Average B: {avg_all_b:.2f}")

        # Non-chalky grains RGB averages
        if non_chalky_rgb_values:
            avg_non_chalky_r = sum(g['R'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)
            avg_non_chalky_g = sum(g['G'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)
            avg_non_chalky_b = sum(g['B'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)

            logger.info(f"NON-CHALKY GRAINS RGB AVERAGES ({len(non_chalky_rgb_values)} grains):")
            logger.info(f"  Average R: {avg_non_chalky_r:.2f}")
            logger.info(f"  Average G: {avg_non_chalky_g:.2f}")
            logger.info(f"  Average B: {avg_non_chalky_b:.2f}")

        # Chalky grains RGB averages
        if chalky_rgb_values:
            avg_chalky_r = sum(g['R'] for g in chalky_rgb_values) / len(chalky_rgb_values)
            avg_chalky_g = sum(g['G'] for g in chalky_rgb_values) / len(chalky_rgb_values)
            avg_chalky_b = sum(g['B'] for g in chalky_rgb_values) / len(chalky_rgb_values)

            logger.info(f"CHALKY GRAINS RGB AVERAGES ({len(chalky_rgb_values)} grains):")
            logger.info(f"  Average R: {avg_chalky_r:.2f}")
            logger.info(f"  Average G: {avg_chalky_g:.2f}")
            logger.info(f"  Average B: {avg_chalky_b:.2f}")
        else:
            logger.info("No chalky grains detected")

        logger.info("=" * 60)
        
        # Generate quality report (now includes Kett prediction via calculate_statistics)
        quality_report = RiceQualityAnalysis.generate_quality_report(
            grain_quality_data, pixels_per_metric
        )
        
        # Calculate statistics including Kett value with device_id
        logger.info(f"📊 Calculating statistics with device_id: {device_id}")
        statistics = calculate_statistics(
            grains_for_kett, 
            rice_variety=rice_variety,
            device_id=device_id  # Pass device_id for automatic model detection
        )
        
        # Add Kett value to quality report
        if statistics.get('kett_value') is not None:
            quality_report['kett_value'] = statistics['kett_value']
            logger.info(f"Kett value added to quality report: {statistics['kett_value']}")
        
        # Add RGB averages to quality report
        if all_rgb_values:
            quality_report['all_rgb_avg'] = {
                'R': round(avg_all_r, 2),
                'G': round(avg_all_g, 2),
                'B': round(avg_all_b, 2),
                'count': len(all_rgb_values)
            }

        if non_chalky_rgb_values:
            quality_report['non_chalky_rgb_avg'] = {
                'R': round(avg_non_chalky_r, 2),
                'G': round(avg_non_chalky_g, 2),
                'B': round(avg_non_chalky_b, 2),
                'count': len(non_chalky_rgb_values)
            }

        if chalky_rgb_values:
            quality_report['chalky_rgb_avg'] = {
                'R': round(avg_chalky_r, 2),
                'G': round(avg_chalky_g, 2),
                'B': round(avg_chalky_b, 2),
                'count': len(chalky_rgb_values)
            }
        
        # Save Excel files
        excel_url, kett_excel_url = QualityService._save_excel_files(
            excel_data, base_name
        )
        
        return {
            'sample_type': sample_type,
            'quality_report': quality_report,
            'grain_quality_data': grain_quality_data,
            'defect_summary': {
                'chalky_indices': chalky_indices,
                'discolor_indices': discolor_indices,
                'broken_indices': broken_indices
            },
            'excel_url': excel_url,
            'kett_excel_url': kett_excel_url
        }
    
    @staticmethod
    def _save_excel_files(excel_data, base_name):
        """
        Save Excel files for quality analysis
        
        Args:
            excel_data: List of grain data dictionaries
            base_name: Base name for files
        
        Returns:
            Tuple of (excel_url, kett_excel_url)
        """
        excel_url = None
        kett_excel_url = None
        
        if not excel_data:
            return excel_url, kett_excel_url
        
        try:
            # Original Excel with all data
            excel_filename = f"{base_name}_quality_measurements.xlsx"
            df = pd.DataFrame(excel_data)
            StorageService.save_excel(df, excel_filename)
            excel_url = f"/excel/{excel_filename}"
            logger.info("Quality Excel measurements saved")
            
            # Filtered Kett Excel (non-discolored grains only)
            kett_data = [
                {
                    'Image Name': row['Image Name'],
                    'R': row['R'],
                    'G': row['G'],
                    'B': row['B']
                }
                for row in excel_data if row['Discoloration'] == 'NO'
            ]
            
            if kett_data:
                kett_excel_filename = f"{base_name}_kett.xlsx"
                kett_df = pd.DataFrame(kett_data)
                StorageService.save_excel(kett_df, kett_excel_filename)
                kett_excel_url = f"/excel/{kett_excel_filename}"
                logger.info("Kett Excel (non-discolored only) saved")
            else:
                logger.warning("No non-discolored grains for Kett Excel")
                
        except Exception as e:
            logger.error(f"Failed to create Excel: {str(e)}")
        
        return excel_url, kett_excel_url