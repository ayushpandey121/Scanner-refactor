# quality/kett.py
"""
Kett whiteness prediction using B-channel interpolation
Uses monotonic B-channel interpolation with R-channel refinement
Supports both Sella and Non-Sella rice varieties
"""

import numpy as np
import pandas as pd
import logging
import os
from io import BytesIO
from scipy.spatial.distance import cdist

logger = logging.getLogger(__name__)

# Singleton cache for predictors
_predictor_cache = {}


def make_monotonic(x, y):
    """
    Make y values monotonically increasing with respect to x using isotonic regression
    
    Args:
        x: Independent variable (e.g., Kett values)
        y: Dependent variable (e.g., B-channel values)
    
    Returns:
        np.ndarray: Monotonically increasing y values
    """
    # Sort by x first
    sort_idx = np.argsort(x)
    x_sorted = x[sort_idx]
    y_sorted = y[sort_idx]
    
    # Apply pool-adjacent-violators algorithm (isotonic regression)
    y_mono = np.copy(y_sorted)
    n = len(y_mono)
    
    # Forward pass: ensure each value >= previous
    for i in range(1, n):
        if y_mono[i] < y_mono[i-1]:
            # Average the violating values
            j = i
            sum_y = y_mono[i]
            count = 1
            
            # Look backward to find the block of violations
            while j > 0 and y_mono[j-1] > y_mono[i]:
                j -= 1
                sum_y += y_mono[j]
                count += 1
            
            # Set all values in the block to their average
            avg = sum_y / count
            for k in range(j, i+1):
                y_mono[k] = avg
    
    # Unsort to match original order
    unsort_idx = np.argsort(sort_idx)
    return y_mono[unsort_idx]


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
            if 'kett' in col_lower:
                column_mapping[col] = 'Kett'
            elif col_lower in ['r', 'red', 'avg_r']:
                column_mapping[col] = 'R'
            elif col_lower in ['g', 'green', 'avg_g']:
                column_mapping[col] = 'G'
            elif col_lower in ['b', 'blue', 'avg_b']:
                column_mapping[col] = 'B'

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

        logger.info(
            f"Successfully loaded dataset from {file_path}: "
            f"{len(kett_values)} samples"
        )

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
    Kett whiteness predictor using B-channel interpolation
    
    Attributes:
        sample_type: 'Sella' or 'Non-Sella'
        kett_values: Array of Kett reference values
        avg_r, avg_g, avg_b: RGB channel arrays
        avg_b_original: Original B values before monotonic adjustment
    """
    
    def __init__(self, model_path, sample_type='sella'):
        """
        Initialize Kett predictor
        
        Args:
            model_path: Path to model CSV file
            sample_type: 'sella' or 'non_sella' (case insensitive)
        
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
        self.kett_values, self.avg_r, self.avg_g, self.avg_b_original = \
            load_dataset_from_csv(model_path)
        
        # Create monotonic B-channel for interpolation
        self.avg_b = make_monotonic(self.kett_values, self.avg_b_original)
        
        self.all_points = np.column_stack((self.avg_r, self.avg_g, self.avg_b))
        
        logger.info(f"Initialized Kett Predictor for {self.sample_type}")
        logger.info(f"  Dataset size: {len(self.kett_values)} points")
        logger.info(
            f"  B-channel (original) range: "
            f"[{np.min(self.avg_b_original):.2f}, {np.max(self.avg_b_original):.2f}]"
        )
        logger.info(
            f"  B-channel (monotonic) range: "
            f"[{np.min(self.avg_b):.2f}, {np.max(self.avg_b):.2f}]"
        )
        logger.info(
            f"  R-channel range: "
            f"[{np.min(self.avg_r):.2f}, {np.max(self.avg_r):.2f}]"
        )
        
        # Log adjustments made for monotonicity
        adjustments = np.abs(self.avg_b - self.avg_b_original) > 0.01
        if np.any(adjustments):
            logger.info(
                f"  Monotonic adjustments made at {np.sum(adjustments)} points:"
            )
            for i in np.where(adjustments)[0]:
                logger.info(
                    f"    Kett={self.kett_values[i]:.1f}: "
                    f"{self.avg_b_original[i]:.2f} → {self.avg_b[i]:.2f}"
                )
    
    def predict(self, r, g, b):
        """
        Predict Kett value using B-channel interpolation
        
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
            logger.info("  Using B-channel interpolation with R-channel refinement")
            
            return self._predict_with_b_channel(r, g, b)
        
        except Exception as e:
            logger.error(f"Error predicting Kett value: {str(e)}")
            return self._simple_fallback(r, g, b)
    
    def _predict_with_b_channel(self, r, g, b):
        """Use B-channel linear interpolation between immediate neighbors"""
        # Sort B values
        sorted_indices = np.argsort(self.avg_b)
        sorted_b = self.avg_b[sorted_indices]
        sorted_kett = self.kett_values[sorted_indices]
        sorted_r = self.avg_r[sorted_indices]
        
        # Find insertion position
        insert_pos = np.searchsorted(sorted_b, b)
        
        logger.info(f"\n  B-value: {b:.2f}")
        logger.info(f"  Insert position: {insert_pos} (out of {len(sorted_b)} points)")
        
        # Case 1: Exact match
        exact_matches = np.where(np.abs(sorted_b - b) < 0.01)[0]
        if len(exact_matches) > 0:
            if len(exact_matches) > 1:
                logger.info(
                    f"  Strategy: Multiple exact B-matches found "
                    f"({len(exact_matches)} points)"
                )
                r_distances = [abs(sorted_r[idx] - r) for idx in exact_matches]
                best_idx = exact_matches[np.argmin(r_distances)]
                kett_pred = sorted_kett[best_idx]
                logger.info("    → Selected based on closest R-value")
                logger.info(
                    f"    → Kett={kett_pred:.1f}, B={sorted_b[best_idx]:.2f}, "
                    f"R={sorted_r[best_idx]:.2f}"
                )
                method = "exact_match_r_refined"
            else:
                idx = exact_matches[0]
                kett_pred = sorted_kett[idx]
                logger.info("  Strategy: Exact B-match")
                logger.info(f"    → Kett={kett_pred:.1f}, B={sorted_b[idx]:.2f}")
                method = "exact_match"
        
        # Case 2: Below minimum - LINEAR EXTRAPOLATION
        elif insert_pos == 0:
            logger.info("  Strategy: Below minimum B-value (linear extrapolation)")
            b1, b2 = sorted_b[0], sorted_b[1]
            kett1, kett2 = sorted_kett[0], sorted_kett[1]
            
            slope = (kett2 - kett1) / (b2 - b1)
            kett_pred = kett1 + slope * (b - b1)
            
            logger.info("    Reference points:")
            logger.info(f"      Point 1: B={b1:.2f}, Kett={kett1:.1f}")
            logger.info(f"      Point 2: B={b2:.2f}, Kett={kett2:.1f}")
            logger.info(f"    Slope: {slope:.4f} Kett/B")
            logger.info(f"    → Extrapolated Kett: {kett_pred:.2f}")
            method = "below_range_extrapolation"
        
        # Case 3: Above maximum - LINEAR EXTRAPOLATION
        elif insert_pos >= len(sorted_b):
            logger.info("  Strategy: Above maximum B-value (linear extrapolation)")
            b1, b2 = sorted_b[-2], sorted_b[-1]
            kett1, kett2 = sorted_kett[-2], sorted_kett[-1]
            
            slope = (kett2 - kett1) / (b2 - b1)
            kett_pred = kett2 + slope * (b - b2)
            
            logger.info("    Reference points:")
            logger.info(f"      Point 1: B={b1:.2f}, Kett={kett1:.1f}")
            logger.info(f"      Point 2: B={b2:.2f}, Kett={kett2:.1f}")
            logger.info(f"    Slope: {slope:.4f} Kett/B")
            logger.info(f"    → Extrapolated Kett: {kett_pred:.2f}")
            method = "above_range_extrapolation"
        
        # Case 4: Between two points - LINEAR INTERPOLATION
        else:
            lower_idx = insert_pos - 1
            upper_idx = insert_pos
            
            b_lower = sorted_b[lower_idx]
            b_upper = sorted_b[upper_idx]
            kett_lower = sorted_kett[lower_idx]
            kett_upper = sorted_kett[upper_idx]
            
            logger.info("  Strategy: Linear interpolation between neighbors")
            logger.info(f"    Lower: B={b_lower:.2f}, Kett={kett_lower:.1f}")
            logger.info(f"    Upper: B={b_upper:.2f}, Kett={kett_upper:.1f}")
            logger.info(f"    Input: B={b:.2f}")
            
            alpha = (b - b_lower) / (b_upper - b_lower)
            kett_pred = kett_lower + alpha * (kett_upper - kett_lower)
            
            logger.info(f"    → Interpolation factor (α): {alpha:.4f}")
            logger.info(f"    → Interpolated Kett: {kett_pred:.2f}")
            method = "linear_interpolation"
        
        logger.info(f"\n  PREDICTION: {kett_pred:.2f} (method: {method})")
        logger.info("="*70 + "\n")
        
        return float(kett_pred)
    
    def _simple_fallback(self, r, g, b):
        """Simple nearest neighbor fallback"""
        query_point = np.array([r, g, b])
        distances = cdist([query_point], self.all_points)[0]
        closest_idx = np.argmin(distances)
        logger.warning(
            f"Using fallback: nearest neighbor Kett={self.kett_values[closest_idx]:.1f}"
        )
        return float(self.kett_values[closest_idx])


def get_kett_predictor(sample_type='sella', model_path=None, device_id=None, 
                       models_base_dir=None):
    """
    Get cached Kett predictor instance
    
    Args:
        sample_type: 'sella' or 'non_sella' (case insensitive)
        model_path: Direct path to model file (overrides device_id)
        device_id: Device ID to auto-detect paths (e.g., "AGS-2001")
        models_base_dir: Base directory for models (default: from config)
    
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
    cache_key = f"{sample_type}_{model_path}"
    
    # Return cached predictor or create new one
    if cache_key not in _predictor_cache:
        _predictor_cache[cache_key] = KettPredictor(model_path, sample_type)
    
    return _predictor_cache[cache_key]


def predict_kett(r, g, b, sample_type='sella', model_path=None, device_id=None,
                models_base_dir=None):
    """
    Predict Kett value for given RGB values
    
    Args:
        r: Red channel value (0-255)
        g: Green channel value (0-255)
        b: Blue channel value (0-255)
        sample_type: 'sella' or 'non_sella'
        model_path: Direct path to model file
        device_id: Device ID to auto-detect paths
        models_base_dir: Base directory for models
    
    Returns:
        float: Predicted Kett whiteness value
    
    Example:
        >>> kett = predict_kett(150, 140, 135, 'sella', device_id='AGS-2001')
        >>> print(f"Kett: {kett:.2f}")
    """
    predictor = get_kett_predictor(
        sample_type=sample_type,
        model_path=model_path,
        device_id=device_id,
        models_base_dir=models_base_dir
    )
    return predictor.predict(r, g, b)