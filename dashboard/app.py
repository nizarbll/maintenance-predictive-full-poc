import sys
import os
from pathlib import Path

# Fix python path for local imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import time
import json
import pandas as pd
import numpy as np
import subprocess
from confluent_kafka import Consumer
from tensorflow.keras.models import load_model
from dataops.config import KAFKA_CFG, PATHS, MLOPS_CFG, resolve_path
from feature_store.retrieve_features import get_online_features_for_engine
from dataops.logger import dashboard_logger

# Page configuration
st.set_page_config(
    page_title="NASA Engine RUL Dashboard",
    page_icon="✈️",
    layout="wide",
)

# Style Customization
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #334155;
        text-align: center;
        color: white;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #38bdf8;
    }
    .metric-title {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
</style>
""", unsafe_allow_html=True)

# Configurations & Paths
BOOTSTRAP = KAFKA_CFG.get("bootstrap_servers", "localhost:9092")
TOPIC = KAFKA_CFG.get("topic", "sensor-data")
MOCK_STREAM_PATH = resolve_path("data/mock_kafka_stream.jsonl")
PRIMARY_MODEL_PATH = resolve_path(PATHS.get("models", {}).get("primary_path", "pompe_model_lstm.keras"))
SEQ_LENGTH = MLOPS_CFG.get("sequence_length", 30)

# Load baseline model
@st.cache_resource
def load_keras_model():
    if PRIMARY_MODEL_PATH.exists():
        try:
            return load_model(str(PRIMARY_MODEL_PATH))
        except Exception as e:
            dashboard_logger.error(f"Failed to load model: {e}")
            return None
    return None

model = load_keras_model()

# Check infrastructure statuses
def check_infra_status():
    status = {"Kafka": False, "PostgreSQL": False, "Feast Registry": False}
    # Check Kafka
    try:
        c = Consumer({'bootstrap.servers': BOOTSTRAP, 'group.id': 'check-infra'})
        c.list_topics(timeout=0.5)
        status["Kafka"] = True
    except Exception:
        pass
    
    # Check PostgreSQL
    try:
        from sqlalchemy import create_engine, text
        db_conn = resolve_path("config/feast.yaml")
        # Just quick attempt
        from dataops.config import FEAST_CFG
        pg_conn = FEAST_CFG.get("offline_store", {}).get("connection_string")
        engine = create_engine(pg_conn)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["PostgreSQL"] = True
    except Exception:
        pass

    # Check Feast Registry
    from dataops.config import FEAST_CFG
    reg_path = resolve_path("engine_rul/feature_repo/data/registry.db")
    if reg_path.exists():
        status["Feast Registry"] = True
        
    return status

# Read telemetry data
def fetch_last_telemetry(limit=50):
    # Try reading from mock stream file first as fallback, or Kafka
    # Since streaming in Streamlit can block, reading from the mock stream file is perfect
    if MOCK_STREAM_PATH.exists() and MOCK_STREAM_PATH.stat().st_size > 0:
        try:
            data = []
            with open(MOCK_STREAM_PATH, "r", encoding="utf-8") as f:
                # Seek near the end
                f.seek(0, os.SEEK_END)
                end_pos = f.tell()
                # Read last lines
                seek_pos = max(0, end_pos - 32000) # read last ~32KB
                f.seek(seek_pos)
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        data.append(json.loads(line))
            if data:
                return pd.DataFrame(data)
        except Exception as e:
            dashboard_logger.error(f"Error reading mock stream: {e}")

    # Fallback to reading raw data from Bronze Data Lake if Kafka is active
    try:
        bronze_dir = resolve_path(PATHS.get("data_lake", {}).get("bronze_dir", "data/bronze"))
        if bronze_dir.exists():
            files = list(bronze_dir.glob("**/*.csv"))
            if files:
                latest_file = max(files, key=os.path.getctime)
                df = pd.read_csv(latest_file)
                if not df.empty:
                    return df.tail(limit)
    except Exception as e:
        dashboard_logger.error(f"Error reading from Bronze Lake: {e}")
            
    # Return empty template if no data
    return pd.DataFrame()

# Streamlit App Layout
st.title("✈️ NASA Remaining Useful Life (RUL) MLOps Platform")
st.markdown("---")

infra_status = check_infra_status()

# Sidebar Control
with st.sidebar:
    st.header("⚙️ System Controls")
    
    st.subheader("Infrastructure Health")
    for name, val in infra_status.items():
        color = "🟢" if val else "🔴"
        st.write(f"{color} **{name}**: {'Online' if val else 'Offline'}")
        
    st.subheader("Selection")
    engine_id = st.number_input("Select Engine Unit Number", min_value=1, max_value=100, value=1)
    
    st.markdown("---")
    st.subheader("MLOps Operations")
    
    if st.button("🔄 Sync Feast Offline Store"):
        with st.spinner("Syncing SQLite offline database to Parquet..."):
            from feature_store.retrieve_features import sync_sqlite_to_parquet
            res = sync_sqlite_to_parquet()
            if res:
                st.success("Successfully synced Feast offline data.")
            else:
                st.error("Failed to sync Feast offline store.")
                
    if st.button("⚡ Apply & Materialize Feast"):
        with st.spinner("Running feast apply & materialize-incremental..."):
            try:
                # Run feast apply
                repo_path = resolve_path("engine_rul/feature_repo")
                subprocess.run(["feast", "apply"], cwd=str(repo_path), check=True)
                # Run materialize
                from datetime import datetime
                subprocess.run(
                    ["feast", "materialize-incremental", datetime.now().isoformat()],
                    cwd=str(repo_path),
                    check=True
                )
                st.success("Feast materialization complete.")
            except Exception as e:
                st.error(f"Feast error: {e}")

    if st.button("🤖 Retrain RUL Model"):
        with st.spinner("Running ML retraining pipeline..."):
            try:
                # Retrain model by running haja.py
                mlops_path = resolve_path("mlops/haja.py")
                res = subprocess.run(["python", str(mlops_path)], capture_output=True, text=True)
                st.code(res.stdout)
                st.success("Model retraining execution completed.")
            except Exception as e:
                st.error(f"Retraining error: {e}")

tabs = st.tabs(["📊 Flux 1: Real-time Sensors", "🔮 Flux 2: MLOps & RUL Prediction"])

# TAB 1: Real-Time Telemetry
with tabs[0]:
    st.subheader("Flux 1: Telemetry Stream (Raw Data via Kafka / Mock)")
    
    placeholder = st.empty()
    
    # Simple loop to simulate real-time plotting
    df_stream = fetch_last_telemetry(60)
    
    if df_stream.empty:
        st.warning("No telemetry stream data found. Start the Kafka Producer (producer.py) first.")
    else:
        with placeholder.container():
            col1, col2, col3 = st.columns(3)
            
            # Extract latest values
            latest_row = df_stream.iloc[-1]
            
            # Map metrics
            temp = latest_row.get("sensor_2", 0.0)
            pressure = latest_row.get("sensor_11", 0.0)
            vibration = latest_row.get("sensor_8", 0.0)
            cycle = latest_row.get("cycle", 0)
            
            with col1:
                st.markdown(f'<div class="metric-card"><div class="metric-title">🌡️ Inlet Temp (Sensor 2)</div><div class="metric-value">{temp:.2f} °K</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-card"><div class="metric-title">💨 HP Outlet Pressure (Sensor 11)</div><div class="metric-value">{pressure:.2f} psia</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-card"><div class="metric-title">🔄 Physical Fan Speed (Sensor 8)</div><div class="metric-value">{vibration:.2f} rpm</div></div>', unsafe_allow_html=True)
            
            # Charts
            st.markdown("### Historical Trends (Last 50 messages)")
            
            # Plot sensors
            chart_df = df_stream[["cycle", "sensor_2", "sensor_8", "sensor_11"]].set_index("cycle")
            st.line_chart(chart_df)
            
            # Alert Check
            st.markdown("### ⚠️ Active Alerts")
            # Basic thresholding logic for illustration
            alerts = []
            if temp > 643.0:
                alerts.append(f"🚨 **High Temperature Warning**: Engine Inlet temperature exceeded safety threshold ({temp:.2f} > 643.0)")
            if pressure < 510.0:
                alerts.append(f"⚠️ **Low Compressor Pressure Warning**: Low pressure detected ({pressure:.2f} < 510.0)")
                
            if alerts:
                for alert in alerts:
                    st.error(alert)
            else:
                st.success("✅ Engine operating within safe margins.")

# TAB 2: Predictions and MLOps
with tabs[1]:
    st.subheader("Flux 2: Feast Integration & RUL Predictions")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### RUL Prediction")
        
        # 1. Fetch features from Feast online store
        online_data = get_online_features_for_engine(engine_id)
        
        if online_data is None or not online_data.get("cycle") or online_data["cycle"][0] is None:
            st.warning(f"No online features found for Engine #{engine_id} in Feast online store. Materialize Feast first.")
        else:
            # Reconstruct feature vector
            # We require sequence of length 30.
            # To fetch 30 sequences of online features, standard Feast online store only stores the LATEST value.
            # Thus, for demo purposes and robust standalone prediction, we fetch history or construct a mock sequence
            # around the latest cycle value to represent the running state.
            cycle = online_data["cycle"][0]
            st.write(f"**Feast Latest Cycle**: {cycle}")
            
            # Let's extract the actual feature schema to predict
            # If model exists, we can perform prediction.
            # Since online store only holds latest row, we construct a 30-cycle running window from the SQLite database
            # table engine_features directly (representing the state gathered from Feast registry).
            try:
                # Connect to offline/online fallback sqlite table to fetch the sequence window
                from dataops.config import FEAST_CFG
                from sqlalchemy import create_engine
                FALLBACK_DB = FEAST_CFG.get("offline_store", {}).get("fallback_db", "data/offline_store.db")
                fallback_path = resolve_path(FALLBACK_DB)
                engine_db = create_engine(f"sqlite:///{fallback_path}")
                
                # Fetch sequence
                seq_df = pd.read_sql(
                    f"SELECT * FROM engine_features WHERE unit_number = {engine_id} ORDER BY cycle DESC LIMIT {SEQ_LENGTH}",
                    con=engine_db
                )
                
                if len(seq_df) < SEQ_LENGTH:
                    st.warning(f"Engine #{engine_id} has only {len(seq_df)} history cycles. Model requires sequence size of {SEQ_LENGTH} to predict.")
                else:
                    seq_df = seq_df.sort_values("cycle")
                    
                    # Columns list matching haja.py features
                    feature_cols = [c for c in seq_df.columns if c not in ["unit_number", "cycle", "event_timestamp", "RUL", "RUL_TARGET", "engine_type", "unique_engine_id", "time_in_months"]]
                    
                    # Generate input sequence (3D tensor)
                    input_seq = seq_df[feature_cols].values
                    input_seq_3d = np.expand_dims(input_seq, axis=0) # shape (1, 30, num_features)
                    
                    if model:
                        predicted_rul = model.predict(input_seq_3d).flatten()[0]
                        
                        # Actual RUL
                        actual_rul = seq_df["RUL_TARGET"].iloc[-1]
                        
                        st.markdown(f'<div class="metric-card"><div class="metric-title">🔮 Predicted RUL</div><div class="metric-value">{predicted_rul:.1f} Cycles</div></div>', unsafe_allow_html=True)
                        st.markdown(f"**Actual RUL Target (Clipped)**: {actual_rul} cycles")
                        
                        # Health bar
                        health_percent = min(100, int((predicted_rul / 125) * 100))
                        st.progress(health_percent / 100)
                        st.write(f"Engine Remaining Life Health: **{health_percent}%**")
                    else:
                        st.error("RUL Model not loaded. Train a model first.")
            except Exception as e:
                st.error(f"Inference pipeline failed: {e}")

    with col2:
        st.markdown("### Feast Online Feature Store Inspector")
        if online_data:
            st.write(f"Latest metrics stored in Feast Online Store (SQLite) for **Engine #{engine_id}**:")
            # Display metrics table
            flat_data = {k: v[0] for k, v in online_data.items() if v is not None}
            st.json(flat_data)
        else:
            st.info("Select an engine unit and click 'Apply & Materialize Feast' to view Feast online metrics.")
