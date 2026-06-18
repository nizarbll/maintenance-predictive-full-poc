import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from feast import FeatureStore
from dataops.config import FEAST_CFG, PATHS, resolve_path
from dataops.logger import feature_store_logger

# Database config
DB_CONN = FEAST_CFG.get("offline_store", {}).get("connection_string")
FALLBACK_DB = FEAST_CFG.get("offline_store", {}).get("fallback_db", "data/offline_store.db")
GOLD_DIR = resolve_path(PATHS.get("data_lake", {}).get("gold_dir", "data/gold"))
FEAST_REPO_DIR = resolve_path(FEAST_CFG.get("repo_path", "engine_rul/feature_repo"))

# Sync SQLite to Parquet for Feast FileOfflineStore if Postgres is offline
def sync_sqlite_to_parquet():
    fallback_path = resolve_path(FALLBACK_DB)
    if not fallback_path.exists():
        feature_store_logger.warning(f"Fallback SQLite database not found at {fallback_path}. Skip syncing.")
        return False
        
    try:
        engine = create_engine(f"sqlite:///{fallback_path}")
        # Check if table exists
        with engine.connect() as conn:
            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='engine_features'")).fetchall()
            if not tables:
                feature_store_logger.warning("Table 'engine_features' not found in SQLite. Skip syncing.")
                return False
                
        df = pd.read_sql("SELECT * FROM engine_features", engine)
        
        # CRITICAL: Convert event_timestamp to UTC timezone-aware datetime
        # Feast materialize requires timezone-aware timestamps, SQLite stores as strings
        if "event_timestamp" in df.columns:
            df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], utc=True)
        
        parquet_dir = resolve_path("data/feature_store")
        parquet_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = parquet_dir / "engine_features.parquet"
        
        df.to_parquet(parquet_path, index=False)
        feature_store_logger.info(f"Synced {len(df)} rows from SQLite to Parquet at {parquet_path}")
        return True
    except Exception as e:
        feature_store_logger.error(f"Failed to sync SQLite to Parquet: {e}")
        return False

def init_db_engine():
    try:
        engine = create_engine(DB_CONN)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine, False
    except Exception:
        fallback_path = resolve_path(FALLBACK_DB)
        engine = create_engine(f"sqlite:///{fallback_path}")
        return engine, True

def build_gold_dataset():
    feature_store_logger.info("Initializing Feast Feature Store...")
    
    # Check Postgres connection
    db_engine, is_sqlite = init_db_engine()
    
    if is_sqlite:
        feature_store_logger.info("Using SQLite fallback offline store. Syncing database table to Parquet for Feast...")
        sync_success = sync_sqlite_to_parquet()
        if not sync_success:
            feature_store_logger.error("Could not sync offline store. Cannot retrieve historical features.")
            return None

    # Initialize Feast Store
    # Feast needs to run from the directory of feature_store.yaml
    store = FeatureStore(repo_path=str(FEAST_REPO_DIR))

    # 1. Fetch unique entity keys and timestamps
    feature_store_logger.info("Retrieving entity dataframe from offline database...")
    try:
        entity_df = pd.read_sql(
            "SELECT DISTINCT unit_number, event_timestamp FROM engine_features",
            con=db_engine
        )
        # Convert timestamp to datetime and match Feast timezone expectations
        entity_df["event_timestamp"] = pd.to_datetime(entity_df["event_timestamp"], utc=True)
    except Exception as e:
        feature_store_logger.error(f"Failed to load entity dataframe: {e}")
        return None

    if entity_df.empty:
        feature_store_logger.warning("No records found in database. Ingest telemetry data first.")
        return None

    feature_store_logger.info(f"Found {len(entity_df)} entity-timestamp pairs. Fetching Feast historical features...")

    # 2. Define features to retrieve
    features_to_fetch = [
        "engine_features:cycle",
        "engine_features:time_in_months",
        "engine_features:RUL_TARGET",
    ]
    
    # Add settings and sensors with roll and diff
    for prefix in ["op_setting_1", "op_setting_2", "op_setting_3"]:
        features_to_fetch.extend([
            f"engine_features:{prefix}",
            f"engine_features:{prefix}_roll_mean",
            f"engine_features:{prefix}_roll_std",
            f"engine_features:{prefix}_diff"
        ])
        
    for i in range(1, 22):
        if i != 16:
            prefix = f"sensor_{i}"
            features_to_fetch.extend([
                f"engine_features:{prefix}",
                f"engine_features:{prefix}_roll_mean",
                f"engine_features:{prefix}_roll_std",
                f"engine_features:{prefix}_diff"
            ])

    # 3. Retrieve historical features from Feast offline store
    try:
        training_df = store.get_historical_features(
            entity_df=entity_df,
            features=features_to_fetch
        ).to_df()
        
        # Save Gold Dataset
        GOLD_DIR.mkdir(parents=True, exist_ok=True)
        gold_path = GOLD_DIR / "gold_dataset.csv"
        training_df.to_csv(gold_path, index=False)
        feature_store_logger.info(
            f"[MONITORING] Gold dataset generated successfully with {len(training_df)} rows and {len(training_df.columns)} columns."
        )
        feature_store_logger.info(f"Gold dataset saved at {gold_path} (size: {os.path.getsize(gold_path)} bytes)")
        return training_df
    except Exception as e:
        feature_store_logger.error(f"Feast historical feature retrieval failed: {e}")
        return None

def get_online_features_for_engine(unit_number: int):
    """Retrieves the latest features from Feast online store (SQLite) for a given engine."""
    store = FeatureStore(repo_path=str(FEAST_REPO_DIR))
    
    features_to_fetch = [
        "engine_features:cycle",
        "engine_features:time_in_months",
        "engine_features:RUL_TARGET",
    ]
    
    for prefix in ["op_setting_1", "op_setting_2", "op_setting_3"]:
        features_to_fetch.extend([
            f"engine_features:{prefix}",
            f"engine_features:{prefix}_roll_mean",
            f"engine_features:{prefix}_roll_std",
            f"engine_features:{prefix}_diff"
        ])
        
    for i in range(1, 22):
        if i != 16:
            prefix = f"sensor_{i}"
            features_to_fetch.extend([
                f"engine_features:{prefix}",
                f"engine_features:{prefix}_roll_mean",
                f"engine_features:{prefix}_roll_std",
                f"engine_features:{prefix}_diff"
            ])

    entity_rows = [{"unit_number": int(unit_number)}]
    
    try:
        response = store.get_online_features(
            features=features_to_fetch,
            entity_rows=entity_rows
        ).to_dict()
        return response
    except Exception as e:
        feature_store_logger.error(f"Failed to fetch online features for engine {unit_number}: {e}")
        return None

if __name__ == "__main__":
    build_gold_dataset()
