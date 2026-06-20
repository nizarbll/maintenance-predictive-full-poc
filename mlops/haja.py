import os
import numpy as np
import mlflow
import mlflow.keras
from mlflow.tracking import MlflowClient
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Conv1D, LSTM, Dense, Dropout, MaxPooling1D
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import mean_absolute_error

BACKUP_MODEL_PATH = "models/backup_model.keras"
PRIMARY_MODEL_PATH = "models/primary_model.keras"
EXPERIMENT_NAME = "RUL_Pipeline"
MODEL_NAME = "RUL_Model"
THRESHOLD = 1.2


def run_pipeline(X, y):
    """
    Main monitoring and recovery pipeline.

    Workflow:
    1. Load current production model
    2. Evaluate production performance
    3. Detect degradation using MAE threshold
    4. If degraded:
            - load challenger/backup model
            - compare performances
            - promote challenger if better
    """

    mlflow.set_experiment(EXPERIMENT_NAME)

    print("\n--- Starting Evaluation & Recovery Pipeline ---")

    try:

        with mlflow.start_run(run_name=EXPERIMENT_NAME):

            client = MlflowClient()

            # Split data
            split = int(0.8 * len(X))

            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]

            # Load production model
            print("Loading production model...")
            try:
                production_model = mlflow.keras.load_model(
                    f"models:/{MODEL_NAME}/Production"
                )
            except Exception as e:
                print(
                    "No production model found → "
                    "training initial production model."
                )
                production_model = train_model(
                    X_train,
                    y_train,
                    input_shape=(
                        X_train.shape[1],
                        X_train.shape[2]
                    )
                )

                # Save locally
                #production_model.save(PRIMARY_MODEL_PATH)

                # Register in MLflow
                mlflow.keras.log_model(
                    production_model,
                    artifact_path="model",
                    registered_model_name=MODEL_NAME
                )

                # Promote initial version to Production
                versions = client.search_model_versions(
                    f"name='{MODEL_NAME}'"
                )

                latest_version = max(
                    versions,
                    key=lambda v: int(v.version)
                )

                client.transition_model_version_stage(
                    name=MODEL_NAME,
                    version=latest_version.version,
                    stage="Production"
                )

                print(
                    f"Initial model version "
                    f"{latest_version.version} "
                    f"promoted to Production."
                )

            # Evaluate production model
            production_pred = production_model.predict(X_test).flatten()
            current_mae = mean_absolute_error(
                y_test,
                production_pred
            )
            print(f"Production MAE: {current_mae:.3f}")
            mlflow.log_metric("current_mae", current_mae)

            
            # Retrieve baseline MAE
            baseline_mae = get_best_mae()
            if baseline_mae is None:
                baseline_mae = current_mae
                print(
                    "No historical baseline found → "
                    "using current MAE as baseline."
                )
            print(f"Baseline MAE: {baseline_mae:.3f}")
            mlflow.log_metric("baseline_mae", baseline_mae)

            
            # Drift detection
            degrade = current_mae > (baseline_mae * THRESHOLD)
            mlflow.log_param("threshold", THRESHOLD)
            mlflow.log_param("drift_detected", degrade)
            
            # Stable production model
            if not degrade:
                print("Production model is stable.")
                mlflow.log_param(
                    "model_status",
                    "stable"
                )
                return

            # Degradation detected
            print(
                "Performance degradation detected → "
                "evaluating backup challenger model."
            )

            # Load backup model
            challenger_model = get_backup_model()

            # Emergency fallback
            if challenger_model is None:
                print(
                    "No backup model available → "
                    "triggering emergency retraining."
                )
                challenger_model = train_model(
                    X_train,
                    y_train,
                    input_shape=(
                        X_train.shape[1],
                        X_train.shape[2]
                    )
                )

            # Evaluate challenger
            challenger_pred = challenger_model.predict(X_test).flatten()
            challenger_mae = mean_absolute_error(
                y_test,
                challenger_pred
            )
            print(
                f"Challenger MAE: "
                f"{challenger_mae:.3f}"
            )
            mlflow.log_metric(
                "challenger_mae",
                challenger_mae
            )

            # Promotion decision
            if challenger_mae < current_mae:
                print(
                    "Challenger outperformed production "
                    "model → promoting to Production."
                )

                # Save locally
                #challenger_model.save(PRIMARY_MODEL_PATH)

                # Register model in MLflow
                mlflow.keras.log_model(
                    challenger_model,
                    artifact_path="model",
                    registered_model_name=MODEL_NAME
                )

                # Retrieve latest registered version
                versions = client.search_model_versions(
                    f"name='{MODEL_NAME}'"
                )
                latest_version = max(
                    versions,
                    key=lambda v: int(v.version)
                )

                # Promote to Production
                client.transition_model_version_stage(
                    name=MODEL_NAME,
                    version=latest_version.version,
                    stage="Production"
                )
                print(
                    f"Model version "
                    f"{latest_version.version} "
                    f"promoted to Production."
                )
                mlflow.log_param(
                    "model_status",
                    "promoted_to_production"
                )

            else:
                print(
                    "Challenger did not outperform "
                    "production model."
                )
                mlflow.log_param(
                    "model_status",
                    "kept_current_production"
                )

    except Exception as e:
        print(f"Pipeline failed: {e}")
        mlflow.log_param(
            "pipeline_error",
            str(e)
        )   
            
