# services/prediction_service.py
import os
import logging
import numpy as np
import pandas as pd
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


class PredictionService:
    """Handle prediction workflows"""
    
    @staticmethod
    def predict_grains(grain_images, padded_dir, filename_to_coords,
                      pixels_per_metric, minlen, chalky_percentage, base_name,
                      exclude_flags_dict=None, rice_variety='non_sella', device_id=None):
        """
        Predict grain characteristics and generate results
        
        Args:
            grain_images: List of grain image filenames
            padded_dir: Directory containing padded grain images
            filename_to_coords: Dictionary mapping filenames to coordinates
            pixels_per_metric: Pixels per metric value
            minlen: Minimum length threshold
            chalky_percentage: Chalky percentage threshold
            base_name: Base name for output files
            exclude_flags_dict: Dictionary mapping filenames to exclusion flags
            rice_variety: Rice variety for Kett prediction ('sella' or 'non_sella')
            device_id: Optional device ID (will auto-detect from local files if not provided)
        
        Returns:
            dict: Prediction results
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
        
        logger.info("Starting grain prediction")
        
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
        
        # FIRST PASS: Collect RGB values for sample type determination and (B-R) statistics
        rgb_values, grain_features = GrainService.collect_rgb_values(
            grain_paths, pixels_per_metric, exclude_flags
        )
        
        # Determine sample type and calculate (B-R) statistics
        if rgb_values:
            # Correctly unpack all three RGB values
            avg_r_all = sum(r for r, g, b in rgb_values) / len(rgb_values)
            avg_g_all = sum(g for r, g, b in rgb_values) / len(rgb_values)
            avg_b_all = sum(b for r, g, b in rgb_values) / len(rgb_values)
            
            # Calculate (B-R) value statistics
            br_values = [b - r for r, g, b in rgb_values]
            avg_br = float(np.mean(br_values))
            std_br = float(np.std(br_values))
            
            sample_type = determine_sample_type(avg_r_all, avg_b_all)
            logger.info(f"Sample type determined: {sample_type} (avg_R={avg_r_all:.2f}, avg_B={avg_b_all:.2f})")
            logger.info(f"(B-R) statistics: avg(B-R)={avg_br:.2f}, std(B-R)={std_br:.2f}, threshold={avg_br - 12:.2f}")
        else:
            sample_type = "White"
            avg_r_all = 0.0
            avg_g_all = 0.0
            avg_b_all = 0.0
            avg_br = 0.0
            std_br = 0.0
            logger.warning("No RGB values collected, defaulting to White sample type")
        
        # SECOND PASS: Process individual grains (skip excluded ones)
        grains = []
        excel_data = []
        
        # For RGB averages
        all_rgb_values = []
        chalky_rgb_values = []
        non_chalky_rgb_values = []
        
        for grain_img in grain_images:
            grain_path = os.path.join(padded_dir, grain_img)
            grain_coords = filename_to_coords.get(grain_img, [])
            exclude_grain = exclude_flags_dict.get(grain_img, False)
            
            # Analyze grain (will skip if excluded)
            grain_data, oriented_path, feature_dict = GrainService.analyze_grain(
                grain_path, pixels_per_metric, grain_coords, minlen, chalky_percentage, exclude_grain
            )
            
            if not grain_data or not oriented_path or not feature_dict:
                if not exclude_grain:
                    logger.warning(f"Skipping grain {grain_img} due to processing errors")
                continue
            
            # Get RGB values and classify using (B-R) threshold
            feature_dict = grain_features.get(grain_img, feature_dict)
            processed_grain = GrainService.process_grain_with_classification(
                grain_path, grain_img, feature_dict, avg_br,
                pixels_per_metric, minlen, chalky_percentage, exclude_grain
            )
            
            if not processed_grain:
                continue
            
            # Collect RGB values for all grains
            all_rgb_values.append({
                'R': processed_grain['R'],
                'G': processed_grain['G'],
                'B': processed_grain['B']
            })

            # Check if grain is chalky and collect RGB values
            is_chalky = grain_data["chalky"] == "Yes"
            if is_chalky:
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
            
            # Update grain_data with classification and RGB values
            grain_data["discolor"] = processed_grain['discoloration_class']
            grain_data["R"] = processed_grain['R']
            grain_data["G"] = processed_grain['G']
            grain_data["B"] = processed_grain['B']
            
            # Build Excel data
            excel_data.append({
                'Image Name': grain_img,
                'Length (mm)': round(processed_grain['length'], 2),
                'Breadth (mm)': round(processed_grain['breadth'], 2),
                'R': round(processed_grain['R'], 2),
                'G': round(processed_grain['G'], 2),
                'B': round(processed_grain['B'], 2),
                'B-R': round(processed_grain['B'] - processed_grain['R'], 2),
                'Discoloration': processed_grain['discoloration_class'],
                'Chalky': grain_data["chalky"]
            })
            
            # Save oriented grain image
            oriented_basename = os.path.basename(oriented_path)
            grain_relative_path = StorageService.save_grain_image(
                oriented_path, base_name, oriented_basename
            )
            grain_data["grain_url"] = f"http://localhost:{Config.PORT}/grain-image/{grain_relative_path}"
            
            grains.append(grain_data)
        
        logger.info(f"Processed {len(grains)} included grains (excluded {excluded_count} large grains)")
        
        # ========================================================================
        # Calculate statistics with device_id for automatic model path detection
        # ========================================================================
        logger.info(f"📊 Calculating statistics with device_id: {device_id}")
        statistics = calculate_statistics(
            grains,
            rice_variety=rice_variety,
            full_rgb_avg={'R': avg_r_all, 'G': avg_g_all, 'B': avg_b_all},
            device_id=device_id  # Pass device_id for automatic model detection
        )
        # ========================================================================
        
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
            logger.info(f"  Average (B-R): {avg_all_b - avg_all_r:.2f}")

        # Non-chalky grains RGB averages
        if non_chalky_rgb_values:
            avg_non_chalky_r = sum(g['R'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)
            avg_non_chalky_g = sum(g['G'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)
            avg_non_chalky_b = sum(g['B'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)

            logger.info(f"NON-CHALKY GRAINS RGB AVERAGES ({len(non_chalky_rgb_values)} grains):")
            logger.info(f"  Average R: {avg_non_chalky_r:.2f}")
            logger.info(f"  Average G: {avg_non_chalky_g:.2f}")
            logger.info(f"  Average B: {avg_non_chalky_b:.2f}")
            logger.info(f"  Average (B-R): {avg_non_chalky_b - avg_non_chalky_r:.2f}")

        # Chalky grains RGB averages
        if chalky_rgb_values:
            avg_chalky_r = sum(g['R'] for g in chalky_rgb_values) / len(chalky_rgb_values)
            avg_chalky_g = sum(g['G'] for g in chalky_rgb_values) / len(chalky_rgb_values)
            avg_chalky_b = sum(g['B'] for g in chalky_rgb_values) / len(chalky_rgb_values)

            logger.info(f"CHALKY GRAINS RGB AVERAGES ({len(chalky_rgb_values)} grains):")
            logger.info(f"  Average R: {avg_chalky_r:.2f}")
            logger.info(f"  Average G: {avg_chalky_g:.2f}")
            logger.info(f"  Average B: {avg_chalky_b:.2f}")
            logger.info(f"  Average (B-R): {avg_chalky_b - avg_chalky_r:.2f}")

            # Add to statistics
            statistics['chalky_rgb_avg'] = {
                'R': round(avg_chalky_r, 2),
                'G': round(avg_chalky_g, 2),
                'B': round(avg_chalky_b, 2),
                'count': len(chalky_rgb_values)
            }
        else:
            logger.info("No chalky grains detected")

        # Add all and non-chalky RGB averages to statistics
        if all_rgb_values:
            statistics['all_rgb_avg'] = {
                'R': round(avg_all_r, 2),
                'G': round(avg_all_g, 2),
                'B': round(avg_all_b, 2),
                'count': len(all_rgb_values)
            }

        if non_chalky_rgb_values:
            statistics['non_chalky_rgb_avg'] = {
                'R': round(avg_non_chalky_r, 2),
                'G': round(avg_non_chalky_g, 2),
                'B': round(avg_non_chalky_b, 2),
                'count': len(non_chalky_rgb_values)
            }

        logger.info("=" * 60)
        
        # Save Excel files
        excel_url, kett_excel_url = PredictionService._save_excel_files(
            excel_data, base_name
        )
        
        return {
            'sample_type': sample_type,
            'statistics': statistics,
            'grains': grains,
            'excel_url': excel_url,
            'kett_excel_url': kett_excel_url
        }
    
    @staticmethod
    def _save_excel_files(excel_data, base_name):
        """
        Save Excel files for predictions
        
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
            # Original Excel with all data (including B-R column)
            excel_filename = f"{base_name}_measurements.xlsx"
            df = pd.DataFrame(excel_data)
            StorageService.save_excel(df, excel_filename)
            excel_url = f"/excel/{excel_filename}"
            logger.info("Excel measurements saved")
            
            # Filtered Kett Excel (non-discolored grains only)
            kett_data = [
                {
                    'Image Name': row['Image Name'],
                    'R': row['R'],
                    'G': row['G'],
                    'B': row['B'],
                    'B-R': row['B-R']
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