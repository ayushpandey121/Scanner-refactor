# quality/kett.py
"""
Kett whiteness prediction using Weighted RGB Distance
Uses weighted Euclidean distance with B-channel priority
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
    Kett whiteness predictor using Weighted RGB Distance
    
    B-channel is weighted more heavily as it correlates best with Kett values.
    Uses K-Nearest Neighbors with weighted Euclidean distance.
    
    Attributes:
        sample_type: 'Sella' or 'Non-Sella'
        kett_values: Array of Kett reference values
        avg_r, avg_g, avg_b: RGB channel arrays
        all_points: Combined RGB array
        weights: Channel weights [w_r, w_g, w_b]
    """
    
    def __init__(self, model_path, sample_type='sella', 
                 weights=None, k_neighbors=5):
        """
        Initialize Kett predictor
        
        Args:
            model_path: Path to model CSV file
            sample_type: 'sella' or 'non_sella' (case insensitive)
            weights: RGB channel weights [w_r, w_g, w_b]. 
                    Default: [1.0, 1.0, 3.0] (B-channel 3x weight)
            k_neighbors: Number of nearest neighbors for KNN (default: 5)
        
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
        
        # Load dataset - use original values
        self.kett_values, self.avg_r, self.avg_g, self.avg_b = \
            load_dataset_from_csv(model_path)
        
        # Set channel weights (B-channel weighted more heavily)
        if weights is None:
            self.weights = np.array([1.0, 1.0, 3.0])  # Default: B-channel 3x
        else:
            self.weights = np.array(weights)
        
        # Store k value
        self.k_neighbors = min(k_neighbors, len(self.kett_values))
        
        # Create combined RGB array
        self.all_points = np.column_stack((self.avg_r, self.avg_g, self.avg_b))
        
        # Pre-compute weighted points for faster distance calculation
        self.weighted_points = self.all_points * self.weights
        
        logger.info(f"Initialized Kett Predictor for {self.sample_type}")
        logger.info(f"  Dataset size: {len(self.kett_values)} points")
        logger.info(f"  Channel weights: R={self.weights[0]:.1f}, G={self.weights[1]:.1f}, B={self.weights[2]:.1f}")
        logger.info(f"  K-neighbors: {self.k_neighbors}")
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
        Predict Kett value using Weighted RGB Distance
        
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
            logger.info(f"  Using Weighted RGB Distance (B-channel priority)")
            
            return self._predict_weighted_rgb(r, g, b)
        
        except Exception as e:
            logger.error(f"Error predicting Kett value: {str(e)}")
            # Fallback to simple nearest neighbor
            return self._predict_nearest_unweighted(r, g, b)
    
    def _predict_weighted_rgb(self, r, g, b):
        """
        Weighted RGB distance with K-Nearest Neighbors
        B-channel is weighted more heavily
        """
        query = np.array([r, g, b])
        
        # Apply weights to query
        weighted_query = query * self.weights
        
        # Calculate weighted Euclidean distance
        distances = np.linalg.norm(self.weighted_points - weighted_query, axis=1)
        
        # Find k nearest neighbors
        k = self.k_neighbors
        if k > len(distances):
            k = len(distances)
        
        # Get indices of k nearest neighbors
        nearest_k_indices = np.argpartition(distances, k-1)[:k]
        nearest_k_indices = nearest_k_indices[np.argsort(distances[nearest_k_indices])]
        
        nearest_distances = distances[nearest_k_indices]
        nearest_kett_values = self.kett_values[nearest_k_indices]
        
        # Calculate unweighted distances for logging
        unweighted_distances = np.linalg.norm(
            self.all_points[nearest_k_indices] - query, axis=1
        )
        
        logger.info(f"\n  K-Nearest Neighbors (k={k}):")
        for i, idx in enumerate(nearest_k_indices):
            logger.info(
                f"    #{i+1}: Kett={self.kett_values[idx]:.1f}, "
                f"RGB({self.avg_r[idx]:.1f}, {self.avg_g[idx]:.1f}, {self.avg_b[idx]:.1f}), "
                f"Weighted Dist={nearest_distances[i]:.2f}, "
                f"Unweighted Dist={unweighted_distances[i]:.2f}"
            )
        
        # Use inverse distance weighting
        epsilon = 1e-6  # Prevent division by zero
        weights = 1.0 / (nearest_distances + epsilon)
        weights = weights / np.sum(weights)  # Normalize
        
        # Weighted average of Kett values
        kett_pred = np.sum(nearest_kett_values * weights)
        
        logger.info(f"\n  Neighbor weights: {weights}")
        logger.info(f"  Individual contributions:")
        for i in range(k):
            contribution = nearest_kett_values[i] * weights[i]
            logger.info(
                f"    Kett {nearest_kett_values[i]:.1f} × {weights[i]:.4f} = {contribution:.2f}"
            )
        
        logger.info(f"\n  PREDICTION: {kett_pred:.2f}")
        logger.info("="*70 + "\n")
        
        return float(kett_pred)
    
    def _predict_nearest_unweighted(self, r, g, b):
        """
        Simple nearest neighbor fallback (unweighted)
        """
        query = np.array([[r, g, b]])
        distances = cdist(query, self.all_points, metric='euclidean')[0]
        
        closest_idx = np.argmin(distances)
        kett_pred = self.kett_values[closest_idx]
        
        logger.warning(
            f"Using fallback - Nearest neighbor: Kett={kett_pred:.1f}, "
            f"RGB({self.avg_r[closest_idx]:.1f}, {self.avg_g[closest_idx]:.1f}, "
            f"{self.avg_b[closest_idx]:.1f}), "
            f"Distance={distances[closest_idx]:.2f}"
        )
        
        return float(kett_pred)


def get_kett_predictor(sample_type='sella', model_path=None, device_id=None, 
                       models_base_dir=None, weights=None, k_neighbors=5):
    """
    Get cached Kett predictor instance
    
    Args:
        sample_type: 'sella' or 'non_sella' (case insensitive)
        model_path: Direct path to model file (overrides device_id)
        device_id: Device ID to auto-detect paths (e.g., "AGS-2001")
        models_base_dir: Base directory for models (default: from config)
        weights: RGB channel weights [w_r, w_g, w_b]. Default: [1.0, 1.0, 3.0]
        k_neighbors: Number of nearest neighbors (default: 5)
    
    Returns:
        KettPredictor: Cached predictor instance
    
    Example:
        >>> # Default: B-channel weighted 3x
        >>> predictor = get_kett_predictor('sella', device_id='AGS-2001')
        >>> 
        >>> # Custom weights: B-channel weighted 5x
        >>> predictor = get_kett_predictor('sella', device_id='AGS-2001', 
        ...                                 weights=[1.0, 1.0, 5.0])
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
    weights_str = str(weights) if weights else "default"
    cache_key = f"{sample_type}_{model_path}_{weights_str}_{k_neighbors}"
    
    # Return cached predictor or create new one
    if cache_key not in _predictor_cache:
        _predictor_cache[cache_key] = KettPredictor(
            model_path, sample_type, weights, k_neighbors
        )
    
    return _predictor_cache[cache_key]


