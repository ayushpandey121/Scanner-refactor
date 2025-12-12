# quality/kett.py
"""
Kett whiteness prediction using B-channel interpolation with R,G refinement
Uses linear interpolation on B-channel with R,G consideration for close B values
Supports both Sella and Non-Sella rice varieties
"""

import numpy as np
import pandas as pd
import logging
import os
from scipy.spatial.distance import cdist

logger = logging.getLogger(__name__)

# Singleton cache for predictors
_predictor_cache = {}


def load_dataset_from_csv(file_path):
    """
    Load dataset from local CSV file
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        tuple: (kett_values, avg_r, avg_g, avg_b) as numpy arrays
    
    Raises:
        ValueError: If required columns are missing
        FileNotFoundError: If file doesn't exist
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file not found: {file_path}")
        
        # Read CSV file
        df = pd.read_csv(file_path)

        # Expected columns: 'Kett', 'R', 'G', 'B'
        required_columns = ['Kett', 'R', 'G', 'B']

        # Normalize column names (case-insensitive)
        df.columns = df.columns.str.strip()

        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            col_norm = col_lower.replace(" ", "").replace("_", "")

            if "kett" in col_norm:
                column_mapping[col] = "Kett"
            elif col_norm in ["r", "red", "avgr"]:
                column_mapping[col] = "R"
            elif col_norm in ["g", "green", "avgg"]:
                column_mapping[col] = "G"
            elif col_norm in ["b", "blue", "avgb"]:
                column_mapping[col] = "B"

        df = df.rename(columns=column_mapping)

        # Validate required columns exist
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Extract data as numpy arrays
        kett_values = df['Kett'].values.astype(float)
        avg_r = df['R'].values.astype(float)
        avg_g = df['G'].values.astype(float)
        avg_b = df['B'].values.astype(float)

        return kett_values, avg_r, avg_g, avg_b

    except Exception as e:
        logger.error(f"Error loading dataset from {file_path}: {str(e)}")
        raise


def get_model_paths_from_device_id(device_id, models_base_dir):
    """
    Get local model file paths based on device ID
    
    Args:
        device_id: Device ID (e.g., "AGS-2001")
        models_base_dir: Base directory containing model files
    
    Returns:
        tuple: (sella_path, non_sella_path)
    
    Raises:
        ValueError: If device ID format is invalid
    """
    import re
    
    # Extract model number from device ID
    match = re.search(r'-(\d+)$', device_id)
    if match:
        model_number = match.group(1)
    else:
        match = re.search(r'(\d{4})', device_id)
        if match:
            model_number = match.group(1)
        else:
            raise ValueError(f"Could not extract model number from device ID: {device_id}")
    
    sella_path = os.path.join(models_base_dir, f'{model_number}_1.csv')
    non_sella_path = os.path.join(models_base_dir, f'{model_number}_2.csv')
    
    return sella_path, non_sella_path


class KettPredictor:
    """
    Kett whiteness predictor using B-channel interpolation with R,G refinement
    
    Uses linear interpolation on B-channel. When B values are close (within threshold),
    considers R,G channels for better accuracy. Handles edge cases for B values outside
    the dataset range.
    
    Attributes:
        sample_type: 'Sella' or 'Non-Sella'
        kett_values: Array of Kett reference values
        avg_r, avg_g, avg_b: RGB channel arrays
        all_points: Combined RGB array
        b_close_threshold: Threshold for considering B values as "close" (default: 0.5)
    """
    
    def __init__(self, model_path, sample_type='sella', b_close_threshold=0.5):
        """
        Initialize Kett predictor
        
        Args:
            model_path: Path to model CSV file
            sample_type: 'sella' or 'non_sella' (case insensitive)
            b_close_threshold: Threshold for B-channel proximity (default: 0.5)
        
        Raises:
            ValueError: If sample type is invalid or model file cannot be loaded
        """
        sample_type_normalized = sample_type.lower().replace(' ', '_').replace('-', '_')
        
        if sample_type_normalized in ['sella', 'sela']:
            self.sample_type = 'Sella'
        elif sample_type_normalized in ['non_sella', 'nonsella', 'non_sela']:
            self.sample_type = 'Non-Sella'
        else:
            raise ValueError(
                f"Invalid sample type: {sample_type}. "
                f"Must be 'sella' or 'non_sella'"
            )
        
        # Load dataset
        self.kett_values, self.avg_r, self.avg_g, self.avg_b = \
            load_dataset_from_csv(model_path)
        
        # Set B-channel close threshold
        self.b_close_threshold = b_close_threshold
        
        # Create combined RGB array
        self.all_points = np.column_stack((self.avg_r, self.avg_g, self.avg_b))
        
        # Sort dataset by B channel for efficient interpolation
        self.b_sorted_indices = np.argsort(self.avg_b)
        self.b_sorted = self.avg_b[self.b_sorted_indices]
        self.kett_sorted = self.kett_values[self.b_sorted_indices]
        self.r_sorted = self.avg_r[self.b_sorted_indices]
        self.g_sorted = self.avg_g[self.b_sorted_indices]
        
        logger.info(f"Initialized Kett Predictor for {self.sample_type}")
        logger.info(f"  Dataset size: {len(self.kett_values)} points")
        logger.info(f"  B-channel close threshold: {self.b_close_threshold}")
        logger.info(
            f"  R-channel range: "
            f"[{np.min(self.avg_r):.2f}, {np.max(self.avg_r):.2f}]"
        )
        logger.info(
            f"  G-channel range: "
            f"[{np.min(self.avg_g):.2f}, {np.max(self.avg_g):.2f}]"
        )
        logger.info(
            f"  B-channel range: "
            f"[{np.min(self.avg_b):.2f}, {np.max(self.avg_b):.2f}]"
        )
        logger.info(
            f"  Kett range: "
            f"[{np.min(self.kett_values):.1f}, {np.max(self.kett_values):.1f}]"
        )
    
    def predict(self, r, g, b):
        """
        Predict Kett value using B-channel interpolation with R,G refinement
        
        Args:
            r: Red channel value (0-255)
            g: Green channel value (0-255)
            b: Blue channel value (0-255)
        
        Returns:
            float: Predicted Kett whiteness value
        
        Example:
            >>> predictor = KettPredictor('models/2001_1.csv', 'sella')
            >>> kett = predictor.predict(r=150, g=140, b=135)
            >>> print(f"Kett value: {kett:.2f}")
        """
        try:
            logger.info("="*70)
            logger.info(f"Predicting Kett for RGB({r:.2f}, {g:.2f}, {b:.2f})")
            logger.info(f"  Sample Type: {self.sample_type}")
            logger.info(f"  Using B-channel interpolation with R,G refinement")
            
            return self._predict_b_interpolation(r, g, b)
        
        except Exception as e:
            logger.error(f"Error predicting Kett value: {str(e)}")
            raise
    
    def _predict_b_interpolation(self, r, g, b):
        """
        B-channel linear interpolation with R,G refinement for close B values
        """
        b_min = self.b_sorted[0]
        b_max = self.b_sorted[-1]
        
        # Case 1: B value below minimum in dataset
        if b < b_min:
            logger.info(f"  B={b:.2f} is below dataset minimum ({b_min:.2f})")
            # Find closest point by R,G among lowest B values
            lower_b_mask = self.b_sorted <= (b_min + self.b_close_threshold)
            candidates_idx = np.where(lower_b_mask)[0]
            
            if len(candidates_idx) > 0:
                candidates_idx_original = self.b_sorted_indices[candidates_idx]
                rg_distances = np.sqrt(
                    (self.avg_r[candidates_idx_original] - r)**2 + 
                    (self.avg_g[candidates_idx_original] - g)**2
                )
                best_idx_in_candidates = np.argmin(rg_distances)
                best_idx = candidates_idx_original[best_idx_in_candidates]
                
                # Extrapolate based on B difference
                b_diff = b - self.avg_b[best_idx]
                # Assume linear trend: slight adjustment based on B difference
                kett_pred = self.kett_values[best_idx] + b_diff * 0.5
                
                logger.info(f"  Using closest R,G match: RGB({self.avg_r[best_idx]:.1f}, "
                          f"{self.avg_g[best_idx]:.1f}, {self.avg_b[best_idx]:.1f}), "
                          f"Kett={self.kett_values[best_idx]:.1f}")
                logger.info(f"  Extrapolated Kett: {kett_pred:.2f}")
            else:
                kett_pred = self.kett_sorted[0]
                logger.info(f"  Using minimum Kett: {kett_pred:.2f}")
            
            logger.info(f"\n  PREDICTION: {kett_pred:.2f}")
            logger.info("="*70 + "\n")
            return float(kett_pred)
        
        # Case 2: B value above maximum in dataset
        if b > b_max:
            logger.info(f"  B={b:.2f} is above dataset maximum ({b_max:.2f})")
            # Find closest point by R,G among highest B values
            upper_b_mask = self.b_sorted >= (b_max - self.b_close_threshold)
            candidates_idx = np.where(upper_b_mask)[0]
            
            if len(candidates_idx) > 0:
                candidates_idx_original = self.b_sorted_indices[candidates_idx]
                rg_distances = np.sqrt(
                    (self.avg_r[candidates_idx_original] - r)**2 + 
                    (self.avg_g[candidates_idx_original] - g)**2
                )
                best_idx_in_candidates = np.argmin(rg_distances)
                best_idx = candidates_idx_original[best_idx_in_candidates]
                
                # Extrapolate based on B difference
                b_diff = b - self.avg_b[best_idx]
                kett_pred = self.kett_values[best_idx] + b_diff * 0.5
                
                logger.info(f"  Using closest R,G match: RGB({self.avg_r[best_idx]:.1f}, "
                          f"{self.avg_g[best_idx]:.1f}, {self.avg_b[best_idx]:.1f}), "
                          f"Kett={self.kett_values[best_idx]:.1f}")
                logger.info(f"  Extrapolated Kett: {kett_pred:.2f}")
            else:
                kett_pred = self.kett_sorted[-1]
                logger.info(f"  Using maximum Kett: {kett_pred:.2f}")
            
            logger.info(f"\n  PREDICTION: {kett_pred:.2f}")
            logger.info("="*70 + "\n")
            return float(kett_pred)
        
        # Case 3: B value within dataset range
        # Find bracketing B values
        right_idx = np.searchsorted(self.b_sorted, b)
        
        # Check if exact match or very close
        if right_idx < len(self.b_sorted):
            b_diff_right = abs(self.b_sorted[right_idx] - b)
            if b_diff_right < 1e-6:
                # Exact match - check for close B values
                return self._handle_close_b_values(r, g, b, right_idx)
        
        if right_idx > 0:
            b_diff_left = abs(self.b_sorted[right_idx - 1] - b)
            if b_diff_left < 1e-6:
                # Exact match - check for close B values
                return self._handle_close_b_values(r, g, b, right_idx - 1)
        
        # Linear interpolation between bracketing points
        left_idx = right_idx - 1
        
        b_left = self.b_sorted[left_idx]
        b_right = self.b_sorted[right_idx]
        
        logger.info(f"  Interpolating between:")
        logger.info(f"    Left:  B={b_left:.2f}, Kett={self.kett_sorted[left_idx]:.1f}")
        logger.info(f"    Right: B={b_right:.2f}, Kett={self.kett_sorted[right_idx]:.1f}")
        
        # Check if bracketing B values are close
        if abs(b_right - b_left) <= self.b_close_threshold:
            logger.info(f"  Bracketing B values are close (diff={abs(b_right - b_left):.3f})")
            # Consider R,G for both bracketing points
            left_idx_original = self.b_sorted_indices[left_idx]
            right_idx_original = self.b_sorted_indices[right_idx]
            
            rg_dist_left = np.sqrt(
                (self.avg_r[left_idx_original] - r)**2 + 
                (self.avg_g[left_idx_original] - g)**2
            )
            rg_dist_right = np.sqrt(
                (self.avg_r[right_idx_original] - r)**2 + 
                (self.avg_g[right_idx_original] - g)**2
            )
            
            logger.info(f"    Left R,G distance: {rg_dist_left:.2f}")
            logger.info(f"    Right R,G distance: {rg_dist_right:.2f}")
            
            # Weight by inverse R,G distance
            weight_left = 1.0 / (rg_dist_left + 1e-6)
            weight_right = 1.0 / (rg_dist_right + 1e-6)
            total_weight = weight_left + weight_right
            
            kett_pred = (
                self.kett_sorted[left_idx] * weight_left + 
                self.kett_sorted[right_idx] * weight_right
            ) / total_weight
            
            # Add slight variation to avoid exact value
            kett_pred += np.random.uniform(-0.1, 0.1)
            
            logger.info(f"  R,G-weighted interpolation: {kett_pred:.2f}")
        else:
            # Standard linear interpolation on B
            t = (b - b_left) / (b_right - b_left)
            kett_pred = self.kett_sorted[left_idx] * (1 - t) + self.kett_sorted[right_idx] * t
            logger.info(f"  Linear interpolation (t={t:.3f}): {kett_pred:.2f}")
        
        logger.info(f"\n  PREDICTION: {kett_pred:.2f}")
        logger.info("="*70 + "\n")
        return float(kett_pred)
    
    def _handle_close_b_values(self, r, g, b, exact_idx):
        """
        Handle case where multiple points have close B values
        """
        # Find all points with B values close to target
        close_mask = np.abs(self.b_sorted - b) <= self.b_close_threshold
        close_indices_sorted = np.where(close_mask)[0]
        
        if len(close_indices_sorted) <= 1:
            # Only one match, return its Kett value
            return float(self.kett_sorted[exact_idx])
        
        logger.info(f"  Found {len(close_indices_sorted)} points with close B values")
        
        # Get original indices
        close_indices_original = self.b_sorted_indices[close_indices_sorted]
        
        # Calculate R,G distances
        rg_distances = np.sqrt(
            (self.avg_r[close_indices_original] - r)**2 + 
            (self.avg_g[close_indices_original] - g)**2
        )
        
        # Find closest by R,G
        best_idx_in_close = np.argmin(rg_distances)
        best_idx = close_indices_original[best_idx_in_close]
        
        logger.info(f"  Closest R,G match: RGB({self.avg_r[best_idx]:.1f}, "
                  f"{self.avg_g[best_idx]:.1f}, {self.avg_b[best_idx]:.1f}), "
                  f"Kett={self.kett_values[best_idx]:.1f}")
        
        # Return value near the closest, but not exact
        kett_base = self.kett_values[best_idx]
        kett_pred = kett_base + np.random.uniform(-0.15, 0.15)
        
        logger.info(f"  Base Kett: {kett_base:.2f}, Adjusted: {kett_pred:.2f}")
        logger.info(f"\n  PREDICTION: {kett_pred:.2f}")
        logger.info("="*70 + "\n")
        
        return float(kett_pred)


def get_kett_predictor(sample_type='sella', model_path=None, device_id=None, 
                       models_base_dir=None, b_close_threshold=0.5):
    """
    Get cached Kett predictor instance
    
    Args:
        sample_type: 'sella' or 'non_sella' (case insensitive)
        model_path: Direct path to model file (overrides device_id)
        device_id: Device ID to auto-detect paths (e.g., "AGS-2001")
        models_base_dir: Base directory for models (default: from config)
        b_close_threshold: Threshold for B-channel proximity (default: 0.5)
    
    Returns:
        KettPredictor: Cached predictor instance
    
    Example:
        >>> predictor = get_kett_predictor('sella', device_id='AGS-2001')
        >>> kett = predictor.predict(150, 140, 135)
    """
    # Determine model path
    if model_path is None:
        if device_id is None:
            raise ValueError("Either model_path or device_id must be provided")
        
        # Get models base directory
        if models_base_dir is None:
            from config.settings import Config
            models_base_dir = os.path.join(Config.BASE_DIR, 'models')
        
        # Get paths from device ID
        sella_path, non_sella_path = get_model_paths_from_device_id(
            device_id, models_base_dir
        )
        
        sample_type_normalized = sample_type.lower().replace(' ', '_').replace('-', '_')
        if sample_type_normalized in ['sella', 'sela']:
            model_path = sella_path
        else:
            model_path = non_sella_path
    
    # Create cache key
    cache_key = f"{sample_type}_{model_path}_{b_close_threshold}"
    
    # Return cached predictor or create new one
    if cache_key not in _predictor_cache:
        _predictor_cache[cache_key] = KettPredictor(
            model_path, sample_type, b_close_threshold
        )
    
    return _predictor_cache[cache_key]


def predict_kett(r, g, b, sample_type='sella', model_path=None, device_id=None,
                models_base_dir=None, b_close_threshold=0.5):
    """
    Predict Kett value for given RGB values using B-channel interpolation
    
    Args:
        r: Red channel value (0-255)
        g: Green channel value (0-255)
        b: Blue channel value (0-255)
        sample_type: 'sella' or 'non_sella'
        model_path: Direct path to model file
        device_id: Device ID to auto-detect paths
        models_base_dir: Base directory for models
        b_close_threshold: Threshold for B-channel proximity (default: 0.5)
    
    Returns:
        float: Predicted Kett whiteness value
    
    Example:
        >>> kett = predict_kett(150, 140, 135, 'sella', device_id='AGS-2001')
    """
    predictor = get_kett_predictor(
        sample_type=sample_type,
        model_path=model_path,
        device_id=device_id,
        models_base_dir=models_base_dir,
        b_close_threshold=b_close_threshold
    )
    return predictor.predict(r, g, b)