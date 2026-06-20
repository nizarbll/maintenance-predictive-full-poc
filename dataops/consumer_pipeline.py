import time
import json
import os
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from confluent_kafka import Consumer, KafkaError
from dataops.config import KAFKA_CFG, PATHS, FEAST_CFG, resolve_path
from dataops.logger import processing_logger
from dataops.validation import validate_dataframe

# Centralized configurations
BOOTSTRAP = KAFKA_CFG.get("bootstrap_servers", "localhost:9092")
TOPIC = KAFKA_CFG.get("topic", "sensor-data")
GROUP_ID = KAFKA_CFG.get("group_id", "nasa-telemetry-ingest")
BATCH_SIZE = KAFKA_CFG.get("batch_size", 200)

# Paths
BRONZE_DIR = resolve_path(PATHS.get("data_lake", {}).get("bronze_dir", "data/bronze"))
SILVER_DIR = resolve_path(PATHS.get("data_lake", {}).get("silver_dir", "data/silver"))
GOLD_DIR = resolve_path(PATHS.get("data_lake", {}).get("gold_dir", "data/gold"))

for directory in [BRONZE_DIR, SILVER_DIR, GOLD_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database Setup
DB_CONN = FEAST_CFG.get("offline_store", {}).get("connection_string")
FALLBACK_DB = FEAST_CFG.get("offline_store", {}).get("fallback_db", "data/offline_store.db")

def init_db_engine():
    try:
        engine = create_engine(DB_CONN)
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        processing_logger.info("Connected to PostgreSQL Offline Store database.")
        return engine, False
    except Exception as e:
        processing_logger.warning(
            f"Failed to connect to PostgreSQL at {DB_CONN}: {e}. "
            f"Falling back to local SQLite offline store at sqlite:///{FALLBACK_DB}"
        )
        # Ensure fallback db parent directory exists
        fallback_path = resolve_path(FALLBACK_DB)
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{fallback_path}")
        return engine, True

db_engine, is_sqlite_fallback = init_db_engine()

# Feature engineering columns
SENSOR_COLS = [f"sensor_{i}" for i in range(1, 22) if i != 16]
OP_COLS = ["op_setting_1", "op_setting_2", "op_setting_3"]
USEFUL_COLS = SENSOR_COLS + OP_COLS
CLIP_LIMIT = 125
WINDOW_SIZE = 5

def add_rul(df):
    # RUL calculation
    grouped = df.groupby("unit_number")
    max_cycles = grouped["cycle"].max()
    df = df.merge(max_cycles.to_frame("max_cycle"), left_on="unit_number", right_index=True)
    df["RUL"] = df["max_cycle"] - df["cycle"]
    df.drop(columns=["max_cycle"], inplace=True)
    df["RUL_TARGET"] = df["RUL"].clip(upper=CLIP_LIMIT)
    return df

def feature_engineering(df):
    df = df.copy()
    df["time_in_months"] = df["cycle"] / 30.0
    dfs = []
    for engine_id, group in df.groupby("unit_number"):
        group = group.sort_values("cycle")
        roll_mean = group[USEFUL_COLS].rolling(window=WINDOW_SIZE, min_periods=1).mean().add_suffix("_roll_mean")
        roll_std = group[USEFUL_COLS].rolling(window=WINDOW_SIZE, min_periods=1).std().fillna(0).add_suffix("_roll_std")
        diff = group[USEFUL_COLS].diff().fillna(0).add_suffix("_diff")
        combined = pd.concat([group, roll_mean, roll_std, diff], axis=1)
        dfs.append(combined)
    return pd.concat(dfs, ignore_index=True)

def normalize(df):
    df = df.copy()
    stds = df[USEFUL_COLS].std()
    drop_cols = stds[stds < 0.01].index.tolist()
    df = df.drop(columns=drop_cols)
    useful = [c for c in USEFUL_COLS if c not in drop_cols]
    
    def minmax(x):
        r = x.max() - x.min()
        return x - x.min() if r == 0 else (x - x.min()) / r

    for col in useful:
        df[col] = df.groupby("unit_number")[col].transform(minmax)
    return df

def get_partition_path(base_dir: str) -> str:
    now = datetime.now(timezone.utc)
    path = os.path.join(
        base_dir,
        f"year={now.strftime('%Y')}",
        f"month={now.strftime('%m')}",
        f"day={now.strftime('%d')}"
    )
    os.makedirs(path, exist_ok=True)
    return path

def process_batch(batch_data: list):
    start_time = time.time()
    processing_logger.info(f"Processing batch of {len(batch_data)} records...")
    
    # Create DataFrame
    df = pd.DataFrame(batch_data)
    
    # 1. Save to Bronze Data Lake (Raw)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bronze_path = os.path.join(get_partition_path(BRONZE_DIR), f"batch_{timestamp_str}.csv")
    df.to_csv(bronze_path, index=False)
    processing_logger.info(f"Saved {len(df)} raw records to Bronze Lake: {bronze_path}")

    # 2. Data Cleaning and Validation
    df_cleaned = validate_dataframe(df)

    # 3. Save to Silver Data Lake (Cleaned)
    silver_path = os.path.join(get_partition_path(SILVER_DIR), f"batch_{timestamp_str}.csv")
    df_cleaned.to_csv(silver_path, index=False)
    processing_logger.info(f"Saved cleaned records to Silver Lake: {silver_path}")

    # 4. Feature Engineering
    df_features = add_rul(df_cleaned)
    df_features = feature_engineering(df_features)
    df_features = normalize(df_features)
    
    # Add timestamps required for Feast — store as ISO string WITH UTC offset
    df_features["event_timestamp"] = datetime.now(timezone.utc).isoformat()
    
    # Clean column types specifically for database compatibility
    # Float columns should be float32/float64, int should be int64
    for col in df_features.columns:
        if col not in ["engine_type", "unique_engine_id", "event_timestamp"]:
            df_features[col] = pd.to_numeric(df_features[col], errors='coerce').astype(float)
    
    # 5. Save Features to SQLite / Postgres (Feast Offline Database)
    df_features.to_sql(
        "engine_features",
        con=db_engine,
        if_exists="append",
        index=False
    )
    
    duration = time.time() - start_time
    num_features = len(df_features.columns) - len(df_cleaned.columns)
    
    # Monitoring Logs
    processing_logger.info(
        f"[MONITORING] Batch processed in {duration:.3f}s | "
        f"Bronze size: {os.path.getsize(bronze_path)} bytes | "
        f"Silver size: {os.path.getsize(silver_path)} bytes | "
        f"Features generated: {num_features} columns | "
        f"Ingested to Store: {len(df_features)} rows"
    )

def consume_mock_stream():
    """Reads from mock file and streams events sequentially if Kafka is not available."""
    mock_file_path = resolve_path("data/mock_kafka_stream.jsonl")
    processing_logger.info(f"Listening to mock stream file at {mock_file_path}...")
    
    last_position = 0
    batch = []
    
    while True:
        if not mock_file_path.exists():
            time.sleep(1)
            continue
            
        with open(mock_file_path, "r", encoding="utf-8") as f:
            f.seek(last_position)
            lines = f.readlines()
            last_position = f.tell()
            
        for line in lines:
            if line.strip():
                batch.append(json.loads(line))
                if len(batch) >= BATCH_SIZE:
                    process_batch(batch)
                    batch = []
                    
        # If the file was cleared/truncated, reset last position
        if os.path.exists(mock_file_path) and os.path.getsize(mock_file_path) < last_position:
            last_position = 0
            
        time.sleep(1)

def consume_kafka():
    """Reads events from real Kafka broker."""
    conf = {
        'bootstrap.servers': BOOTSTRAP,
        'group.id': GROUP_ID,
        'auto.offset.reset': 'latest',
        'enable.auto.commit': True
    }
    
    consumer = Consumer(conf)
    consumer.subscribe([TOPIC])
    processing_logger.info(f"Listening to Kafka topic '{TOPIC}' from {BOOTSTRAP}...")
    
    batch = []
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    processing_logger.error(f"Kafka error: {msg.error()}")
                    break
                    
            event_val = json.loads(msg.value().decode('utf-8'))
            batch.append(event_val)
            
            if len(batch) >= BATCH_SIZE:
                process_batch(batch)
                batch = []
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

def main():
    # Detect if we should use Kafka or Fallback mock file
    # We test if Kafka is reachable
    try:
        temp_consumer = Consumer({'bootstrap.servers': BOOTSTRAP, 'group.id': 'temp-check'})
        temp_consumer.list_topics(timeout=1.0)
        use_kafka = True
    except Exception:
        use_kafka = False
        
    if use_kafka:
        consume_kafka()
    else:
        consume_mock_stream()

if __name__ == "__main__":
    main()