def predict_kett(r, g, b, sample_type='sella', model_path=None, device_id=None,
                models_base_dir=None, weights=None, k_neighbors=5):
    """
    Predict Kett value for given RGB values using Weighted RGB Distance
    
    Args:
        r: Red channel value (0-255)
        g: Green channel value (0-255)
        b: Blue channel value (0-255)
        sample_type: 'sella' or 'non_sella'
        model_path: Direct path to model file
        device_id: Device ID to auto-detect paths
        models_base_dir: Base directory for models
        weights: RGB channel weights [w_r, w_g, w_b]. Default: [1.0, 1.0, 3.0]
        k_neighbors: Number of nearest neighbors (default: 5)
    
    Returns:
        float: Predicted Kett whiteness value
    
    Example:
        >>> # Default weights (B-channel 3x)
        >>> kett = predict_kett(150, 140, 135, 'sella', device_id='AGS-2001')
        >>> 
        >>> # Custom weights (B-channel 5x)
        >>> kett = predict_kett(150, 140, 135, 'sella', device_id='AGS-2001',
        ...                     weights=[1.0, 1.0, 5.0])
    """
    predictor = get_kett_predictor(
        sample_type=sample_type,
        model_path=model_path,
        device_id=device_id,
        models_base_dir=models_base_dir,
        weights=weights,
        k_neighbors=k_neighbors
    )
    return predictor.predict(r, g, b)