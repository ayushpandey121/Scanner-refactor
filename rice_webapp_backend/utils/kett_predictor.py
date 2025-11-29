import numpy as np
from scipy.spatial.distance import cdist
import logging
import boto3
import pandas as pd
from io import BytesIO
import os
from config import Config

logger = logging.getLogger(__name__)


def get_model_paths_from_device_id(device_id):
    """
    Get local model file paths based on device ID
    
    Args:
        device_id: Device ID (e.g., "AGS-2001")
    
    Returns:
        tuple: (sella_path, non_sella_path)
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
    
    models_folder = os.path.join(Config.BASE_DIR, 'models')
    sella_path = os.path.join(models_folder, f'{model_number}_1.csv')
    non_sella_path = os.path.join(models_folder, f'{model_number}_2.csv')
    
    return sella_path, non_sella_path


def load_dataset_from_s3(bucket_name, file_key):
    """
    Load dataset from CSV file stored in S3

    Args:
        bucket_name: S3 bucket name
        file_key: S3 object key (path to CSV file)

    Returns:
        tuple: (kett_values, avg_r, avg_g, avg_b) as numpy arrays
    """
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')

        # Download file from S3
        logger.info(f"Downloading {file_key} from S3 bucket {bucket_name}")
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        csv_data = response['Body'].read()

        # Read CSV file
        df = pd.read_csv(BytesIO(csv_data))
        
        # Expected columns: 'Kett', 'R', 'G', 'B'
        # Adjust column names if needed
        required_columns = ['Kett', 'R', 'G', 'B']
        
        # Check if columns exist (case-insensitive)
        df.columns = df.columns.str.strip()
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower().replace('_', '')
            if 'kett' in col_lower:
                column_mapping[col] = 'Kett'
            elif col_lower in ['r', 'red', 'avgr']:
                column_mapping[col] = 'R'
            elif col_lower in ['g', 'green', 'avgg']:
                column_mapping[col] = 'G'
            elif col_lower in ['b', 'blue', 'avgb']:
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
        
        logger.info(f"Successfully loaded dataset: {len(kett_values)} samples")
        
        return kett_values, avg_r, avg_g, avg_b
        
    except Exception as e:
        logger.error(f"Error loading dataset from S3: {str(e)}")
        raise


def make_monotonic(x, y):
    """
    Make y values monotonically increasing with respect to x using isotonic regression
    while minimizing changes to the original data.
    
    Args:
        x: independent variable (e.g., Kett values)
        y: dependent variable (e.g., B-channel values)
    
    Returns:
        Monotonically increasing y values
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


