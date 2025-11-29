import logging
import numpy as np
from utils.kett_predictor import get_kett_predictor

logger = logging.getLogger(__name__)


def determine_sample_type(avg_r, avg_b):
    """
    Determine sample type based on average RGB values of all grains
    Priority: Brown > Mixed > Yellow > White > Default
    
    Args:
        avg_r: Average R value across all grains
        avg_b: Average B value across all grains
    
    Returns:
        str: Sample type ('White', 'Yellow', 'Brown', or 'Mixed')
    """
    avg_rb_gap = avg_r - avg_b

    # Check Brown first (most specific: high R, low B)
    if avg_r > 162 and avg_b < 145:
        return "Brown"
    
    # Check Mixed (high R and B with significant gap)
    elif avg_r > 145 and avg_b > 130 and avg_rb_gap > 13:
        return "Mixed"

    # Check Yellow (low R, low B)
    elif avg_r < 143 and avg_b < 125:
        return "Yellow"
    
    # Check White (high R, high B with small gap)
    elif (avg_r > 140 and avg_b > 126) or (avg_rb_gap < 12):
        return "White"
    else:
        # Default to White if none match (safest threshold)
        return "White"


def calculate_br_statistics(grains_with_rgb):
    """
    Calculate average and standard deviation of (B-R) values from all grains
    
    Args:
        grains_with_rgb: List of dictionaries containing 'B' and 'R' values
    
    Returns:
        Tuple of (avg_br, std_br)
    """
    br_values = [g['B'] - g['R'] for g in grains_with_rgb 
                 if 'B' in g and 'R' in g and g['B'] > 0 and g['R'] > 0]
    
    if not br_values:
        logger.warning("No valid B-R values found for calculating statistics")
        return 0, 0
    
    avg_br = np.mean(br_values)
    std_br = np.std(br_values)
    
    logger.info(f"(B-R) value statistics: Avg={avg_br:.2f}, Std={std_br:.2f}, Threshold={avg_br - 12:.2f}")
    
    return avg_br, std_br


def classify_discoloration(b_value, r_value, avg_br):
    """
    Classify grain discoloration based on (B-R) value compared to average(B-R) - 12
    
    Args:
        b_value: Blue channel value of the grain
        r_value: Red channel value of the grain
        avg_br: Average (B-R) value across all grains
    
    Returns:
        str: "YES" if discolored, "NO" otherwise
    """
    br_value = b_value - r_value
    threshold = avg_br - 11
    
    if br_value < threshold:
        return "YES"
    else:
        return "NO"


