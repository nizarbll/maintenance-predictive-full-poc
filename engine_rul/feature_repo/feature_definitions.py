from datetime import timedelta
import os
from sqlalchemy import create_engine, text
from feast import (
    Entity,
    FeatureView,
    Field,
    FileSource,
)
from feast.types import Float32, Int64

# Define the entity (Primary Key)
engine = Entity(
    name="unit_number",
    join_keys=["unit_number"],
    description="Industrial engine unit number"
)

# Detect if PostgreSQL is running to choose the offline source
def get_feast_source():
    pg_conn = "postgresql://postgres:postgres@localhost:5432/feature_store"
    try:
        engine_db = create_engine(pg_conn)
        with engine_db.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # If connection succeeds, use PostgreSQLSource
        from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource
        return PostgreSQLSource(
            name="engine_features_source",
            query="SELECT * FROM engine_features",
            timestamp_field="event_timestamp",
        )
    except Exception:
        # Fallback to FileSource (Parquet file exported from SQLite fallback)
        # The file is saved at "data/feature_store/engine_features.parquet" relative to project root
        # Since Feast runs from the repo directory, we use "../../data/feature_store/engine_features.parquet"
        parquet_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../data/feature_store/engine_features.parquet")
        )
        # Ensure parent folder exists
        os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
        return FileSource(
            name="engine_features_source",
            path=parquet_path,
            timestamp_field="event_timestamp",
        )

engine_source = get_feast_source()

# Define schema fields
schema_fields = [
    Field(name="cycle", dtype=Int64),
    Field(name="time_in_months", dtype=Float32),
    Field(name="RUL", dtype=Float32),
    Field(name="RUL_TARGET", dtype=Float32),
]

# Add operational settings
for i in range(1, 4):
    schema_fields.append(Field(name=f"op_setting_{i}", dtype=Float32))
    schema_fields.append(Field(name=f"op_setting_{i}_roll_mean", dtype=Float32))
    schema_fields.append(Field(name=f"op_setting_{i}_roll_std", dtype=Float32))
    schema_fields.append(Field(name=f"op_setting_{i}_diff", dtype=Float32))

# Add sensors
for i in range(1, 22):
    if i != 16:
        schema_fields.append(Field(name=f"sensor_{i}", dtype=Float32))
        schema_fields.append(Field(name=f"sensor_{i}_roll_mean", dtype=Float32))
        schema_fields.append(Field(name=f"sensor_{i}_roll_std", dtype=Float32))
        schema_fields.append(Field(name=f"sensor_{i}_diff", dtype=Float32))

# Create the Feature View
engine_features_fv = FeatureView(
    name="engine_features",
    entities=[engine],
    ttl=timedelta(days=365),
    schema=schema_fields,
    source=engine_source,
    online=True
)