def load_dataset_from_local_csv(file_path):
    """
    Load dataset from local CSV file

    Args:
        file_path: Path to local CSV file

    Returns:
        tuple: (kett_values, avg_r, avg_g, avg_b) as numpy arrays
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_path)

        # Expected columns: 'Kett', 'R', 'G', 'B'
        # Adjust column names if needed
        required_columns = ['Kett', 'R', 'G', 'B']

        # Check if columns exist (case-insensitive)
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

        logger.info(f"Successfully loaded dataset from {file_path}: {len(kett_values)} samples")

        return kett_values, avg_r, avg_g, avg_b

    except Exception as e:
        logger.error(f"Error loading dataset from {file_path}: {str(e)}")
        raise


class AccurateKettPredictor:
    """Predict Kett using B-channel interpolation with sample-type specific datasets"""

    def __init__(self, sample_type='sella', bucket_name=None, sella_file_key=None, non_sella_file_key=None, local_sella_path=None, local_non_sella_path=None, device_id=None):
        """
        Initialize predictor with specific sample type

        Args:
            sample_type: 'sella' or 'non_sella' (case insensitive)
            bucket_name: S3 bucket name (required if loading from S3)
            sella_file_key: S3 key for Sella dataset CSV file
            non_sella_file_key: S3 key for Non-Sella dataset CSV file
            local_sella_path: Local path to Sella dataset CSV file
            local_non_sella_path: Local path to Non-Sella dataset CSV file
            device_id: Device ID to auto-detect model paths (e.g., "AGS-2001")
        """
        sample_type = sample_type.lower().replace(' ', '_').replace('-', '_')

        # Auto-detect paths from device ID if provided
        if device_id and not (local_sella_path or local_non_sella_path):
            try:
                local_sella_path, local_non_sella_path = get_model_paths_from_device_id(device_id)
                logger.info(f"Auto-detected model paths for device {device_id}")
            except Exception as e:
                logger.warning(f"Could not auto-detect model paths from device ID: {e}")

        # Load dataset from local CSV or S3
        if sample_type in ['sella', 'sela']:
            if local_sella_path and os.path.exists(local_sella_path):
                self.kett_values, self.avg_r, self.avg_g, self.avg_b_original = load_dataset_from_local_csv(local_sella_path)
            elif bucket_name and sella_file_key:
                self.kett_values, self.avg_r, self.avg_g, self.avg_b_original = load_dataset_from_s3(
                    bucket_name, sella_file_key
                )
            else:
                raise ValueError("Either local_sella_path or (bucket_name and sella_file_key) are required for Sella dataset")

            self.sample_type = 'Sella'

        elif sample_type in ['non_sella', 'nonsella', 'non_sela']:
            if local_non_sella_path and os.path.exists(local_non_sella_path):
                self.kett_values, self.avg_r, self.avg_g, self.avg_b_original = load_dataset_from_local_csv(local_non_sella_path)
            elif bucket_name and non_sella_file_key:
                self.kett_values, self.avg_r, self.avg_g, self.avg_b_original = load_dataset_from_s3(
                    bucket_name, non_sella_file_key
                )
            else:
                raise ValueError("Either local_non_sella_path or (bucket_name and non_sella_file_key) are required for Non-Sella dataset")

            self.sample_type = 'Non-Sella'

        else:
            raise ValueError(f"Invalid sample type: {sample_type}. Must be 'sella' or 'non_sella'")

        # Create monotonic B-channel for interpolation
        self.avg_b = make_monotonic(self.kett_values, self.avg_b_original)

        self.all_points = np.column_stack((self.avg_r, self.avg_g, self.avg_b))

        logger.info(f"Initialized Kett Predictor for {self.sample_type}")
        logger.info(f"  Dataset size: {len(self.kett_values)} points")
        logger.info(f"  B-channel (original) range: [{np.min(self.avg_b_original):.2f}, {np.max(self.avg_b_original):.2f}]")
        logger.info(f"  B-channel (monotonic) range: [{np.min(self.avg_b):.2f}, {np.max(self.avg_b):.2f}]")
        logger.info(f"  R-channel range: [{np.min(self.avg_r):.2f}, {np.max(self.avg_r):.2f}]")

        # Log adjustments made for monotonicity
        adjustments = np.abs(self.avg_b - self.avg_b_original) > 0.01
        if np.any(adjustments):
            logger.info(f"  Monotonic adjustments made at {np.sum(adjustments)} points:")
            for i in np.where(adjustments)[0]:
                logger.info(f"    Kett={self.kett_values[i]:.1f}: {self.avg_b_original[i]:.2f} → {self.avg_b[i]:.2f}")
    
    def predict_kett(self, r, g, b):
        """
        Predict Kett using B-channel interpolation with R-channel refinement
        """
        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"Predicting Kett for RGB({r:.2f}, {g:.2f}, {b:.2f})")
            logger.info(f"  Sample Type: {self.sample_type}")
            logger.info(f"  Using B-channel interpolation (monotonic) with R-channel refinement")
            
            return self._predict_with_b_channel(r, g, b)
        
        except Exception as e:
            logger.error(f"Error predicting Kett value: {str(e)}")
            return self._simple_fallback(r, g, b)
    
    def _predict_with_b_channel(self, r, g, b):
        """Use B-channel linear interpolation between immediate neighbors"""
        # Sort B values to find bracketing points
        sorted_indices = np.argsort(self.avg_b)
        sorted_b = self.avg_b[sorted_indices]
        sorted_kett = self.kett_values[sorted_indices]
        sorted_r = self.avg_r[sorted_indices]
        
        # Find position where b would be inserted to maintain sorted order
        insert_pos = np.searchsorted(sorted_b, b)
        
        logger.info(f"\n  B-value: {b:.2f}")
        logger.info(f"  Insert position: {insert_pos} (out of {len(sorted_b)} points)")
        
        # Case 1: b is exactly at a data point (very close match)
        exact_matches = np.where(np.abs(sorted_b - b) < 0.01)[0]
        if len(exact_matches) > 0:
            # If multiple exact matches, use R-channel to choose
            if len(exact_matches) > 1:
                logger.info(f"  Strategy: Multiple exact B-matches found ({len(exact_matches)} points)")
                r_distances = [abs(sorted_r[idx] - r) for idx in exact_matches]
                best_idx = exact_matches[np.argmin(r_distances)]
                kett_pred = sorted_kett[best_idx]
                logger.info(f"    → Selected based on closest R-value")
                logger.info(f"    → Kett={kett_pred:.1f}, B={sorted_b[best_idx]:.2f}, R={sorted_r[best_idx]:.2f}")
                method = "exact_match_r_refined"
            else:
                idx = exact_matches[0]
                kett_pred = sorted_kett[idx]
                logger.info(f"  Strategy: Exact B-match")
                logger.info(f"    → Kett={kett_pred:.1f}, B={sorted_b[idx]:.2f}")
                method = "exact_match"
        
        # Case 2: b is below the minimum dataset value - LINEAR EXTRAPOLATION
        elif insert_pos == 0:
            logger.info(f"  Strategy: Below minimum B-value (linear extrapolation)")
            # Use the first two points to extrapolate
            b1, b2 = sorted_b[0], sorted_b[1]
            kett1, kett2 = sorted_kett[0], sorted_kett[1]
            
            # Calculate slope
            slope = (kett2 - kett1) / (b2 - b1)
            
            # Extrapolate
            kett_pred = kett1 + slope * (b - b1)
            
            logger.info(f"    Reference points:")
            logger.info(f"      Point 1: B={b1:.2f}, Kett={kett1:.1f}")
            logger.info(f"      Point 2: B={b2:.2f}, Kett={kett2:.1f}")
            logger.info(f"    Slope: {slope:.4f} Kett/B")
            logger.info(f"    → Extrapolated Kett: {kett_pred:.2f}")
            method = "below_range_extrapolation"
        
        # Case 3: b is above the maximum dataset value - LINEAR EXTRAPOLATION
        elif insert_pos >= len(sorted_b):
            logger.info(f"  Strategy: Above maximum B-value (linear extrapolation)")
            # Use the last two points to extrapolate
            b1, b2 = sorted_b[-2], sorted_b[-1]
            kett1, kett2 = sorted_kett[-2], sorted_kett[-1]
            
            # Calculate slope
            slope = (kett2 - kett1) / (b2 - b1)
            
            # Extrapolate
            kett_pred = kett2 + slope * (b - b2)
            
            logger.info(f"    Reference points:")
            logger.info(f"      Point 1: B={b1:.2f}, Kett={kett1:.1f}")
            logger.info(f"      Point 2: B={b2:.2f}, Kett={kett2:.1f}")
            logger.info(f"    Slope: {slope:.4f} Kett/B")
            logger.info(f"    → Extrapolated Kett: {kett_pred:.2f}")
            method = "above_range_extrapolation"
        
        # Case 4: b is between two data points - LINEAR INTERPOLATION
        else:
            lower_idx = insert_pos - 1
            upper_idx = insert_pos
            
            b_lower = sorted_b[lower_idx]
            b_upper = sorted_b[upper_idx]
            kett_lower = sorted_kett[lower_idx]
            kett_upper = sorted_kett[upper_idx]
            
            logger.info(f"  Strategy: Linear interpolation between neighbors")
            logger.info(f"    Lower: B={b_lower:.2f}, Kett={kett_lower:.1f}")
            logger.info(f"    Upper: B={b_upper:.2f}, Kett={kett_upper:.1f}")
            logger.info(f"    Input: B={b:.2f}")
            
            # Linear interpolation formula
            alpha = (b - b_lower) / (b_upper - b_lower)
            kett_pred = kett_lower + alpha * (kett_upper - kett_lower)
            
            logger.info(f"    → Interpolation factor (α): {alpha:.4f}")
            logger.info(f"    → Interpolated Kett: {kett_pred:.2f}")
            method = "linear_interpolation"
        
        logger.info(f"\n  PREDICTION: {kett_pred:.2f} (method: {method})")
        logger.info(f"{'='*70}\n")
        
        return float(kett_pred)
    
    def _simple_fallback(self, r, g, b):
        """Simple nearest neighbor fallback"""
        query_point = np.array([r, g, b])
        distances = cdist([query_point], self.all_points)[0]
        closest_idx = np.argmin(distances)
        logger.warning(f"Using fallback: nearest neighbor Kett={self.kett_values[closest_idx]:.1f}")
        return float(self.kett_values[closest_idx])


# Singleton cache for predictors
_predictor_cache = {}


def get_kett_predictor(sample_type='sella', local_sella_path=None, local_non_sella_path=None, device_id=None):
    """
    Get a Kett predictor for the specified sample type (cached)

    Args:
        sample_type: 'sella' or 'non_sella' (case insensitive)
        local_sella_path: Local path to Sella dataset CSV file
        local_non_sella_path: Local path to Non-Sella dataset CSV file
        device_id: Device ID to auto-detect model paths (e.g., "AGS-2001")

    Returns:
        AccurateKettPredictor instance
    """
    sample_type_key = sample_type.lower().replace(' ', '_').replace('-', '_')
    cache_key = f"{sample_type_key}_{local_sella_path}_{local_non_sella_path}_{device_id}"

    if cache_key not in _predictor_cache:
        _predictor_cache[cache_key] = AccurateKettPredictor(
            sample_type=sample_type,
            local_sella_path=local_sella_path,
            local_non_sella_path=local_non_sella_path,
            device_id=device_id
        )

    return _predictor_cache[cache_key]


def predict_kett(r, g, b, sample_type='sella', bucket_name=None, sella_file_key=None, non_sella_file_key=None, device_id=None):
    """
    Predict Kett value for given RGB values and sample type
    
    Args:
        r: Red channel value
        g: Green channel value
        b: Blue channel value
        sample_type: 'sella' or 'non_sella' (case insensitive)
        bucket_name: S3 bucket name
        sella_file_key: S3 key for Sella dataset CSV file (e.g., 'models_sella/2001_1.csv')
        non_sella_file_key: S3 key for Non-Sella dataset CSV file (e.g., 'models_nonsella/2001_2.csv')
        device_id: Device ID to auto-detect model paths (e.g., "AGS-2001")
    
    Returns:
        Predicted Kett value (float)
    """
    predictor = get_kett_predictor(
        sample_type=sample_type,
        bucket_name=bucket_name,
        sella_file_key=sella_file_key,
        non_sella_file_key=non_sella_file_key,
        device_id=device_id
    )
    return predictor.predict_kett(r, g, b)