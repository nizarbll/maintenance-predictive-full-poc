import json
import time
import os
import pandas as pd
from pathlib import Path
# pyrefly: ignore [missing-import]
from confluent_kafka import Producer
from dataops.config import KAFKA_CFG, resolve_path, PATHS
from dataops.logger import ingestion_logger

BOOTSTRAP = KAFKA_CFG.get("bootstrap_servers", "localhost:9092")
TOPIC = KAFKA_CFG.get("topic", "sensor-data")
SEND_INTERVAL_SEC = KAFKA_CFG.get("send_interval_sec", 0.5)

# Resolve paths
DATASET_DIR = resolve_path("dataset")
CSV_PATH = DATASET_DIR / "merged_dataset.csv"

# Fallback path if Kafka is down
MOCK_STREAM_PATH = resolve_path("data/mock_kafka_stream.jsonl")

def init_producer():
    try:
        conf = {'bootstrap.servers': BOOTSTRAP}
        producer = Producer(conf)
        # Quick test to see if broker is reachable
        # Note: list_topics will block or raise exception if Kafka is unreachable
        producer.list_topics(timeout=1.0)
        ingestion_logger.info(f"Connected to Kafka broker at {BOOTSTRAP}")
        return producer, False
    except Exception as e:
        ingestion_logger.warning(
            f"Could not connect to Kafka broker at {BOOTSTRAP}: {e}. "
            f"Enabling local file-based streaming simulation fallback."
        )
        return None, True

def main():
    if not CSV_PATH.exists():
        ingestion_logger.error(f"Merged dataset file not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    ingestion_logger.info(f"Loaded dataset from {CSV_PATH} with {len(df):,} rows.")

    producer, is_mock = init_producer()

    # Clear mock stream file if we are in mock mode
    if is_mock:
        MOCK_STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MOCK_STREAM_PATH, "w", encoding="utf-8") as f:
            f.truncate(0)

    ingestion_logger.info(f"Starting data simulation stream. Mode: {'MOCK' if is_mock else 'KAFKA'}")
    
    count = 0
    try:
        for _, row in df.iterrows():
            message = {
                'unit_number': int(row["unit_number"]),
                'cycle': int(row["cycle"]),
                'RUL': int(row["RUL"]),
                'op_setting_1': float(row["op_setting_1"]),
                'op_setting_2': float(row["op_setting_2"]),
                'op_setting_3': float(row["op_setting_3"]),
                'sensor_1': float(row["sensor_1"]),
                'sensor_2': float(row["sensor_2"]),
                'sensor_3': float(row["sensor_3"]),
                'sensor_4': float(row["sensor_4"]),
                'sensor_5': float(row["sensor_5"]),
                'sensor_6': float(row["sensor_6"]),
                'sensor_7': float(row["sensor_7"]),
                'sensor_8': float(row["sensor_8"]),
                'sensor_9': float(row["sensor_9"]),
                'sensor_10': float(row["sensor_10"]),
                'sensor_11': float(row["sensor_11"]),
                'sensor_12': float(row["sensor_12"]),
                'sensor_13': float(row["sensor_13"]),
                'sensor_14': float(row["sensor_14"]),
                'sensor_15': float(row["sensor_15"]),
                'sensor_17': float(row["sensor_17"]),
                'sensor_18': float(row["sensor_18"]),
                'sensor_19': float(row["sensor_19"]),
                'sensor_20': float(row["sensor_20"]),
                'sensor_21': float(row["sensor_21"]),
                'engine_type': str(row["engine_type"]),
                # Fixed bug: unique_engine_id is now explicitly fetched from dataset
                'unique_engine_id': str(row["unique_engine_id"])
            }

            if is_mock:
                # Append to JSONL file to simulate Kafka stream topic
                with open(MOCK_STREAM_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(message) + "\n")
            else:
                # Send to Kafka
                producer.produce(
                    TOPIC,
                    key=str(message['unique_engine_id']),
                    value=json.dumps(message).encode('utf-8')
                )
                producer.poll(0)

            count += 1
            if count % 100 == 0:
                ingestion_logger.info(f"Stream progress: {count} messages streamed.")
            
            time.sleep(SEND_INTERVAL_SEC)
            
    except KeyboardInterrupt:
        ingestion_logger.info("Simulation stopped by user.")
    finally:
        if not is_mock and producer:
            ingestion_logger.info("Flushing remaining Kafka messages...")
            producer.flush()

if __name__ == "__main__":
    main()