# Kafka telemetry simulator

Streams rows from `dataset/merged_dataset.csv` to Kafka like a live aircraft engine fleet: one message per operational cycle, keyed by `unique_engine_id`, with ingestion timestamps and optional sensor noise.

## 1. Start Kafka

From the project root:

```bash
docker compose up -d
```

- Broker (from your machine): `localhost:29092`
- Kafka UI: http://localhost:8080

## 2. Install Python deps

```bash
pip install -r requirements-kafka.txt
```

## 3. Produce events

Default: 10 messages/sec, fleet mode (engines interleaved):

```bash
python kafka/stream_producer.py
```

Examples:

```bash
# Slower stream, 5 engines only
python kafka/stream_producer.py --rate 2 --max-engines 5

# One engine, every cycle in order
python kafka/stream_producer.py --mode sequential --engine-id FD001_1

# Continuous replay for load testing
python kafka/stream_producer.py --loop --rate 50

# Full CSV columns in each message
python kafka/stream_producer.py --full-payload
```

## 4. Consume (verify)

```bash
python kafka/stream_consumer.py --from-beginning
```

## Message shape

Topic: `engine-telemetry` (auto-created, 6 partitions)

```json
{
  "event_id": "uuid",
  "event_type": "SENSOR_READING",
  "schema_version": "1.0",
  "source": "nasa-turbofan-simulator",
  "ingested_at": "2026-05-21T12:00:00+00:00",
  "simulated_cycle_time": 0.333,
  "telemetry": {
    "unique_engine_id": "FD001_1",
    "cycle": 42,
    "sensor_1": 0.12,
    "RUL": 150,
    ...
  }
}
```

`event_type` becomes `RUL_LOW_ALERT` when `RUL <= 30`.