def calculate_statistics(grains, rice_variety='non_sella', full_rgb_avg=None, 
                        local_sella_path=None, local_non_sella_path=None, device_id=None):
    """
    Calculate statistics from grain data including Kett prediction
    
    Args:
        grains: List of grain dictionaries
        rice_variety: Rice variety type - 'sella' or 'non_sella' for Kett prediction
        full_rgb_avg: Dictionary with 'R', 'G', 'B' keys containing full dataset averages.
                      If provided, use these values for Kett prediction instead of filtering.
        local_sella_path: Local path to Sella dataset CSV file (optional)
        local_non_sella_path: Local path to Non-Sella dataset CSV file (optional)
        device_id: Device ID to auto-detect model paths (e.g., "AGS-2001")
    
    Returns:
        dict: Statistics including averages, counts, and Kett value
    """
    if not grains:
        return {
            'total_grains': 0,
            'avg_length': 0,
            'avg_breadth': 0,
            'avg_br': 0,
            'std_br': 0,
            'discolored_count': 0,
            'chalky_count': 0,
            'broken_count': 0,
            'kett_value': None,
            'rice_variety': rice_variety
        }
    
    total_grains = len(grains)
    
    # Calculate averages
    total_length = sum(g.get('length', 0) for g in grains)
    total_breadth = sum(g.get('width', 0) for g in grains)
    avg_length = round(total_length / total_grains, 2) if total_grains > 0 else 0
    avg_breadth = round(total_breadth / total_grains, 2) if total_grains > 0 else 0
    
    # Calculate (B-R) value statistics
    br_values = [g.get('B', 0) - g.get('R', 0) for g in grains 
                 if 'B' in g and 'R' in g]
    avg_br = np.mean(br_values) if br_values else 0
    std_br = np.std(br_values) if br_values else 0
    
    logger.info(f"(B-R) value statistics: Avg={avg_br:.2f}, Std={std_br:.2f}, Threshold={avg_br - 12:.2f}")
    
    # Count defects
    discolored_count = sum(1 for g in grains if g.get('discolor') == 'YES')
    chalky_count = sum(1 for g in grains if g.get('chalky') == 'Yes')
    broken_count = sum(1 for g in grains if g.get('broken', False))
    
    # ========================================================================
    # Calculate Kett value from FULL DATASET (all grains)
    # ========================================================================
    kett_value = None
    
    # Build predictor kwargs
    predictor_kwargs = {}
    if local_sella_path:
        predictor_kwargs['local_sella_path'] = local_sella_path
    if local_non_sella_path:
        predictor_kwargs['local_non_sella_path'] = local_non_sella_path
    if device_id:
        predictor_kwargs['device_id'] = device_id
        logger.info(f"Using device_id for Kett prediction: {device_id}")
    
    # Use full dataset RGB averages if provided
    if full_rgb_avg and 'R' in full_rgb_avg and 'G' in full_rgb_avg and 'B' in full_rgb_avg:
        avg_r = full_rgb_avg['R']
        avg_g = full_rgb_avg['G']
        avg_b_for_kett = full_rgb_avg['B']
        
        logger.info("=" * 60)
        logger.info("KETT PREDICTION USING FULL DATASET:")
        logger.info(f"  Using ALL GRAINS RGB averages: R={avg_r:.2f}, G={avg_g:.2f}, B={avg_b_for_kett:.2f}")
        logger.info("=" * 60)
        
        # Predict Kett value using the specified rice variety
        try:
            predictor = get_kett_predictor(rice_variety, **predictor_kwargs)
            kett_value = predictor.predict_kett(avg_r, avg_g, avg_b_for_kett)
            if kett_value is not None:
                kett_value = round(kett_value, 2)
                logger.info(f"Kett value predicted: {kett_value} from FULL DATASET RGB({avg_r:.2f}, {avg_g:.2f}, {avg_b_for_kett:.2f}) "
                          f"using {rice_variety} dataset")
        except Exception as e:
            logger.error(f"Failed to predict Kett value: {str(e)}")
            kett_value = None
    
    # Fallback: Use non-discolored grains (old method)
    elif not full_rgb_avg:
        logger.warning("No full_rgb_avg provided, falling back to non-discolored grains method")
        non_discolored_grains = [g for g in grains if g.get('discolor') == 'NO']
        
        if non_discolored_grains:
            # Get RGB values from grains (if available)
            rgb_grains = [g for g in non_discolored_grains 
                         if 'R' in g and 'G' in g and 'B' in g]
            
            if rgb_grains:
                # Calculate average RGB from non-discolored grains
                avg_r = sum(g['R'] for g in rgb_grains) / len(rgb_grains)
                avg_g = sum(g['G'] for g in rgb_grains) / len(rgb_grains)
                avg_b_non_disc = sum(g['B'] for g in rgb_grains) / len(rgb_grains)
                
                logger.info(f"Fallback: Using non-discolored grains RGB({avg_r:.2f}, {avg_g:.2f}, {avg_b_non_disc:.2f})")
                
                # Predict Kett value using the specified rice variety
                try:
                    predictor = get_kett_predictor(rice_variety, **predictor_kwargs)
                    kett_value = predictor.predict_kett(avg_r, avg_g, avg_b_non_disc)
                    if kett_value is not None:
                        kett_value = round(kett_value, 2)
                        logger.info(f"Kett value predicted: {kett_value} from RGB({avg_r:.2f}, {avg_g:.2f}, {avg_b_non_disc:.2f}) "
                                  f"using {rice_variety} dataset")
                except Exception as e:
                    logger.error(f"Failed to predict Kett value: {str(e)}")
                    kett_value = None
    # ========================================================================
    
    return {
        'total_grains': total_grains,
        'avg_length': avg_length,
        'avg_breadth': avg_breadth,
        'avg_br': round(avg_br, 2),
        'std_br': round(std_br, 2),
        'discolored_count': discolored_count,
        'chalky_count': chalky_count,
        'broken_count': broken_count,
        'kett_value': kett_value,
        'rice_variety': rice_variety
    }