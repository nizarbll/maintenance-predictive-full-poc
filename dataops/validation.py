import pandas as pd
import numpy as np
from dataops.logger import processing_logger

# Columns that should be numeric
SENSOR_COLS = [f"sensor_{i}" for i in range(1, 22) if i != 16]
OP_COLS = ["op_setting_1", "op_setting_2", "op_setting_3"]
REQUIRED_COLS = ["unit_number", "cycle"] + OP_COLS + SENSOR_COLS

def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates the schema, types, missing values, duplicates, and outliers of the dataframe.
    Logs warning/errors and returns a clean dataframe.
    """
    df = df.copy()
    processing_logger.info(f"Starting data validation on batch of shape {df.shape}...")

    # 1. Schema Check (Required Columns)
    missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing_cols:
        processing_logger.error(f"Schema Validation Failed: Missing columns {missing_cols}")
        # Insert missing columns with default/NaN values to avoid crashes downstream
        for col in missing_cols:
            df[col] = np.nan
    else:
        processing_logger.info("Schema Validation: All required columns present.")

    # 2. Type Check & Cast
    for col in REQUIRED_COLS:
        if col in df.columns:
            original_type = df[col].dtype
            if not np.issubdtype(original_type, np.number):
                processing_logger.warning(f"Type Mismatch: Column {col} is type {original_type}, coercing to numeric.")
                df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. Handle Missing Values
    null_counts = df[REQUIRED_COLS].isnull().sum()
    total_nulls = null_counts.sum()
    if total_nulls > 0:
        processing_logger.warning(f"Missing Values: Found {total_nulls} null values across required columns.")
        # Forward fill and then backward fill missing values grouped by unit_number
        if "unit_number" in df.columns:
            df = df.groupby("unit_number", group_keys=False).apply(lambda g: g.ffill().bfill())
        else:
            df = df.ffill().bfill()
        
        # Fill remaining NaNs with column median/mean
        for col in REQUIRED_COLS:
            if df[col].isnull().any():
                fill_val = df[col].mean() if not np.isnan(df[col].mean()) else 0.0
                df[col] = df[col].fillna(fill_val)
        processing_logger.info("Missing Values: Nulls imputed successfully.")

    # 4. Remove Duplicates
    if "unit_number" in df.columns and "cycle" in df.columns:
        dups = df.duplicated(subset=["unit_number", "cycle"]).sum()
        if dups > 0:
            processing_logger.warning(f"Duplicates: Found {dups} duplicate unit-cycle entries. Removing duplicates...")
            df = df.drop_duplicates(subset=["unit_number", "cycle"])
            processing_logger.info("Duplicates: Removed duplicates.")

    # 5. Outliers Detection & Handling
    # Clean up sensor measurements by clipping extreme values (e.g. beyond 6 standard deviations)
    for col in SENSOR_COLS + OP_COLS:
        col_mean = df[col].mean()
        col_std = df[col].std()
        if col_std > 0:
            lower_bound = col_mean - 6 * col_std
            upper_bound = col_mean + 6 * col_std
            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            if outliers > 0:
                processing_logger.warning(f"Outliers: Column {col} has {outliers} values beyond 6-sigma. Clipping to bounds [{lower_bound:.2f}, {upper_bound:.2f}].")
                df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

    processing_logger.info(f"Validation complete. Output shape: {df.shape}")
    return df
