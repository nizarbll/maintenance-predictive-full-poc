import sys
import os
from pathlib import Path

# Fix python path for local imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import mlflow
import mlflow.keras
from mlflow.tracking import MlflowClient
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv1D, LSTM, Dense, Dropout, MaxPooling1D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import mean_absolute_error
from dataops.config import MLOPS_CFG, PATHS, resolve_path
from dataops.logger import training_logger

# Configurations
EXPERIMENT_NAME = MLOPS_CFG.get("experiment_name", "RUL_Pipeline")
MODEL_NAME = MLOPS_CFG.get("model_name", "RUL_Model")
THRESHOLD = MLOPS_CFG.get("drift_threshold", 1.2)
SEQ_LENGTH = MLOPS_CFG.get("sequence_length", 30)

PRIMARY_MODEL_PATH = resolve_path(PATHS.get("models", {}).get("primary_path", "pompe_model_lstm.keras"))
BACKUP_MODEL_DIR = resolve_path(PATHS.get("models", {}).get("backup_dir", "models/backup"))
BACKUP_MODEL_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_MODEL_PATH = BACKUP_MODEL_DIR / "pompe_model_lstm_backup.keras"

GOLD_DATASET_PATH = resolve_path(PATHS.get("data_lake", {}).get("gold_dir", "data/gold")) / "gold_dataset.csv"

def generate_sequences(df, feature_cols, sequence_length=30):
    """Generates 3D sequences for LSTM training."""
    X, y = [], []
    for _, group in df.groupby("unit_number"):
        group = group.sort_values("cycle")
        if len(group) < sequence_length:
            continue
        data = group[feature_cols].values
        labels = group["RUL_TARGET"].values
        for i in range(len(group) - sequence_length + 1):
            X.append(data[i:i+sequence_length])
            y.append(labels[i+sequence_length-1])
    return np.array(X), np.array(y)

def train_model(X_train, y_train, input_shape):
    training_logger.info("Initializing LSTM Model...")
    model = Sequential()
    model.add(Conv1D(filters=64, kernel_size=3, activation='relu', padding='same', input_shape=input_shape))
    model.add(MaxPooling1D(pool_size=2)) 
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(units=32, activation='relu'))
    model.add(Dense(units=1, activation='linear'))
    model.compile(loss='mse', optimizer=Adam(learning_rate=0.001), metrics=['mae'])

    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        verbose=1
    )

    epochs = MLOPS_CFG.get("training", {}).get("epochs", 10)
    batch_size = MLOPS_CFG.get("training", {}).get("batch_size", 64)
    val_split = MLOPS_CFG.get("training", {}).get("validation_split", 0.15)

    training_logger.info(f"Starting training for {epochs} epochs, batch size {batch_size}...")
    model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=val_split,
        callbacks=[early_stop],
        verbose=1
    )
    return model

def safe_init_mlflow():
    """Initializes MLflow tracking. Falls back gracefully if tracking server is down."""
    try:
        # Check if local or remote server is set, default to local sqlite / file tracking
        mlflow.set_experiment(EXPERIMENT_NAME)
        client = MlflowClient()
        training_logger.info(f"MLflow Initialized. Tracking experiment: '{EXPERIMENT_NAME}'")
        return client, True
    except Exception as e:
        training_logger.warning(
            f"MLflow Server not available: {e}. "
            "Pipeline will run in standalone mode (saving models locally)."
        )
        return None, False

def load_active_production_model():
    """Tries to load model from MLflow registry, then from disk, then trains new if missing."""
    client, has_mlflow = safe_init_mlflow()
    model = None
    
    if has_mlflow:
        try:
            model_uri = f"models:/{MODEL_NAME}/Production"
            model = mlflow.keras.load_model(model_uri)
            training_logger.info("Successfully loaded active Production model from MLflow registry.")
            return model, has_mlflow
        except Exception:
            training_logger.info("No Production model found in MLflow registry. Checking local disk...")
            
    if PRIMARY_MODEL_PATH.exists():
        try:
            model = load_model(str(PRIMARY_MODEL_PATH))
            training_logger.info(f"Loaded existing model from disk: {PRIMARY_MODEL_PATH}")
            return model, has_mlflow
        except Exception as e:
            training_logger.error(f"Failed to load model from disk: {e}")
            
    return None, has_mlflow

