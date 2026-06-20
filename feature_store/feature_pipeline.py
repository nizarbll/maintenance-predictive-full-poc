import pandas as pd
from datetime import datetime, timezone
import numpy as np
from sqlalchemy import create_engine

postgres_engine = create_engine("postgresql://postgres:postgres@localhost:5432/feature_store")  

sensor_cols = [f"sensor_{i}" for i in range(1, 22) if i != 16]
op_cols = ["op_setting_1", "op_setting_2", "op_setting_3"]
useful_cols = sensor_cols + op_cols

sequence_length = 30
window_size = 5
clip_limit = 125

def add_rul(df):

    grouped = df.groupby("unit_number")
    max_cycles = grouped["cycle"].max()

    df = df.merge(
        max_cycles.to_frame("max_cycle"),
        left_on="unit_number",
        right_index=True
    )

    df["RUL"] = df["max_cycle"] - df["cycle"]
    df.drop(columns=["max_cycle"], inplace=True)

    df["RUL_TARGET"] = df["RUL"].clip(upper=clip_limit)

    return df


def feature_engineering(df):

    df["time_in_months"] = df["cycle"] / 30.0

    dfs = []

    for engine_id, group in df.groupby("unit_number"):

        group = group.sort_values("cycle")

        roll_mean = group[useful_cols].rolling(window=window_size, min_periods=1).mean()
        roll_mean = roll_mean.add_suffix("_roll_mean")

        roll_std = group[useful_cols].rolling(window=window_size, min_periods=1).std().fillna(0)
        roll_std = roll_std.add_suffix("_roll_std")

        diff = group[useful_cols].diff().fillna(0)
        diff = diff.add_suffix("_diff")

        combined = pd.concat([group, roll_mean, roll_std, diff], axis=1)
        dfs.append(combined)

    return pd.concat(dfs, ignore_index=True)

def normalize(df):

    stds = df[sensor_cols + op_cols].std()
    drop_cols = stds[stds < 0.01].index.tolist()

    df = df.drop(columns=drop_cols)

    useful = [c for c in sensor_cols + op_cols if c not in drop_cols]

    def minmax(x):
        r = x.max() - x.min()
        return x - x.min() if r == 0 else (x - x.min()) / r

    for col in useful:
        df[col] = df.groupby("unit_number")[col].transform(minmax)

    return df, useful

def generate_sequences(df, feature_cols):

    X, y = [], []

    for _, group in df.groupby("unit_number"):

        group = group.sort_values("cycle")

        data = group[feature_cols].values
        labels = group["RUL_TARGET"].values

        if len(group) < sequence_length:
            continue

        for i in range(len(group) - sequence_length + 1):

            X.append(data[i:i+sequence_length])
            y.append(labels[i+sequence_length-1])

    return np.array(X), np.array(y)

def process_batch(df):

    # 1. timestamp (important pour Feast)
    df["event_timestamp"] = datetime.now(timezone.utc)

    # 2. RUL computation
    df = add_rul(df)

    # 3. Feature engineering
    df = feature_engineering(df)

    # 4. Normalisation
    df, _ = normalize(df)

    # 5. SAVE TO POSTGRES (offline store Feast)
    df.to_sql(
        "engine_features",
        con=postgres_engine,
        if_exists="append",
        index=False
    )