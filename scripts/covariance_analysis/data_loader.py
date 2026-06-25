# scripts/covariance_analysis/data_loader.py
import pandas as pd
from loguru import logger

CSV_PATH = "data/lmfdb/lmfdb_sql_weight2_ml.csv"

def load_lmfdb_correlation_data():
    """Load LMFDB correlation data from CSV.

    Returns:
        pd.DataFrame: Filtered non-CM forms with trace columns
    """
    logger.info(f"Loading correlation data from {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    df_non_cm = df[df['is_cm'] == 0].copy()
    logger.info(f"Loaded {len(df_non_cm)} non-CM forms from {len(df)} total forms")
    return df_non_cm

def separate_by_dimension_boundary(df, boundary_dim=6):
    """Split dataframe into low and high dimension classes.

    Args:
        df: DataFrame with 'dim' column
        boundary_dim: Dimension threshold (default 6 based on Sprint 3)

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (low_dim_df, high_dim_df)
    """
    logger.info(f"Separating forms by dimension boundary d={boundary_dim}")
    low_df = df[df['dim'] <= boundary_dim].copy()
    high_df = df[df['dim'] > boundary_dim].copy()

    if len(low_df) < 50:
        raise ValueError(f"Insufficient low-dimension forms: {len(low_df)} < 50")
    if len(high_df) < 50:
        raise ValueError(f"Insufficient high-dimension forms: {len(high_df)} < 50")

    logger.info(f"Low dimensions (d≤{boundary_dim}): {len(low_df)} forms")
    logger.info(f"High dimensions (d>{boundary_dim}): {len(high_df)} forms")

    return low_df, high_df