def get_production_model(client):
    versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    if not versions:
        return None
    return max(versions, key=lambda v: int(v.version)).version


def get_best_mae():
    client = MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["metrics.current_mae ASC"],
        max_results=1
    )
    
    return runs[0].data.metrics["current_mae"] if runs else None


def initialize_production_model(X, y):

    """
    Bootstrap the very first production model.

    This function is executed only when no
    production model exists in MLflow.
    """

    print("\n--- Initializing Production Model ---")

    try:

        client = MlflowClient()

        # =====================================================
        # Check if production model already exists
        # =====================================================

        try:

            mlflow.keras.load_model(
                f"models:/{MODEL_NAME}/Production"
            )

            print(
                "Production model already exists."
            )

            return

        except:
            print(
                "No production model found."
            )

        # =====================================================
        # Split data
        # =====================================================

        split = int(0.8 * len(X))

        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # =====================================================
        # Train initial model
        # =====================================================

        print("Training initial production model...")

        model = train_model(
            X_train,
            y_train,
            input_shape=(
                X_train.shape[1],
                X_train.shape[2]
            )
        )

        # =====================================================
        # Evaluate initial model
        # =====================================================

        predictions = model.predict(X_test).flatten()

        mae = mean_absolute_error(
            y_test,
            predictions
        )

        print(f"Initial model MAE: {mae:.3f}")

        # =====================================================
        # Save locally
        # =====================================================

        os.makedirs("models", exist_ok=True)

        model.save(PRIMARY_MODEL_PATH)

        # =====================================================
        # Register model in MLflow
        # =====================================================

        mlflow.set_experiment(EXPERIMENT_NAME)

        with mlflow.start_run(
            run_name="initial_production_training"
        ):

            mlflow.log_metric(
                "initial_mae",
                mae
            )

            mlflow.keras.log_model(
                model,
                artifact_path="model",
                registered_model_name=MODEL_NAME
            )

        # =====================================================
        # Promote latest version to Production
        # =====================================================

        versions = client.search_model_versions(
            f"name='{MODEL_NAME}'"
        )

        latest_version = max(
            versions,
            key=lambda v: int(v.version)
        )

        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=latest_version.version,
            stage="Production"
        )

        print(
            f"Initial model version "
            f"{latest_version.version} "
            f"promoted to Production."
        )

    except Exception as e:

        print(
            f"Production initialization failed: {e}"
        )
#----------------

def train_model(X_train, y_train, input_shape):

    model = Sequential()
    model.add(Conv1D(filters=64, kernel_size=3, activation='relu', padding='same', input_shape=input_shape))
    model.add(MaxPooling1D(pool_size=2)) 
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(units=32, activation='relu'))
    model.add(Dense(units=1, activation='linear'))
    model.compile(loss='mse', optimizer=Adam(learning_rate=0.001), metrics=['mae'])

    early_stop = EarlyStopping(
        monitor='val_loss',         # On surveille l'erreur sur les données de validation
        patience=10,                # Si pas d'amélioration après 10 époques...
        restore_best_weights=True,  # ...on s'arrête et on charge la meilleure version de l'IA !
        verbose=1
    )

    model.fit(
        X_train, y_train,
        epochs=100,                  # Maximum 100 tours d'apprentissage
        batch_size=64,               # L'IA analyse les séquences par paquets de 64
        validation_split=0.15,       # On cache 15% des données à l'IA pour la tester à chaque tour
        shuffle=False,
        callbacks=[early_stop],
        verbose=1
    )

    return model


def run_scheduled_backup_training(X, y):
    """
    To be triggered every 15 days.
    Trains on the newest available data asynchronously and saves strictly to the BACKUP path.
    """

    print("--- Starting Scheduled Backup Training ---")

    try:
        split = int(0.8 * len(X))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        os.makedirs("models", exist_ok=True)

        # continuous learning on the latest data to keep the backup model fresh and ready to swap in case of degradation
        with mlflow.start_run(run_name="scheduled_backup_training"):
            if os.path.exists(BACKUP_MODEL_PATH):
                #print(f"Found existing backup model at {BACKUP_MODEL_PATH} → fine-tuning on latest data")
                backup_model = load_model(BACKUP_MODEL_PATH)
                backup_model.fit(
                    X_train,
                    y_train
                )
            else:
                #print("No backup model found → training from scratch")
                backup_model = train_model(
                    X_train,
                    y_train,
                    input_shape=(X_train.shape[1], X_train.shape[2])
                )

            backup_pred = backup_model.predict(X_test).flatten()
            backup_mae = mean_absolute_error(y_test, backup_pred)

            mlflow.log_metric("backup_mae", backup_mae)
            print(f"Backup model MAE: {backup_mae:.3f}")

            backup_model.save(BACKUP_MODEL_PATH)

            mlflow.keras.log_model(
                backup_model,
                artifact_path="backup_model"
            )

            print(f"Backup model saved to {BACKUP_MODEL_PATH}")

    except Exception as e:
        print(f"Scheduled training failed: {e}")