def run_pipeline():
    training_logger.info("=== Starting MLOps Retraining & Drift Pipeline ===")
    
    if not GOLD_DATASET_PATH.exists():
        training_logger.error(f"Gold dataset not found at {GOLD_DATASET_PATH}. Generate it first using retrieve_features.py.")
        return

    # Load dataset
    df = pd.read_csv(GOLD_DATASET_PATH)
    feature_cols = [c for c in df.columns if c not in ["unit_number", "cycle", "event_timestamp", "RUL", "RUL_TARGET", "engine_type", "unique_engine_id", "time_in_months"]]
    
    training_logger.info(f"Generating sequences from Gold dataset. Features: {len(feature_cols)} dimensions.")
    X, y = generate_sequences(df, feature_cols, SEQ_LENGTH)
    
    if len(X) == 0:
        training_logger.error("Not enough sequences generated for training.")
        return

    # Train/Test Split
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model, has_mlflow = load_active_production_model()

    if model is None:
        training_logger.info("No active model found. Training baseline model...")
        model = train_model(X_train, y_train, (X_train.shape[1], X_train.shape[2]))
        model.save(str(PRIMARY_MODEL_PATH))
        training_logger.info(f"Baseline model trained and saved to {PRIMARY_MODEL_PATH}")
        
        if has_mlflow:
            with mlflow.start_run(run_name="baseline_model_training"):
                mlflow.keras.log_model(
                    model,
                    artifact_path="model",
                    registered_model_name=MODEL_NAME
                )
                client = MlflowClient()
                versions = client.search_model_versions(f"name='{MODEL_NAME}'")
                latest_version = max(versions, key=lambda v: int(v.version)).version
                client.transition_model_version_stage(
                    name=MODEL_NAME, version=latest_version, stage="Production"
                )
                training_logger.info(f"Baseline model registered as version {latest_version} in Production.")
        return

    # Evaluate current model to check for drift
    y_pred = model.predict(X_test).flatten()
    current_mae = mean_absolute_error(y_test, y_pred)
    training_logger.info(f"Current active model MAE: {current_mae:.4f}")

    if has_mlflow:
        with mlflow.start_run(run_name="drift_evaluation"):
            mlflow.log_metric("current_mae", float(current_mae))
            
            client = MlflowClient()
            experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
            runs = client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["metrics.current_mae ASC"],
                max_results=1
            )
            
            baseline_mae = runs[0].data.metrics.get("current_mae") if runs else None
            if baseline_mae is None:
                baseline_mae = current_mae
                
            mlflow.log_metric("baseline_mae", float(baseline_mae))
            drift_detected = current_mae > (baseline_mae * THRESHOLD)
            mlflow.log_param("drift_detected", drift_detected)
            
            training_logger.info(f"Baseline MAE: {baseline_mae:.4f} | Threshold MAE: {(baseline_mae * THRESHOLD):.4f}")
            
            if not drift_detected:
                training_logger.info("Model performance stable. No retraining needed.")
                mlflow.log_param("model_status", "stable")
                return

            training_logger.warning("Performance degraded! Drift detected. Training challenger model...")
            challenger_model = train_model(X_train, y_train, (X_train.shape[1], X_train.shape[2]))
            
            challenger_pred = challenger_model.predict(X_test).flatten()
            challenger_mae = mean_absolute_error(y_test, challenger_pred)
            mlflow.log_metric("challenger_mae", float(challenger_mae))
            training_logger.info(f"Challenger model MAE: {challenger_mae:.4f}")
            
            if challenger_mae < current_mae:
                training_logger.info("Challenger model is better! Promoting to Production...")
                challenger_model.save(str(PRIMARY_MODEL_PATH))
                
                mlflow.keras.log_model(
                    challenger_model,
                    artifact_path="model",
                    registered_model_name=MODEL_NAME,
                    input_example=X_train[:1]
                )
                
                versions = client.search_model_versions(f"name='{MODEL_NAME}'")
                latest_version = max(versions, key=lambda v: int(v.version)).version
                client.transition_model_version_stage(
                    name=MODEL_NAME, version=latest_version, stage="Production"
                )
                mlflow.log_param("model_status", "promoted_to_production")
                training_logger.info(f"Challenger promoted to Production as version {latest_version}.")
            else:
                training_logger.info("Challenger model did not outperform production model. Keeping current model.")
                mlflow.log_param("model_status", "kept_current_model")
    else:
        # Standard drift training without MLflow registry (local fallback)
        # We check drift against a hardcoded/local threshold or compare directly with a fast trained model
        training_logger.warning("MLflow disabled. Training and saving locally.")
        challenger_model = train_model(X_train, y_train, (X_train.shape[1], X_train.shape[2]))
        challenger_pred = challenger_model.predict(X_test).flatten()
        challenger_mae = mean_absolute_error(y_test, challenger_pred)
        
        if challenger_mae < current_mae:
            training_logger.info(f"Challenger ({challenger_mae:.4f}) outperforms current ({current_mae:.4f}). Overwriting local model.")
            challenger_model.save(str(PRIMARY_MODEL_PATH))
        else:
            training_logger.info("Current local model remains better.")

def run_scheduled_backup_training():
    """Trains on newest data asynchronously and saves strictly to backup path."""
    training_logger.info("=== Starting Scheduled Backup Training ===")
    if not GOLD_DATASET_PATH.exists():
        training_logger.error("Gold dataset missing.")
        return
        
    df = pd.read_csv(GOLD_DATASET_PATH)
    feature_cols = [c for c in df.columns if c not in ["unit_number", "cycle", "event_timestamp", "RUL", "RUL_TARGET", "engine_type", "unique_engine_id", "time_in_months"]]
    X, y = generate_sequences(df, feature_cols, SEQ_LENGTH)
    
    if len(X) == 0:
        return
        
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    backup_model = train_model(X_train, y_train, (X_train.shape[1], X_train.shape[2]))
    backup_pred = backup_model.predict(X_test).flatten()
    backup_mae = mean_absolute_error(y_test, backup_pred)
    
    backup_model.save(str(BACKUP_MODEL_PATH))
    training_logger.info(f"Backup model trained with MAE {backup_mae:.4f} and saved to {BACKUP_MODEL_PATH}")

if __name__ == "__main__":
    run_pipeline()